from aws_cdk import (
    Duration,
    RemovalPolicy,
    Size,
    Stack,
    aws_events as _events,
    aws_events_targets as _targets,
    aws_iam as _iam,
    aws_lambda as _lambda,
    aws_logs as _logs,
    aws_ssm as _ssm
)

from constructs import Construct

class WebmonitorSearch(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        region = Stack.of(self).region

    ### PARAMETERS ###

        lunker = _ssm.StringParameter.from_string_parameter_attributes(
            self, 'lunker',
            parameter_name = '/account/lunker'
        )

        organization = _ssm.StringParameter.from_string_parameter_attributes(
            self, 'organization',
            parameter_name = '/organization/id'
        )

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
                    'dynamodb:GetItem',
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
                    's3:GetObject',
                    's3:ListBucket'
                ],
                resources = [
                    '*'
                ]
            )
        )

        role.add_to_policy(
            _iam.PolicyStatement(
                actions = [
                    'lambda:InvokeFunction'
                ],
                resources = [
                    '*'
                ]
            )
        )

    ### LAMBDA FUNCTION ###

        search = _lambda.Function(
            self, 'search',
            runtime = _lambda.Runtime.PYTHON_3_13,
            architecture = _lambda.Architecture.ARM_64,
            code = _lambda.Code.from_asset('search'),
            handler = 'search.handler',
            environment = dict(
                S3_BUCKET = 'temporarywebmonitor'
            ),
            ephemeral_storage_size = Size.gibibytes(4),
            timeout = Duration.seconds(900),
            memory_size = 3008,
            role = role
        )

        searchlogs = _logs.LogGroup(
            self, 'searchlogs',
            log_group_name = '/aws/lambda/'+search.function_name,
            retention = _logs.RetentionDays.ONE_WEEK,
            removal_policy = RemovalPolicy.DESTROY
        )

        list = _lambda.Function(
            self, 'list',
            function_name = 'searchlist',
            runtime = _lambda.Runtime.PYTHON_3_13,
            architecture = _lambda.Architecture.ARM_64,
            code = _lambda.Code.from_asset('search'),
            handler = 'list.handler',
            environment = dict(
                DYNAMODB_TABLE = 'arn:aws:dynamodb:'+region+':'+lunker.string_value+':table/lunker',
                S3_BUCKET = 'temporarywebmonitor',
                SEARCH_FUNCTION_NAME = search.function_name,
                STATE_TABLE = 'state'
            ),
            timeout = Duration.seconds(900),
            memory_size = 256,
            role = role
        )

        composite = _iam.CompositePrincipal(
            _iam.OrganizationPrincipal(organization.string_value),
            _iam.ServicePrincipal('apigateway.amazonaws.com')
        )

        list.grant_invoke_composite_principal(composite)

        listlogs = _logs.LogGroup(
            self, 'listlogs',
            log_group_name = '/aws/lambda/'+list.function_name,
            retention = _logs.RetentionDays.ONE_WEEK,
            removal_policy = RemovalPolicy.DESTROY
        )

        event = _events.Rule(
            self, 'event',
            schedule = _events.Schedule.cron(
                minute = '15',
                hour = '11',
                month = '*',
                week_day = '*',
                year = '*'
            )
        )

        event.add_target(
            _targets.LambdaFunction(list)
        )
