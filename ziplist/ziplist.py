import boto3
import datetime
import json
import os
import zipfile
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
    items = event.get('Items')
    if items is None:
        item = event.get('Item')
        items = [item] if item else []

    # Keep first-seen order while dropping empty/duplicate items.
    items = list(dict.fromkeys(i for i in items if i))
    if not items:
        raise ValueError('Event must include Item or Items')

    print('Items Count: '+str(len(items))+' Key: '+key)
    print('Items: '+json.dumps(items))

    s3_client = boto3.client('s3')
    bucket = os.environ['S3_BUCKET']
    zip_path = '/tmp/' + key

    _ensure_s3_object_exists(s3_client, bucket, key)
    s3_client.download_file(bucket, key, zip_path)

    try:
        needles = [(item, item.encode('utf-8')) for item in items]
        zip_domains_by_item = {item: set() for item in items}
        with zipfile.ZipFile(zip_path, 'r') as zf:
            for name in zf.namelist():
                with zf.open(name) as f:
                    for line in f:
                        matched_items = [item for item, needle in needles if needle in line]
                        if matched_items:
                            decoded = line.decode('utf-8', errors='ignore').strip()
                            if decoded:
                                for matched_item in matched_items:
                                    zip_domains_by_item[matched_item].add(decoded)

        total_matches = sum(len(v) for v in zip_domains_by_item.values())
        print('Matches: ' + str(total_matches))

        # Extract table name from key: between last '-' and '.'
        table_name = key.rsplit('-', 1)[-1].rsplit('.', 1)[0]
        
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(table_name)
        ttl = int((datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=30)).timestamp())
        summary = {}
        total_inserted = 0
        total_deleted = 0

        for item in items:
            sk_query = 'LUNKER#' + item + '#'

            response = table.query(
                KeyConditionExpression = Key('pk').eq('LUNKER#') & Key('sk').begins_with(sk_query),
                ProjectionExpression = '#domain',
                ExpressionAttributeNames = {'#domain': 'domain'}
            )
            responsedata = response['Items']
            while 'LastEvaluatedKey' in response:
                response = table.query(
                    KeyConditionExpression = Key('pk').eq('LUNKER#') & Key('sk').begins_with(sk_query),
                    ProjectionExpression = '#domain',
                    ExpressionAttributeNames = {'#domain': 'domain'},
                    ExclusiveStartKey = response['LastEvaluatedKey']
                )
                responsedata.extend(response['Items'])

            dynamodb_domains = set(i.get('domain') for i in responsedata if 'domain' in i)
            zip_domains = zip_domains_by_item[item]

            to_insert = zip_domains - dynamodb_domains
            with table.batch_writer(overwrite_by_pkeys=['pk', 'sk']) as batch:
                for domain in to_insert:
                    parts = domain.split('.')
                    tld = parts[-1] if len(parts) > 1 else domain
                    sld = parts[-2] if len(parts) > 1 else domain
                    sk = f'LUNKER#{item}#{domain}'
                    batch.put_item(
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

            to_delete = dynamodb_domains - zip_domains
            with table.batch_writer(overwrite_by_pkeys=['pk', 'sk']) as batch:
                for domain in to_delete:
                    sk = f'LUNKER#{item}#{domain}'
                    batch.delete_item(
                        Key={
                            'pk': 'LUNKER#',
                            'sk': sk
                        }
                    )

            summary[item] = {
                'matches': len(zip_domains),
                'inserted': len(to_insert),
                'deleted': len(to_delete)
            }
            total_inserted += len(to_insert)
            total_deleted += len(to_delete)
            print(f'Item: {item} Matches: {len(zip_domains)} Inserted: {len(to_insert)} Deleted: {len(to_delete)}')

        return {
            'statusCode': 200,
            'body': json.dumps({
                'itemCount': len(items),
                'items': items,
                'inserted': total_inserted,
                'deleted': total_deleted,
                'summary': summary
            })
        }
    finally:
        if os.path.exists(zip_path):
            os.remove(zip_path)
            print(f'Removed temporary file: {zip_path}')