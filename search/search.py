import boto3
import datetime
import json
import os
import sqlite3
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key


def _get_previous_day_key(key):
    if len(key) < 11 or key[4] != '-' or key[7] != '-':
        return None

    try:
        dt = datetime.datetime.strptime(key[:10], '%Y-%m-%d')
    except ValueError:
        return None

    return (dt - datetime.timedelta(days=1)).strftime('%Y-%m-%d') + key[10:]


def _ensure_s3_object_exists(s3_client, bucket, key):
    try:
        s3_client.head_object(Bucket=bucket, Key=key)
        return
    except ClientError as error:
        code = error.response.get('Error', {}).get('Code', '')
        if code not in ('404', 'NoSuchKey', 'NotFound'):
            raise

    previous_day_key = _get_previous_day_key(key)
    if not previous_day_key:
        raise FileNotFoundError(f'S3 object not found and no date prefix available for fallback: {key}')

    try:
        s3_client.head_object(Bucket=bucket, Key=previous_day_key)
    except ClientError as error:
        raise FileNotFoundError(
            f'S3 object not found for requested key {key} or fallback key {previous_day_key}'
        ) from error

    s3_client.copy_object(
        Bucket=bucket,
        CopySource={'Bucket': bucket, 'Key': previous_day_key},
        Key=key
    )
    print(f'Copied previous day object in S3: {previous_day_key} -> {key}')

def handler(event, context):

    key = event.get('Key')
    item = event.get('Item')

    print('Item: '+item+' Key: '+key)

    s3_client = boto3.client('s3')
    bucket = os.environ['S3_BUCKET']
    db_path = '/tmp/' + key

    _ensure_s3_object_exists(s3_client, bucket, key)
    s3_client.download_file(bucket, key, db_path)

    try:
        # Query permutation table for additional search terms.
        # Lunker writes keys as: pk=LUNKER#, sk=LUNKER#<lowercase_sld>, and table is in us-east-2.
        perm_table_env = os.environ.get('DYNAMODB_TABLE', 'permutation').strip()
        normalized_item = (item or '').strip().lower()

        perm_table_candidates = []
        if perm_table_env.startswith('arn:'):
            perm_table_candidates.append(perm_table_env.split('/')[-1])
        elif perm_table_env:
            perm_table_candidates.append(perm_table_env)
        if 'permutation' not in perm_table_candidates:
            perm_table_candidates.append('permutation')

        region_candidates = []
        if perm_table_env.startswith('arn:'):
            arn_parts = perm_table_env.split(':')
            if len(arn_parts) > 3 and arn_parts[3]:
                region_candidates.append(arn_parts[3])
        for region_name in [os.environ.get('AWS_REGION', '').strip(), 'us-east-2']:
            if region_name and region_name not in region_candidates:
                region_candidates.append(region_name)

        perms = []
        for perm_region in region_candidates:
            if perm_table_env.startswith('arn:'):
                perm_client = boto3.client('dynamodb', region_name=perm_region)
                try:
                    perm_response = perm_client.get_item(
                        TableName=perm_table_env,
                        Key={
                            'pk': {'S': 'LUNKER#'},
                            'sk': {'S': 'LUNKER#' + normalized_item}
                        }
                    )
                    perm_item = perm_response.get('Item', {})
                    if 'perm' in perm_item:
                        if 'L' in perm_item['perm']:
                            perms = [v.get('S') for v in perm_item['perm']['L'] if 'S' in v]
                        elif 'SS' in perm_item['perm']:
                            perms = list(perm_item['perm']['SS'])
                except ClientError as e:
                    if e.response.get('Error', {}).get('Code') not in ('ResourceNotFoundException', 'ResourceNotFound'):
                        raise

                if perms:
                    print(
                        'Permutation table hit: '
                        + perm_table_env
                        + ' region=' + perm_region
                        + ' sk=LUNKER#' + normalized_item
                    )
                    break

            perm_dynamodb = boto3.resource('dynamodb', region_name=perm_region)
            for perm_table_name in perm_table_candidates:
                perm_table = perm_dynamodb.Table(perm_table_name)

                try:
                    perm_response = perm_table.get_item(
                        Key={
                            'pk': 'LUNKER#',
                            'sk': 'LUNKER#' + normalized_item
                        }
                    )
                except ClientError as e:
                    if e.response.get('Error', {}).get('Code') in ('ResourceNotFoundException', 'ResourceNotFound'):
                        continue
                    raise

                perm_item = perm_response.get('Item', {})
                candidate_perms = perm_item.get('perm', [])
                if candidate_perms:
                    perms = list(candidate_perms)
                    print(
                        'Permutation table hit: '
                        + perm_table_name
                        + ' region=' + perm_region
                        + ' sk=LUNKER#' + normalized_item
                    )
                    break

            if perms:
                break

        print('Permutations: ' + str(len(perms)))

        search_terms = [item] + list(perms)
        wildcards = ['%' + term + '%' for term in search_terms]

        db = sqlite3.connect(db_path)
        cursor = db.cursor()

        if 'osint' in key:

            placeholders = ' OR '.join(['artifact LIKE ?' for _ in wildcards])
            cursor.execute(
                f'SELECT artifact FROM dns WHERE {placeholders} ORDER BY artifact',
                wildcards
            )

        else:

            placeholders = ' OR '.join(['domain LIKE ?' for _ in wildcards])
            cursor.execute(
                f'SELECT domain FROM domains WHERE {placeholders} ORDER BY domain',
                wildcards
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
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)
            print(f'Removed temporary file: {db_path}')