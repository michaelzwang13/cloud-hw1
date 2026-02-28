import json
import datetime
import os
import boto3

sqs = boto3.client('sqs')
SQS_QUEUE_URL = os.environ['SQS_QUEUE_URL']

# Configuration
ALLOWED_CITIES = ['manhattan']
ALLOWED_CUISINES = ['chinese', 'indian', 'mexican', 'japanese', 'italian']

def validate_booking(slots):
    # 1. Validate Location
    if slots.get('Location') and slots['Location'].get('value'):
        user_city = slots['Location']['value']['interpretedValue'].lower()
        if user_city not in ALLOWED_CITIES:
            return {
                'isValid': False,
                'violatedSlot': 'Location',
                'message': f"Sorry, we only have restaurants in {', '.join(ALLOWED_CITIES).title()}. Which would you like?"
            }

    # 2. Validate Cuisine
    if slots.get('Cuisine') and slots['Cuisine'].get('value'):
        cuisine = slots['Cuisine']['value']['interpretedValue'].lower()
        if cuisine not in ALLOWED_CUISINES:
            return {
                'isValid': False,
                'violatedSlot': 'Cuisine',
                'message': f"Sorry, we only support {', '.join(c.title() for c in ALLOWED_CUISINES)} cuisines. Which would you like?"
            }

    # 3. Validate Date
    if slots.get('Date') and slots['Date'].get('value'):
        booking_date_str = slots['Date']['value']['interpretedValue']
        booking_date = datetime.datetime.strptime(booking_date_str, '%Y-%m-%d').date()
        if booking_date < datetime.date.today():
            return {
                'isValid': False,
                'violatedSlot': 'Date',
                'message': 'We cannot book for a past date. Please pick a future date.'
            }

    # 3. Validate Party Count
    if slots.get('PartyCount') and slots['PartyCount'].get('value'):
        count = int(slots['PartyCount']['value']['interpretedValue'])
        if count <= 0 or count > 10:
            return {
                'isValid': False,
                'violatedSlot': 'PartyCount',
                'message': 'We can only accommodate 1 to 10 people. How many people are in your party?'
            }

    return {'isValid': True}

def lambda_handler(event, context):
    intent_name = event['sessionState']['intent']['name']
    slots = event['sessionState']['intent']['slots']
    source = event['invocationSource'] 
    
    if source == 'DialogCodeHook':
        validation_result = validate_booking(slots)
        
        if not validation_result['isValid']:
            return {
                "sessionState": {
                    "dialogAction": {
                        "slotToElicit": validation_result['violatedSlot'],
                        "type": "ElicitSlot"
                    },
                    "intent": {"name": intent_name, "slots": slots}
                },
                "messages": [{"contentType": "PlainText", "content": validation_result['message']}]
            }

        return {
            "sessionState": {
                "dialogAction": {"type": "Delegate"},
                "intent": {"name": intent_name, "slots": slots}
            }
        }

    if source == 'FulfillmentCodeHook':
        def slot_value(slot_name):
            slot = slots.get(slot_name)
            if slot and slot.get('value'):
                return slot['value']['interpretedValue']
            return None

        message = {
            'location': slot_value('Location'),
            'date': slot_value('Date'),
            'time': slot_value('Time'),
            'partyCount': slot_value('PartyCount'),
            'cuisine': slot_value('Cuisine'),
            'email': slot_value('Email'),
        }

        sqs.send_message(
            QueueUrl=SQS_QUEUE_URL,
            MessageBody=json.dumps(message)
        )

        return {
            "sessionState": {
                "dialogAction": {"type": "Close"},
                "intent": {"name": intent_name, "slots": slots, "state": "Fulfilled"}
            },
            "messages": [{"contentType": "PlainText", "content": "You're all set. Check your email shortly for my suggestions. Have a good day!"}]
        }