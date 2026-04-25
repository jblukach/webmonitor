import boto3
import datetime
import json
import os
import requests

def handler(event, context):

    secret = boto3.client('secretsmanager')

    getsecret = secret.get_secret_value(
        SecretId = os.environ['SECRET_MGR_ARN']
    )

    login = json.loads(getsecret['SecretString'])

    year = datetime.datetime.now().strftime('%Y')
    month = datetime.datetime.now().strftime('%m')
    day = datetime.datetime.now().strftime('%d')

    headers = {'User-Agent': 'Web Monitor (https://github.com/jblukach/webmonitor)'}

    items = []
    items.append('dailyupdate')
    items.append('weeklyupdate')
    items.append('monthlyupdate')
    items.append('quarterlyupdate')
    items.append('dailyremove')
    items.append('weeklyremove')
    items.append('monthlyremove')
    items.append('quarterlyremove')
    items.append('detailed-update')
    items.append('malware')

    s3 = boto3.resource('s3')

    for item in items:

        print(f'Downloading {item} list...')

        url = 'https://domains-monitor.com/api/v1/'+login['token']+'/get/'+item+'/list/text/'
        response = requests.get(url, headers=headers)
        print(f'HTTP Status Code: {response.status_code}')

        fname = f'{year}-{month}-{day}-{item}.csv'
        fpath = f'/tmp/{fname}'

        f = open(fpath, 'w')
        f.write(response.text)
        f.close()

        s3.meta.client.upload_file(
            fpath,
            os.environ['S3_BUCKET_NAME'],
            fname,
            ExtraArgs = {
                'ContentType': "text/csv"
            }
        )

    os.system('ls -lh /tmp')

    return {
        'statusCode': 200,
        'body': json.dumps('Downloaded!')
    }