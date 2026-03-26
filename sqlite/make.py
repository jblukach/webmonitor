import boto3
import json
import os
import sqlite3

def handler(event, context):

    print(event)

    key = event.get('Key')
    fname = key.split('.')[0]

    s3_client = boto3.client('s3')
    s3_client.download_file(os.environ['S3_BUCKET'], key, '/tmp/'+key)

    if os.path.exists('/tmp/'+fname+'.sqlite3'):
        os.remove('/tmp/'+fname+'.sqlite3')

    db = sqlite3.connect('/tmp/'+fname+'.sqlite3')
    db.execute('CREATE TABLE IF NOT EXISTS domains (pk INTEGER PRIMARY KEY, domain TEXT)')
    db.execute('CREATE INDEX domain_index ON domains (domain)')

    f = open('/tmp/'+key, 'r')
    data = f.read()
    f.close()

    datas = data.split('\n')

    for data in datas:
        db.execute('INSERT INTO domains (domain) VALUES (?)', (data,))

    db.commit()
    db.close()

    s3_resource = boto3.resource('s3')

    s3_resource.meta.client.upload_file(
        '/tmp/'+fname+'.sqlite3',
        os.environ['S3_BUCKET'],
        fname+'.sqlite3',
        ExtraArgs = {
            'ContentType': "application/x-sqlite3"
        }
    )

    os.system('ls -lh /tmp')

    return {
        'statusCode': 200,
        'body': json.dumps('Make SQLite!')
    }