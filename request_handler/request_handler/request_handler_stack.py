from constructs import Construct
from aws_cdk import (
    Stack,
    aws_lambda as _lambda,
    aws_apigateway as apigw,
    aws_dynamodb as ddb,
)
from .hitcounter import HitCounter


class RequestHandlerStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        data_table = ddb.Table(
            self, 'sga-notif-data',
            partition_key={
                'name': 'event_team_player',
                'type': ddb.AttributeType.STRING
            },
            time_to_live_attribute='ttl',
        )

        published_table = ddb.Table(
            self, 'sga-notif-published',
            partition_key={
                'name': 'event_team_player',
                'type': ddb.AttributeType.STRING
            },
            time_to_live_attribute='ttl',
        )

        update_lambda = _lambda.Function(
            self,
            'ReceiveUpdatesHandler',
            runtime=_lambda.Runtime.PYTHON_3_11,
            code=_lambda.Code.from_asset('lambda'),
            handler='receive_updates.handler',
            environment={
                'DATA_TABLE_NAME': data_table.table_name,
            }
        )

        notif_lambda = _lambda.Function(
            self,
            'PublishHandler',
            runtime=_lambda.Runtime.PYTHON_3_11,
            code=_lambda.Code.from_asset('lambda'),
            handler='publish_notifications.handler',
            environment={
                'DATA_TABLE_NAME': data_table.table_name,
                'PUBLISHED_TABLE_NAME': published_table.table_name,
            },
            memory_size=256,
        )

        update_with_counter = HitCounter(
            self, 'SGAHitCounter',
            downstream=update_lambda,
        )

        apigw.LambdaRestApi(
            self, 'Endpoint',
            handler=update_with_counter.handler,
        )

        data_table.grant_read_write_data(update_lambda)
        data_table.grant_read_write_data(notif_lambda)
        published_table.grant_read_write_data(notif_lambda)
