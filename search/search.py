import boto3
import datetime
import json
import os
import sqlite3
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key


_DYNAMODB_RESOURCE = boto3.resource('dynamodb')
_DYNAMODB_CLIENTS = {}


def _get_dynamodb_client(region_name):
    if region_name not in _DYNAMODB_CLIENTS:
        _DYNAMODB_CLIENTS[region_name] = boto3.client('dynamodb', region_name=region_name)
    return _DYNAMODB_CLIENTS[region_name]


def _build_fts_or_query(terms):
    quoted_terms = []
    for term in terms:
        normalized = (term or '').strip()
        if len(normalized) < 3:
            continue
        quoted_terms.append('"' + normalized.replace('"', '""') + '"')
    return ' OR '.join(quoted_terms)


def _sqlite_search_domains(db, search_terms):
    cursor = db.cursor()
    unique_terms = list(dict.fromkeys(t for t in search_terms if t))

    cursor.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='domains_fts'")
    has_fts = cursor.fetchone() is not None

    short_terms = [term for term in unique_terms if len(term.strip()) < 3]

    if has_fts:
        fts_query = _build_fts_or_query(unique_terms)
        has_fts_terms = bool(fts_query)

        if has_fts_terms and short_terms:
            placeholders = ' OR '.join(['domain LIKE ?' for _ in short_terms])
            like_params = ['%' + term + '%' for term in short_terms]
            cursor.execute(
                f"SELECT domain FROM domains WHERE domain IN (SELECT domain FROM domains_fts WHERE domains_fts MATCH ?) UNION SELECT domain FROM domains WHERE {placeholders}",
                [fts_query] + like_params
            )
            return cursor.fetchall()

        if has_fts_terms:
            cursor.execute(
                'SELECT domain FROM domains_fts WHERE domains_fts MATCH ?',
                (fts_query,)
            )
            return cursor.fetchall()

    wildcards = ['%' + term + '%' for term in unique_terms if term.strip()]
    if not wildcards:
        return []

    placeholders = ' OR '.join(['domain LIKE ?' for _ in wildcards])
    cursor.execute(
        f'SELECT domain FROM domains WHERE {placeholders}',
        wildcards
    )
    return cursor.fetchall()


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


def _get_permutations(perm_table_env, normalized_item, region_candidates):
    perm_table_identifiers = []
    if perm_table_env:
        perm_table_identifiers.append(perm_table_env)
        if perm_table_env.startswith('arn:'):
            perm_table_identifiers.append(perm_table_env.split('/')[-1])

    if 'permutation' not in perm_table_identifiers:
        perm_table_identifiers.append('permutation')

    for perm_region in region_candidates:
        perm_client = _get_dynamodb_client(perm_region)

        for table_identifier in perm_table_identifiers:
            try:
                perm_response = perm_client.get_item(
                    TableName=table_identifier,
                    Key={
                        'pk': {'S': 'LUNKER#'},
                        'sk': {'S': 'LUNKER#' + normalized_item}
                    },
                    ProjectionExpression='perm'
                )
            except ClientError as e:
                if e.response.get('Error', {}).get('Code') in ('ResourceNotFoundException', 'ResourceNotFound'):
                    continue
                raise

            perm_item = perm_response.get('Item', {})
            perm_attr = perm_item.get('perm', {})
            if 'L' in perm_attr:
                perms = [v.get('S') for v in perm_attr['L'] if 'S' in v]
            elif 'SS' in perm_attr:
                perms = list(perm_attr['SS'])
            else:
                perms = []

            if perms:
                print(
                    'Permutation table hit: '
                    + table_identifier
                    + ' region=' + perm_region
                    + ' sk=LUNKER#' + normalized_item
                )
                return perms

    return []

def handler(event, _context):
    _ = _context

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

        region_candidates = []
        if perm_table_env.startswith('arn:'):
            arn_parts = perm_table_env.split(':')
            if len(arn_parts) > 3 and arn_parts[3]:
                region_candidates.append(arn_parts[3])
        for region_name in [os.environ.get('AWS_REGION', '').strip(), 'us-east-2']:
            if region_name and region_name not in region_candidates:
                region_candidates.append(region_name)

        perms = _get_permutations(perm_table_env, normalized_item, region_candidates)

        print('Permutations: ' + str(len(perms)))

        search_terms = [item] + list(perms)

        db = sqlite3.connect(db_path)
        db.execute('PRAGMA query_only = ON')
        db.execute('PRAGMA temp_store = MEMORY')
        db.execute('PRAGMA cache_size = -8000')
        cursor = db.cursor()

        if 'osint' in key:

            wildcards = ['%' + term + '%' for term in search_terms if (term or '').strip()]
            if not wildcards:
                rows = []
            else:
                placeholders = ' OR '.join(['artifact LIKE ?' for _ in wildcards])
                cursor.execute(
                    f'SELECT artifact FROM dns WHERE {placeholders}',
                    wildcards
                )
                rows = cursor.fetchall()

        else:

            rows = _sqlite_search_domains(db, search_terms)

        db.close()

        print('Matches: ' + str(len(rows)))

        # Extract table name from key: between last '-' and '.'
        table_name = key.rsplit('-', 1)[-1].rsplit('.', 1)[0]
        
        table = _DYNAMODB_RESOURCE.Table(table_name)

        sk_query = 'LUNKER#' + item + '#'
        
        response = table.query(
            KeyConditionExpression = Key('pk').eq('LUNKER#') & Key('sk').begins_with(sk_query),
            ProjectionExpression = '#d',
            ExpressionAttributeNames = {'#d': 'domain'}
        )
        responsedata = response.get('Items', [])
        while 'LastEvaluatedKey' in response:
            response = table.query(
                KeyConditionExpression = Key('pk').eq('LUNKER#') & Key('sk').begins_with(sk_query),
                ExclusiveStartKey = response['LastEvaluatedKey'],
                ProjectionExpression = '#d',
                ExpressionAttributeNames = {'#d': 'domain'}
            )
            responsedata.extend(response.get('Items', []))

        print('DynamoDB: '+str(len(responsedata)))

        # Extract domain values from SQLite rows
        sqlite_domains = set(row[0] for row in rows)
        
        # Extract domain values from DynamoDB response
        dynamodb_domains = set(item.get('domain') for item in responsedata if 'domain' in item)

        # Items in SQLite but not in DynamoDB - INSERT
        to_insert = sqlite_domains - dynamodb_domains
        ttl = int((datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=30)).timestamp())

        with table.batch_writer() as batch:
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
                print(f'Inserted: {domain}')

        # Items in DynamoDB but not in SQLite - DELETE
        to_delete = dynamodb_domains - sqlite_domains
        with table.batch_writer() as batch:
            for domain in to_delete:
                sk = f'LUNKER#{item}#{domain}'
                batch.delete_item(
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