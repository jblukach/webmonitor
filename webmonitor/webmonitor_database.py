from aws_cdk import (
    RemovalPolicy,
    Stack,
    aws_s3tables_alpha as _tables,
)

from constructs import Construct

class WebmonitorDatabase(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        table = _tables.TableBucket(
            self, 'table',
            table_bucket_name = 'webmonitor',
            removal_policy = RemovalPolicy.RETAIN,
            unreferenced_file_removal = _tables.UnreferencedFileRemoval(
                status = _tables.UnreferencedFileRemovalStatus.ENABLED,
                noncurrent_days = 14,
                unreferenced_days = 7
            )
        )
