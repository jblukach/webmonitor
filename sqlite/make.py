import boto3
import datetime
import json
import os

def handler(event, context):

    print(event)

    key = event.get('Key')
    
    if key:
        print(f'Processing: {key}')

    return {
        'statusCode': 200,
        'body': json.dumps('Make SQLite!')
    }