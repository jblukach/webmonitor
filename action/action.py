import boto3
import json
import os

def handler(event, context):

    print(event)

    for record in event.get('Records', []):
        if record.get('eventName') == 'INSERT':
            new_image = record.get('dynamodb', {}).get('NewImage', {})
            if new_image and 'sld' in new_image:

                print(new_image['sld']['S'])
                print(new_image['domain']['S'])
                print(new_image['tbl']['S'])







    return {
        'statusCode': 200,
        'body': json.dumps('Action Completed!')
    }