import json
import os
import boto3
from datetime import datetime, timedelta
from decimal import Decimal
from discord_webhook import DiscordWebhook


webhook_url: str = "https://discord.com/api/webhooks/1178825840130269215/PGEclTRH1aKe93qp_IQ77q59bJ1A8JuqCCgbRwXk8wsG7JeC1qU_BpxR-lG_ppFeLmGJ"
client = boto3.client('dynamodb')
ddb = boto3.resource('dynamodb')
published_table: ddb.Table = ddb.Table(os.environ['PUBLISHED_TABLE_NAME'])
data_table: ddb.Table = ddb.Table(os.environ['DATA_TABLE_NAME'])
expiration_time = (datetime.utcnow() + timedelta(hours=12)).timestamp()
current_time = datetime.utcnow().timestamp()


def send_email(message_body):
    ses_client = boto3.client("ses")
    subject = "First Basket Model Update"
    body = message_body
    message = {"Subject": {"Data": subject}, "Body": {"Html": {"Data": body}}}
    response = ses_client.send_email(
        Source="first-basket@oddunicycle.com",
        Destination={"ToAddresses": ["levi.delissa@gmail.com", "mlewis8111@gmail.com"]},
        Message=message)


def calc_ev(best_odds, fair_odds):
    # TODO handle negative odds...
    try:
        best = float(best_odds)
        fair = float(fair_odds)
    except:
        return float(-1.0)
    win_p = 100.0 / (fair + 100.0)
    loss_p = 1.0 - win_p
    stake = 10000.0 / best
    exp_win_amt = 100.0 * win_p
    exp_loss_amt = stake * loss_p

    return (exp_win_amt - exp_loss_amt) / stake


