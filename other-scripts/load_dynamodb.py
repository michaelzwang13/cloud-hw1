import json
import boto3
from decimal import Decimal
from datetime import datetime, timezone

TABLE_NAME = 'yelp-restaurants'

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table(TABLE_NAME)

with open('restaurants.json', 'r') as f:
    data = json.load(f)

timestamp = datetime.now(timezone.utc).isoformat()

restaurants = []
for cuisine_list in data.values():
    for r in cuisine_list:
        r['insertedAtTimestamp'] = timestamp
        restaurants.append(r)

def chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

total = 0
with table.batch_writer() as batch:
    for restaurant in restaurants:
        item = {k: Decimal(str(v)) if isinstance(v, float) else v
                for k, v in restaurant.items() if v is not None and v != ''}
        batch.put_item(Item=item)
        total += 1

print(f'Loaded {total} restaurants into {TABLE_NAME}')