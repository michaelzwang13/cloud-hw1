import json
import boto3
from requests_aws4auth import AWS4Auth
import requests

OPENSEARCH_ENDPOINT = 'https://search-yelp-restaurants-dl6skx24xolvw23jwcfegjz4be.us-east-1.es.amazonaws.com'
INDEX = 'restaurants'
REGION = 'us-east-1'

credentials = boto3.Session().get_credentials()
awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, REGION, 'es', session_token=credentials.token)

with open('../data/restaurants.json', 'r') as f:
    data = json.load(f)

restaurants = []
for cuisine, items in data.items():
    for r in items:
        restaurants.append({
            'id': r['id'],
            'cuisine': cuisine
        })

url = f'{OPENSEARCH_ENDPOINT}/{INDEX}/_bulk'
headers = {'Content-Type': 'application/json'}

bulk_body = ''
for r in restaurants:
    bulk_body += json.dumps({'index': {'_index': INDEX, '_id': r['id']}}) + '\n'
    bulk_body += json.dumps(r) + '\n'

response = requests.post(url, auth=awsauth, headers=headers, data=bulk_body)
print(f'HTTP status: {response.status_code}')

if response.status_code != 200:
    print('Error response:', response.text)
else:
    result = response.json()
    errors = [item for item in result.get('items', []) if 'error' in item.get('index', {})]
    print(f'Indexed {len(result.get("items", []))} restaurants. Errors: {len(errors)}')
    if errors:
        print(errors[:3])