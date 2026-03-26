import boto3
import datetime
import json
import os
from boto3.dynamodb.conditions import Key

def handler(event, context):

    year = datetime.datetime.now().strftime('%Y')
    month = datetime.datetime.now().strftime('%m')
    day = datetime.datetime.now().strftime('%d')

    s3_client = boto3.client('s3')
    lambda_client = boto3.client('lambda')

    objects = s3_client.list_objects(
        Bucket = os.environ['S3_BUCKET']
    )

    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(os.environ['DYNAMODB_TABLE'])

    response = table.query(
        KeyConditionExpression = Key('pk').eq('LUNKER#')
    )
    responsedata = response['Items']
    while 'LastEvaluatedKey' in response:
        response = table.query(
            KeyConditionExpression = Key('pk').eq('LUNKER#'),
            ExclusiveStartKey = response['LastEvaluatedKey']
        )
        responsedata.update(response['Items'])

    print('DynamoDB: '+str(len(responsedata)))

    items = []

    for item in responsedata:
        items.append(item['sld'])

    items = sorted(set(items))

    print('Items: '+str(len(items)))

    for item in items:

        print('Item: '+item)

        for key in objects['Contents']:

            if key['Key'].startswith(f'{year}-{month}-{day}-') and key['Key'].endswith('.sqlite3'):

                if key['Size'] != 0:

                    print(' - '+key['Key'])

                    payload = {
                        'Key': key['Key'],
                        'Item': item
                    }

                    #lambda_client.invoke(
                    #    FunctionName = os.environ['SEARCH_FUNCTION_NAME'],
                    #    InvocationType = 'Event',
                    #    Payload = json.dumps(payload)
                    #)

    return {
        'statusCode': 200,
        'body': json.dumps('Query Lunker & List Files!')
    }