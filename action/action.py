import boto3
import json
import os
from functools import lru_cache
from boto3.dynamodb.conditions import Key


_DYNAMODB_RESOURCE = boto3.resource('dynamodb')
_DYNAMODB_CLIENT = boto3.client('dynamodb')
_SES_CLIENT = boto3.client('ses')


def _table_name_from_arn(table_arn):
    if not table_arn:
        raise ValueError('LUNKER_TABLE must be set')

    if '/table/' in table_arn:
        return table_arn.split('/table/', 1)[1]

    # Backward-compatible: allow plain table names like "lunker".
    return table_arn


def _query_lunker_emails(table, index_name, lookup_value):
    tk_prefix = 'LUNKER#' + lookup_value + '#'
    emails = set()

    response = table.query(
        IndexName=index_name,
        KeyConditionExpression=Key('pk').eq('LUNKER#') & Key('tk').begins_with(tk_prefix),
        ProjectionExpression='email'
    )
    for item in response.get('Items', []):
        email = item.get('email')
        if email:
            emails.add(email)

    while 'LastEvaluatedKey' in response:
        response = table.query(
            IndexName=index_name,
            KeyConditionExpression=Key('pk').eq('LUNKER#') & Key('tk').begins_with(tk_prefix),
            ExclusiveStartKey=response['LastEvaluatedKey'],
            ProjectionExpression='email'
        )
        for item in response.get('Items', []):
            email = item.get('email')
            if email:
                emails.add(email)

    return sorted(emails)


@lru_cache(maxsize=8)
def _get_tk_index_name(table_name, configured_index_name):
    return _resolve_tk_index_name(_DYNAMODB_CLIENT, table_name, configured_index_name)


def _resolve_tk_index_name(dynamodb_client, table_name, configured_index_name):
    if configured_index_name and len(configured_index_name) >= 3:
        return configured_index_name

    response = dynamodb_client.describe_table(TableName=table_name)
    for index in response.get('Table', {}).get('GlobalSecondaryIndexes', []):
        hash_key = None
        range_key = None

        for key_schema in index.get('KeySchema', []):
            if key_schema.get('KeyType') == 'HASH':
                hash_key = key_schema.get('AttributeName')
            elif key_schema.get('KeyType') == 'RANGE':
                range_key = key_schema.get('AttributeName')

        if hash_key == 'pk' and range_key == 'tk':
            return index.get('IndexName')

    raise ValueError('Unable to resolve a Global Secondary Index with pk as HASH and tk as RANGE')


def _defang_domain(domain):
    if not domain:
        return ''
    return domain.replace('.', '[.]')


def _build_raw_email(source, subject, body):
    return '\r\n'.join(
        [
            f'From: {source}',
            f'To: {source}',
            f'Subject: {subject}',
            'MIME-Version: 1.0',
            'Content-Type: text/plain; charset=UTF-8',
            '',
            body,
        ]
    )


def _subject_from_table(table_name):
    if table_name in ('osint', 'malware'):
        return 'Suspect Domain'
    if table_name == 'dailyupdate':
        return 'New Domain'
    if table_name == 'dailyremove':
        return 'Expired Domain'
    return table_name if table_name else 'lunker'

def handler(event, _context):

    print(event)

    table_name = _table_name_from_arn(os.environ['LUNKER_TABLE'])
    configured_index_name = os.environ.get('LUNKER_TK_INDEX')

    lunker_table = _DYNAMODB_RESOURCE.Table(table_name)
    tk_index_name = _get_tk_index_name(table_name, configured_index_name)

    from_email = os.environ.get('SES_FROM', 'hello@lukach.io')

    results = []
    all_emails = set()
    sent_count = 0

    for record in event.get('Records', []):
        if record.get('eventName') == 'INSERT':
            new_image = record.get('dynamodb', {}).get('NewImage', {})
            if new_image and 'sld' in new_image:
                sld = new_image['sld']['S']
                search = new_image.get('search', {}).get('S')
                domain = new_image.get('domain', {}).get('S')
                table = new_image.get('tbl', {}).get('S')
                lookup_value = search or sld

                emails = _query_lunker_emails(lunker_table, tk_index_name, lookup_value)
                all_emails.update(emails)

                print('sld: ' + sld)
                if search:
                    print('search: ' + search)
                if domain:
                    print('domain: ' + domain)
                if table:
                    print('table: ' + table)
                print('emails: ' + str(len(emails)))
                print('email_list: ' + ','.join(emails))

                if emails:
                    subject = _subject_from_table(table)
                    defanged_domain = _defang_domain(domain)
                    body = defanged_domain if defanged_domain else 'N/A'
                    raw_message = _build_raw_email(from_email, subject, body)

                    _SES_CLIENT.send_raw_email(
                        Source=from_email,
                        Destinations=emails,
                        RawMessage={'Data': raw_message}
                    )
                    sent_count += 1
                    print('ses: sent raw email')
                else:
                    print('ses: skipped, no recipients')

                results.append(
                    {
                        'sld': sld,
                        'search': search,
                        'lookup': lookup_value,
                        'email': emails,
                        'subject': table,
                        'body': _defang_domain(domain),
                        'sent': bool(emails)
                    }
                )


    return {
        'statusCode': 200,
        'body': json.dumps(
            {
                'message': 'Action Completed!',
                'email': sorted(all_emails),
                'emails_sent': sent_count,
                'results': results
            }
        )
    }