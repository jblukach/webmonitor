import boto3
import datetime
import json
import os
from boto3.dynamodb.conditions import Key


def _build_ziplist_payloads(key, items, max_payload_bytes=200000):
    payloads = []
    chunk = []

    for item in items:
        candidate = chunk + [item]
        payload = {'Key': key, 'Items': candidate}
        payload_size = len(json.dumps(payload).encode('utf-8'))

        if payload_size <= max_payload_bytes:
            chunk = candidate
            continue

        if chunk:
            payloads.append({'Key': key, 'Items': chunk})
            chunk = [item]
            continue

        # Fallback for an unusually large single item string.
        payloads.append({'Key': key, 'Item': item})

    if chunk:
        payloads.append({'Key': key, 'Items': chunk})

    return payloads

def handler(event, context):

    status = event.get('Status') or event.get('status')

    year = datetime.datetime.now().strftime('%Y')
    month = datetime.datetime.now().strftime('%m')
    day = datetime.datetime.now().strftime('%d')

    s3_client = boto3.client('s3')
    lambda_client = boto3.client('lambda')

    objects = s3_client.list_objects(
        Bucket = os.environ['S3_BUCKET']
    )

    dynamodb = boto3.resource('dynamodb')
    state = dynamodb.Table(os.environ['STATE_TABLE'])
    table = dynamodb.Table(os.environ['DYNAMODB_TABLE'])
    today = year+'-'+month+'-'+day
    ttl_30_days = int((datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days = 30)).timestamp())

    items = []
    run_scheduled_mode = True

    if status:
        run_scheduled_mode = False
        state_response = state.get_item(
            Key={
                'pk': 'LUNKER#',
                'sk': 'LUNKER#'+status
            }
        )
        state_item = state_response.get('Item')

        if state_item:
            if state_item.get('lastday') == today:
                print('Status already processed today: '+status)
                items = []
            else:
                items = [status]
        else:
            print('Status not found in state table, running single status: '+status)
            items = [status]

    if run_scheduled_mode:
        response = table.query(
            KeyConditionExpression = Key('pk').eq('LUNKER#')
        )
        responsedata = response['Items']
        while 'LastEvaluatedKey' in response:
            response = table.query(
                KeyConditionExpression = Key('pk').eq('LUNKER#'),
                ExclusiveStartKey = response['LastEvaluatedKey']
            )
            responsedata.extend(response['Items'])

        print('DynamoDB: '+str(len(responsedata)))

        for item in responsedata:
            items.append(item['sld'])

        items = sorted(set(items))

    print('Items Count: '+str(len(items)))
    print('Items: '+json.dumps(items))

    if items:
        zip_payloads = _build_ziplist_payloads(
            f'{year}-{month}-{day}-full.zip',
            items
        )

        print('Ziplist Invocations: '+str(len(zip_payloads)))
        for payload in zip_payloads:
            lambda_client.invoke(
                FunctionName = 'ziplist',
                InvocationType = 'Event',
                Payload = json.dumps(payload)
            )

    for item in items:

        print('Item: '+item)

        state.put_item(
            Item={
                'pk': 'LUNKER#',
                'sk': 'LUNKER#'+item,
                'lastday': today,
                'ttl': ttl_30_days
            }
        )

        for key in objects['Contents']:

            if key['Key'].startswith(f'{year}-{month}-{day}-') and key['Key'].endswith('.sqlite3'):

                if key['Size'] != 0:

                    print(' - '+key['Key'])

                    payload = {
                        'Key': key['Key'],
                        'Item': item
                    }

                    lambda_client.invoke(
                        FunctionName = os.environ['SEARCH_FUNCTION_NAME'],
                        InvocationType = 'Event',
                        Payload = json.dumps(payload)
                    )

    return {
        'statusCode': 200,
        'body': json.dumps({
            'message': 'Query Lunker & List Files!',
            'itemCount': len(items),
            'items': items
        })
    }