import uvicorn
from fastapi import FastAPI, Header, Body, HTTPException
from pydantic import BaseModel
from urllib.request import urlopen
from urllib.error import URLError
import urllib.parse
import argparse
import logging

KIWIX_URL = 'http://127.0.0.1:8080'
EXPECTED_BEARER_TOKEN = ''

app = FastAPI()

class SearchRequest(BaseModel):
	query: str
	count: int

class SearchResult(BaseModel):
	link: str
	title: str | None
	snippet: str | None

@app.post('/search')
async def external_search(search_request: SearchRequest = Body(...), authorization: str | None = Header(None)):
	if EXPECTED_BEARER_TOKEN != '':
		expected_auth_header = f'Bearer {EXPECTED_BEARER_TOKEN}'
		if authorization != expected_auth_header:
			raise HTTPException(status_code=401, detail='Unauthorized')

	query, count = search_request.query, search_request.count

	try:
		response = urlopen(KIWIX_URL + '/search?' + urllib.parse.urlencode({'pattern':search_request.query}) + f'&pageLength={count}', timeout = 10)
	except URLError as e:
		logging.error(f'Failed to connect to the kiwix server "{KIWIX_URL}" {e}')
		return []
	html_content = response.read().decode('utf-8')

	results_unparsed = html_content.split('<div class="results">')[1][21:].split('<div class="footer">')[0].split('</li>')[:-1]

	if len(results_unparsed) == 0:
		print('No results found')
		return []

	results = []
	for result in results_unparsed[:search_request.count]:
		href = KIWIX_URL + result[result.find('<a href="') + 9 : result.find('">')]
		name = result[result.find('">') + 3 : result.find('</a>') - 1].strip()
		body = result[result.find('<cite>') + 6 : result.find('</cite>') - 1]
		results.append(
			SearchResult(
				link = href,
				title = name,
				snippet = body,
			)
		)
	print(f'Found {len(results)} results')
	return results

if __name__ == '__main__':
	parser = argparse.ArgumentParser()
	parser.add_argument('-p', '--port', type = int, default = 8008, help = 'Port to open  [default: 8008]')
	parser.add_argument('-u', '--url', default = KIWIX_URL, help = f'Adress of the kiwix server [default: {KIWIX_URL}]')
	parser.add_argument('-t', '--token', default = EXPECTED_BEARER_TOKEN, help = 'Expected bearer token [optional]')
	parser.add_argument('-a', '--adress', default = '0.0.0.0', help = 'Adress to listen on [default: 0.0.0.0]')

	args = parser.parse_args()

	KIWIX_URL = args.url
	EXPECTED_BEARER_TOKEN = args.token

	uvicorn.run(app, host=args.adress, port=args.port)
