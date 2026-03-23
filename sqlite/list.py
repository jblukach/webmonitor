import boto3
import datetime
import json
import os

def handler(event, context):

    year = datetime.datetime.now().strftime('%Y')
    month = datetime.datetime.now().strftime('%m')
    day = datetime.datetime.now().strftime('%d')

    s3_client = boto3.client('s3')
    lambda_client = boto3.client('lambda')

    objects = s3_client.list_objects(
        Bucket = os.environ['S3_BUCKET']
    )

    for key in objects['Contents']:

        if key['Key'].startswith(f'{year}-{month}-{day}-') and key['Key'].endswith('.csv'):

            if key['Size'] != 0 and 'detailed-update' not in key['Key']:
                
                print(key['Key'])

                lambda_client.invoke(
                    FunctionName = os.environ['MAKE_FUNCTION_NAME'],
                    InvocationType = 'Event',
                    Payload = json.dumps({
                        'Key': key['Key']
                    })
                )

    return {
        'statusCode': 200,
        'body': json.dumps('List Files!')
    }