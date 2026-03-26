import json

def handler(event, context):

    key = event.get('Key')
    item = event.get('Item')

    print('Key: '+key)
    print('Item: '+item)

    return {
        'statusCode': 200,
        'body': json.dumps('Completed!')
    }