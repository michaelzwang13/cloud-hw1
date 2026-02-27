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

def get_random_restaurant(cuisine):
    url = f'{OPENSEARCH_ENDPOINT}/restaurants/_search'
    query = {
        'size': 1,
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
    print(f'OpenSearch status: {response.status_code}, body: {response.text[:500]}')
    hits = response.json().get('hits', {}).get('hits', [])
    if not hits:
        return None
    return hits[0]['_source']['id']

def get_restaurant_details(restaurant_id):
    response = table.get_item(Key={'id': restaurant_id})
    return response.get('Item')

def send_email(to_email, restaurant, booking):
    rating = float(restaurant.get('rating', 0))
    subject = 'Your Restaurant Suggestion from Dining Concierge'
    body = f"""Hello!

Based on your request, here is a restaurant suggestion:

Restaurant: {restaurant.get('name')}
Cuisine: {restaurant.get('cuisine', '').title()}
Address: {restaurant.get('address')}
Rating: {rating} / 5
Phone: {restaurant.get('phone', 'N/A')}

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

    restaurant_id = get_random_restaurant(cuisine)
    if not restaurant_id:
        print(f'No restaurant found for cuisine: {cuisine}')
        return

    restaurant = get_restaurant_details(restaurant_id)
    if not restaurant:
        print(f'Restaurant {restaurant_id} not found in DynamoDB')
        return

    send_email(email, restaurant, booking)
    print(f'Email sent to {email} for {cuisine} restaurant: {restaurant.get("name")}')

    sqs.delete_message(QueueUrl=SQS_QUEUE_URL, ReceiptHandle=receipt_handle)