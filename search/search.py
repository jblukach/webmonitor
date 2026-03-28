import boto3
import datetime
import json
import os
import sqlite3
from boto3.dynamodb.conditions import Key

def handler(event, context):

    key = event.get('Key')
    item = event.get('Item')

    print('Item: '+item+' Key: '+key)

    s3_client = boto3.client('s3')
    s3_client.download_file(os.environ['S3_BUCKET'], key, '/tmp/'+key)

    db_path = '/tmp/' + key
    wildcard = '%' + item + '%'

    db = sqlite3.connect(db_path)
    cursor = db.cursor()

    if 'osint' in key:

        cursor.execute(
            'SELECT artifact FROM dns WHERE artifact LIKE ? ORDER BY artifact',
            (wildcard,)
        )

    else:

        cursor.execute(
            'SELECT domain FROM domains WHERE domain LIKE ? ORDER BY domain',
            (wildcard,)
        )

    rows = cursor.fetchall()
    db.close()

    print('Matches: ' + str(len(rows)))

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

    # Extract domain values from SQLite rows
    sqlite_domains = set(row[0] for row in rows)
    
    # Extract domain values from DynamoDB response
    dynamodb_domains = set(item.get('domain') for item in responsedata if 'domain' in item)

    # Items in SQLite but not in DynamoDB - INSERT
    to_insert = sqlite_domains - dynamodb_domains
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

    # Items in DynamoDB but not in SQLite - DELETE
    to_delete = dynamodb_domains - sqlite_domains
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