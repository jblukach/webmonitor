import boto3
import datetime
import json
import os
import sqlite3

def handler(event, context):

    #year = datetime.datetime.now().strftime('%Y')
    #month = datetime.datetime.now().strftime('%m')
    #day = datetime.datetime.now().strftime('%d')

    #s3_client = boto3.client('s3')
    #s3_resource = boto3.resource('s3')

    #objects = s3_client.list_objects(
    #    Bucket = os.environ['S3_BUCKET']
    #)

    #for key in objects['Contents']:

    #    if key['Key'].startswith(f'{year}-{month}-{day}-') and key['Key'].endswith('.csv'):

    #        if key['Size'] != 0 and 'detailed-update' not in key['Key']:

    #            fname = key['Key'].split('.')[0]

    #            s3_client.download_file(os.environ['S3_BUCKET'], key['Key'], '/tmp/'+key['Key'])

    #            if os.path.exists('/tmp/'+fname+'.sqlite3'):
    #                os.remove('/tmp/'+fname+'.sqlite3')

    #            db = sqlite3.connect('/tmp/'+fname+'.sqlite3')
    #            db.execute('CREATE TABLE IF NOT EXISTS domains (pk INTEGER PRIMARY KEY, domain TEXT)')
    #            db.execute('CREATE INDEX domain_index ON domains (domain)')

    #            f = open('/tmp/'+key['Key'], 'r')
    #            data = f.read()
    #            f.close()

    #            datas = data.split('\n')

    #            for data in datas:
    #                db.execute('INSERT INTO domains (domain) VALUES (?)', (data,))

    #            db.commit()
    #            db.close()

    #            s3_resource.meta.client.upload_file(
    #                '/tmp/'+fname+'.sqlite3',
    #                os.environ['S3_BUCKET'],
    #                fname+'.sqlite3',
    #                ExtraArgs = {
    #                    'ContentType': "application/x-sqlite3"
    #                }
    #            )

    #os.system('ls -lh /tmp')

    return {
        'statusCode': 200,
        'body': json.dumps('SQLite Created!')
    }