def handler(event, context):
    print('request: {}'.format(json.dumps(event)))
    response_text: str = ''

    # query data table
    unpublished_records: dict = {}
    paginator = client.get_paginator('scan')
    for page_idx, page in enumerate(paginator.paginate(
        TableName=os.environ['DATA_TABLE_NAME'],
        Select='ALL_ATTRIBUTES',
        FilterExpression='#t > :current_time',
        ExpressionAttributeNames={'#t': 'ttl'},
        ExpressionAttributeValues={
            ':current_time': {'N': str(current_time)},
        },
    )):
        for record in page['Items']:
            unpublished_records[record['event_team_player']['S']] = {
                'best_odds': record['best_odds']['S'],
                'fair_odds': record['fair_odds']['S'],
                'best_book': record['best_book']['S'],
            }

    # query published table
    published_records: dict = {}
    paginator = client.get_paginator('scan')
    for page_idx, page in enumerate(paginator.paginate(
            TableName=os.environ['PUBLISHED_TABLE_NAME'],
            Select='ALL_ATTRIBUTES',
            FilterExpression='#t > :current_time',
            ExpressionAttributeNames={'#t': 'ttl'},
            ExpressionAttributeValues={
                ':current_time': {'N': str(current_time)},
            },
    )):
        for record in page['Items']:
            published_records[record['event_team_player']['S']] = {
                'best_odds': record['best_odds']['S'],
                'fair_odds': record['fair_odds']['S'],
                'best_book': record['best_book']['S'],
            }

    # compare with notif table
    new_records: list = []
    improved_records: list = []
    for k, v in unpublished_records.items():
        if k not in published_records:
            new_records.append(k)
        else:
            published_best = published_records[k]['best_odds']
            published_fair = published_records[k]['fair_odds']
            current_best = v['best_odds']
            current_fair = v['fair_odds']
            current_ev = calc_ev(current_best, current_fair)
            prior_ev = calc_ev(published_best, published_fair)
            if current_ev >= 0.0 and current_ev > prior_ev:
                improved_records.append(k)

    # send update
    new_records = sorted(new_records)
    improved_records = sorted(improved_records)
    webhook_content: str = ''
    if len(new_records) or len(improved_records):
        msg: str = '''<html>
            <head>
            <style>
                table {
                text-align: center;
                
                border-collapse: collapse;
                margin: 25px 0;
                font-size: 0.9em;
                font-family: sans-serif;
                min-width: 400px;
                box-shadow: 0 0 20px rgba(0, 0, 0, 0.15);
                }
                thead tr {
                    background-color: #009879;
                    color: #ffffff;
                    text-align: center;
                }
                
                th, td {
                    padding: 2px 4px;
                    text-align: center;
                }

                tbody tr:nth-of-type(even) {
                    background-color: #f3f3f3;
                }
            </style>
            </head>
            <body>'''
        if len(improved_records):
            msg += '<h3>IMPROVED</h3><br>'
            msg += '<table>'
            msg += '<tr><th>Team</th><th>Player</th><th>Prior BO</th><th>Current BO</th><th>Prior FO</th><th>Current FO</th><th>Prior EV</th><th>Current EV</th></tr>'
            for r in improved_records:
                event, team, player = r.split('_')
                current_best_odds = float(unpublished_records[r]['best_odds'])
                current_best_book = unpublished_records[r]['best_book']
                prior_best_book = published_records[r]['best_book']
                current_fair_odds = float(unpublished_records[r]['fair_odds'])
                prior_best_odds = float(published_records[r]['best_odds'])
                prior_fair_odds = float(published_records[r]['fair_odds'])
                current_ev = float(calc_ev(current_best_odds, current_fair_odds))
                prior_ev = float(calc_ev(prior_best_odds, prior_fair_odds))
                msg += f'<tr><td>{team}</td><td>{player}</td><td>{round(prior_best_odds)} ({prior_best_book})</td><td>{round(current_best_odds)} ({current_best_book})</td><td>{round(prior_fair_odds)}</td><td>{round(current_fair_odds)}</td><td>{round(100*prior_ev)}%</td><td>{round(100*current_ev)}%</td></tr>'
                webhook_content += f'{team} - {player} - improved:\nnow: {round(current_fair_odds)} ({current_best_book}) - {round(current_fair_odds)} (fair) - {round(current_ev*100)}% EV\nwas: {round(prior_fair_odds)} ({prior_best_book}) - {round(prior_fair_odds)} (fair) - {round(prior_ev*100)}% EV\n\n\n'
            msg += '</table><br><br>'
        if len(new_records):
            msg += '<h3>NEW</h3><br>'
            msg += '<table>'
            msg += '<tr><th>Team</th><th>Player</th><th>Current BO</th><th>Current FO</th><th>Current EV</th></tr>'
            for r in new_records:
                event, team, player = r.split('_')
                current_best_odds = float(unpublished_records[r]['best_odds'])
                current_best_book = unpublished_records[r]['best_book']
                current_fair_odds = float(unpublished_records[r]['fair_odds'])
                current_ev = float(calc_ev(current_best_odds, current_fair_odds))
                msg += f'<tr><td>{team}</td><td>{player}</td><td>{round(current_best_odds)} ({current_best_book})</td><td>{round(current_fair_odds)}</td><td>{round(100*current_ev)}%</td></tr>'
                if current_ev > 0:
                    webhook_content += f'{team} - {player} - new:\nnow: {round(current_fair_odds)} ({current_best_book}) - {round(current_fair_odds)} (fair) - {round(current_ev*100)}% EV\n\n\n'
            msg += '</table><br><br>'
        msg += '</body>'
        print(msg)
        send_email(msg)
        if webhook_content:
            webhook = DiscordWebhook(url=webhook_url, content=webhook_content)
            webhook_response = webhook.execute()

    else:
        print('no updates!')

    # publish records
    for k, v in unpublished_records.items():
        best_odds = v['best_odds']
        fair_odds = v['fair_odds']
        best_book = v['best_book']
        published_table.update_item(
            Key={'event_team_player': k},
            UpdateExpression=(
                'SET #t = :ttl, '
                'best_odds = :best_odds, '
                'fair_odds = :fair_odds, '
                'best_book = :best_book '
            ),
            ExpressionAttributeValues={
                ':ttl': Decimal(str(expiration_time)),
                ':best_odds': str(best_odds),
                ':fair_odds': str(fair_odds),
                ':best_book': str(best_book),
            },
            ExpressionAttributeNames={
                '#t': 'ttl',
            }
        )

    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'text/plain'
        },
        'body': f'{response_text}'
    }
