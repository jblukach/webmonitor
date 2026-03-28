from aws_cdk import (
    Duration,
    RemovalPolicy,
    Size,
    Stack,
    aws_iam as _iam,
    aws_lambda as _lambda,
    aws_logs as _logs
)

from constructs import Construct

class WebmonitorZiplist(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

    ### IAM ROLE ###

        role = _iam.Role(
            self, 'role',
            assumed_by = _iam.ServicePrincipal(
                'lambda.amazonaws.com'
            )
        )

        role.add_managed_policy(
            _iam.ManagedPolicy.from_aws_managed_policy_name(
                'service-role/AWSLambdaBasicExecutionRole'
            )
        )

        role.add_to_policy(
            _iam.PolicyStatement(
                actions = [
                    'dynamodb:DeleteItem',
                    'dynamodb:PutItem',
                    'dynamodb:Query'
                ],
                resources = [
                    '*'
                ]
            )
        )

        role.add_to_policy(
            _iam.PolicyStatement(
                actions = [
                    's3:GetObject'
                ],
                resources = [
                    '*'
                ]
            )
        )

    ### LAMBDA FUNCTION ###

        ziplist = _lambda.Function(
            self, 'ziplist',
            function_name = 'ziplist',
            runtime = _lambda.Runtime.PYTHON_3_13,
            architecture = _lambda.Architecture.ARM_64,
            code = _lambda.Code.from_asset('ziplist'),
            handler = 'ziplist.handler',
            environment = dict(
                S3_BUCKET = 'temporarywebmonitor'
            ),
            ephemeral_storage_size = Size.gibibytes(4),
            timeout = Duration.seconds(900),
            memory_size = 3008,
            role = role
        )

        logs = _logs.LogGroup(
            self, 'logs',
            log_group_name = '/aws/lambda/'+ziplist.function_name,
            retention = _logs.RetentionDays.ONE_WEEK,
            removal_policy = RemovalPolicy.DESTROY
        )
