import boto3
import datetime
import json
import os
import zipfile
from boto3.dynamodb.conditions import Key

def handler(event, context):

    #key = event.get('Key')
    #item = event.get('Item')

    key = '2026-03-28-full.zip'
    item = 'lukach'

    print('Item: '+item+' Key: '+key)

    s3_client = boto3.client('s3')
    s3_client.download_file(os.environ['S3_BUCKET'], key, '/tmp/'+key)

    zip_path = '/tmp/' + key

    matches = []
    with zipfile.ZipFile(zip_path, 'r') as zf:
        for name in zf.namelist():
            with zf.open(name) as f:
                for line in f:
                    decoded = line.decode('utf-8', errors='ignore').strip()
                    if item in decoded:
                        matches.append(decoded)

    print('Matches: ' + str(len(matches)))

    # Extract table name from key: between last '-' and '.'
    table_name = key.rsplit('-', 1)[-1].rsplit('.', 1)[0]
    
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(table_name)

    sk_query = 'LUNKER#' + item + '#'
    
    response = table.query(
        KeyConditionExpression = Key('pk').eq('LUNKER#') & Key('sk').begins_with(sk_query)
    )
    responsedata = response['Items']
    while 'LastEvaluatedKey' in response:
        response = table.query(
            KeyConditionExpression = Key('pk').eq('LUNKER#') & Key('sk').begins_with(sk_query),
            ExclusiveStartKey = response['LastEvaluatedKey']
        )
        responsedata.extend(response['Items'])

    print('DynamoDB: '+str(len(responsedata)))

    # Extract domain values from zip matches
    zip_domains = set(matches)
    
    # Extract domain values from DynamoDB response
    dynamodb_domains = set(i.get('domain') for i in responsedata if 'domain' in i)

    # Items in zip but not in DynamoDB - INSERT
    to_insert = zip_domains - dynamodb_domains
    ttl = int((datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=30)).timestamp())

    for domain in to_insert:
        parts = domain.split('.')
        tld = parts[-1] if len(parts) > 1 else domain
        sld = parts[-2] if len(parts) > 1 else domain
        sk = f'LUNKER#{item}#{domain}'
        table.put_item(
            Item={
                'pk': 'LUNKER#',
                'sk': sk,
                'domain': domain,
                'sld': sld,
                'tld': tld,
                'ttl': ttl,
                'tbl': table_name,
                'search': item
            }
        )
        print(f'Inserted: {domain}')

    # Items in DynamoDB but not in zip - DELETE
    to_delete = dynamodb_domains - zip_domains
    for domain in to_delete:
        sk = f'LUNKER#{item}#{domain}'
        table.delete_item(
            Key={
                'pk': 'LUNKER#',
                'sk': sk
            }
        )
        print(f'Deleted: {domain}')

    print(f'Inserted: {len(to_insert)}, Deleted: {len(to_delete)}')

    return {
        'statusCode': 200,
        'body': json.dumps({
            'inserted': len(to_insert),
            'deleted': len(to_delete)
        })
    }