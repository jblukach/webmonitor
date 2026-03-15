from aws_cdk import (
    Duration,
    RemovalPolicy,
    Stack,
    aws_s3 as _s3
)

from constructs import Construct

class WebmonitorStorage(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        bucket = _s3.Bucket(
            self, 'bucket',
            bucket_name = 'tempwebmonitor',
            encryption = _s3.BucketEncryption.S3_MANAGED,
            block_public_access = _s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy = RemovalPolicy.DESTROY,
            auto_delete_objects = True,
            enforce_ssl = True,
            versioned = False
        )

        bucket.add_lifecycle_rule(
            expiration = Duration.days(1),
            noncurrent_version_expiration = Duration.days(1)
        )
