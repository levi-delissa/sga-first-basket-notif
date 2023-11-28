import json
import os
import boto3
from datetime import datetime, timedelta
from decimal import Decimal


ddb = boto3.resource('dynamodb')
count_table = ddb.Table(os.environ['HITS_TABLE_NAME'])
_lambda = boto3.client('lambda')
micro_expiration_time = (datetime.utcnow() + timedelta(hours=1)).timestamp()
total_expiration_time = (datetime.utcnow() + timedelta(days=7)).timestamp()


def handler(event, context):
    # print('request: {}'.format(json.dumps(event)))

    count_table.update_item(
        Key={'path': event['path']},
        UpdateExpression='ADD hits :incr SET #t = :ttl',
        ExpressionAttributeValues={
            ':incr': 1,
            ':ttl': Decimal(str(micro_expiration_time))
        },
        ExpressionAttributeNames={'#t': 'ttl'},
    )

    count_table.update_item(
        Key={'path': 'grand_total'},
        UpdateExpression='ADD hits :incr SET #t = :ttl',
        ExpressionAttributeValues={
            ':incr': 1,
            ':ttl': Decimal(str(total_expiration_time))
        },
        ExpressionAttributeNames={'#t': 'ttl'},
    )

    resp = _lambda.invoke(
        FunctionName=os.environ['DOWNSTREAM_FUNCTION_NAME'],
        Payload=json.dumps(event),
    )

    body = resp['Payload'].read()
    # print('downstream response: {}'.format(body))
    return json.loads(body)
