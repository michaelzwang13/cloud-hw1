import json
import boto3
import os
import random
from decimal import Decimal
from requests_aws4auth import AWS4Auth
import requests

SQS_QUEUE_URL = os.environ['SQS_QUEUE_URL']
OPENSEARCH_ENDPOINT = os.environ['OPENSEARCH_ENDPOINT']
DYNAMODB_TABLE = os.environ['DYNAMODB_TABLE']
SES_SENDER = os.environ['SES_SENDER']
REGION = 'us-east-1'

sqs = boto3.client('sqs', region_name=REGION)
dynamodb = boto3.resource('dynamodb', region_name=REGION)
ses = boto3.client('ses', region_name=REGION)
table = dynamodb.Table(DYNAMODB_TABLE)

credentials = boto3.Session().get_credentials().get_frozen_credentials()
awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, REGION, 'es',
                   session_token=credentials.token)

def get_random_restaurants(cuisine, count=3):
    url = f'{OPENSEARCH_ENDPOINT}/restaurants/_search'
    query = {
        'size': count,
        'query': {
            'function_score': {
                'query': {'match': {'cuisine': cuisine}},
                'functions': [{'random_score': {}}],
                'score_mode': 'sum'
            }
        }
    }
    response = requests.get(url, auth=awsauth,
                            headers={'Content-Type': 'application/json'},
                            data=json.dumps(query))
    hits = response.json().get('hits', {}).get('hits', [])
    return [hit['_source']['id'] for hit in hits]

def get_restaurant_details(restaurant_id):
    response = table.get_item(Key={'id': restaurant_id})
    return response.get('Item')

def send_email(to_email, restaurants, booking):
    subject = 'Your Restaurant Suggestions from Dining Concierge'

    recommendations = ''
    for i, r in enumerate(restaurants, 1):
        rating = float(r.get('rating', 0))
        recommendations += f"""
{i}. {r.get('name')}
   Address: {r.get('address')}
   Rating: {rating} / 5
   Phone: {r.get('phone', 'N/A')}
"""

    body = f"""Hello!

Based on your request, here are {len(restaurants)} {restaurants[0].get('cuisine', '').title()} restaurant suggestions:
{recommendations}
Reservation Details:
- Date: {booking.get('date')}
- Time: {booking.get('time')}
- Party size: {booking.get('partyCount')}

Enjoy your meal!

- Dining Concierge
"""
    ses.send_email(
        Source=SES_SENDER,
        Destination={'ToAddresses': [to_email]},
        Message={
            'Subject': {'Data': subject},
            'Body': {'Text': {'Data': body}}
        }
    )

def lambda_handler(event, context):
    response = sqs.receive_message(
        QueueUrl=SQS_QUEUE_URL,
        MaxNumberOfMessages=1,
        WaitTimeSeconds=0
    )

    messages = response.get('Messages', [])
    if not messages:
        print('No messages in queue')
        return

    message = messages[0]
    receipt_handle = message['ReceiptHandle']
    booking = json.loads(message['Body'])

    cuisine = booking.get('cuisine', '').lower()
    email = booking.get('email')

    if not cuisine or not email:
        print(f'Missing cuisine or email in message: {booking}')
        sqs.delete_message(QueueUrl=SQS_QUEUE_URL, ReceiptHandle=receipt_handle)
        return

    restaurant_ids = get_random_restaurants(cuisine)
    if not restaurant_ids:
        print(f'No restaurants found for cuisine: {cuisine}')
        return

    restaurants = []
    for rid in restaurant_ids:
        details = get_restaurant_details(rid)
        if details:
            restaurants.append(details)

    if not restaurants:
        print(f'Could not fetch restaurant details from DynamoDB')
        return

    send_email(email, restaurants, booking)
    print(f'Email sent to {email} with {len(restaurants)} {cuisine} restaurants')

    sqs.delete_message(QueueUrl=SQS_QUEUE_URL, ReceiptHandle=receipt_handle)