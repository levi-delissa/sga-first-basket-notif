import json
import os
import boto3
from datetime import datetime, timedelta
from urllib.parse import unquote


ddb = boto3.resource('dynamodb')
data_table = ddb.Table(os.environ['DATA_TABLE_NAME'])
_lambda = boto3.client('lambda')
expiration_time = (datetime.utcnow() + timedelta(hours=2)).timestamp()


def handler(event, context):
    print('request: {}'.format(json.dumps(event)))

    path_data: str = ''
    if len(event['path']):
        path_data = unquote(event['path'][1:])

    response_text: str = ''
    best_book: str = ''
    if len(path_data.split('_')) == 5:
        data = path_data.split('_')
        event_key: str = data[0]
        team: str = data[1]
        player: str = data[2]
        best_odds: str = data[3]
        if ':' in str(best_odds):
            best_odds, best_book = best_odds.split(':')
        fair_odds: str = data[4]
        response_text = (
            f'event_key: {event_key} \n'
            f'team: {team} \n'
            f'player: {player} \n'
            f'best_odds: {best_odds} \n'
            f'best_book: {best_book} \n'
            f'fair_odds: {fair_odds} \n'
        )

        data_table.update_item(
            Key={'event_team_player': f'{event_key}_{team}_{player}'},
            UpdateExpression=(
                'SET #t = :ttl, '
                'best_odds = :best_odds, '
                'fair_odds = :fair_odds, '
                'best_book = :best_book'
            ),
            ExpressionAttributeValues={
                ':ttl': str(expiration_time),
                ':best_odds': str(best_odds),
                ':fair_odds': str(fair_odds),
                ':best_book': str(best_book),
            },
            ExpressionAttributeNames={
                '#t': 'ttl',
            }
        )

    else:
        response_text = 'Unknown problem when parsing event data!'

    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'text/plain'
        },
        'body': f'{response_text}'
    }
