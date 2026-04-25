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
    db.execute('PRAGMA journal_mode = OFF')
    db.execute('PRAGMA synchronous = OFF')
    db.execute('PRAGMA temp_store = MEMORY')
    db.execute('CREATE TABLE IF NOT EXISTS domains (pk INTEGER PRIMARY KEY, domain TEXT NOT NULL UNIQUE)')

    f = open('/tmp/'+key, 'r')
    data = f.read()
    f.close()

    datas = [line.strip() for line in data.split('\n') if line.strip()]

    db.executemany('INSERT OR IGNORE INTO domains (domain) VALUES (?)', ((line,) for line in datas))

    try:
        db.execute("CREATE VIRTUAL TABLE IF NOT EXISTS domains_fts USING fts5(domain, content='domains', content_rowid='pk', tokenize='trigram')")
        db.execute("INSERT INTO domains_fts(domains_fts) VALUES ('rebuild')")
        print('Built FTS index: domains_fts')
    except sqlite3.OperationalError as error:
        # Fallback for runtimes where SQLite is compiled without FTS5/trigram.
        print('FTS index unavailable, continuing without FTS: ' + str(error))

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