from aws_cdk import (
    RemovalPolicy,
    Stack,
    aws_dynamodb as _dynamodb,
    aws_iam as _iam,
    aws_ssm as _ssm
)

from constructs import Construct

class WebmonitorDynamoDB(Stack):

    def _replica_resource_policy(
        self,
        organization_id: str,
        table_name: str,
        region: str
    ) -> _iam.PolicyDocument:
        return _iam.PolicyDocument(
            statements = [
                _iam.PolicyStatement(
                    sid = 'AllowOrganizationGetItemAndQuery',
                    effect = _iam.Effect.ALLOW,
                    principals = [
                        _iam.OrganizationPrincipal(organization_id = organization_id)
                    ],
                    actions = [
                        'dynamodb:GetItem',
                        'dynamodb:Query'
                    ],
                    resources = [
                        self.format_arn(
                            region = region,
                            service = 'dynamodb',
                            resource = 'table',
                            resource_name = table_name
                        ),
                        self.format_arn(
                            region = region,
                            service = 'dynamodb',
                            resource = 'table',
                            resource_name = f'{table_name}/index/*'
                        )
                    ]
                )
            ]
        )

    def _replicas_for_table(
        self,
        organization_id: str,
        table_name: str
    ) -> list[_dynamodb.ReplicaTableProps]:
        return [
            _dynamodb.ReplicaTableProps(
                region = 'us-east-1',
                resource_policy = self._replica_resource_policy(
                    organization_id,
                    table_name,
                    'us-east-1'
                )
            ),
            _dynamodb.ReplicaTableProps(
                region = 'us-west-2',
                resource_policy = self._replica_resource_policy(
                    organization_id,
                    table_name,
                    'us-west-2'
                )
            ),
        ]

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

    ### PARAMETER ###

        organization = _ssm.StringParameter.from_string_parameter_attributes(
            self, 'organization',
            parameter_name = '/organization/id'
        )

    ### DATABASES ###

        dailyremove = _dynamodb.TableV2(
            self, 'dailyremove',
            table_name = 'dailyremove',
            partition_key = {
                'name': 'pk',
                'type': _dynamodb.AttributeType.STRING
            },
            sort_key = {
                'name': 'sk',
                'type': _dynamodb.AttributeType.STRING
            },
            billing = _dynamodb.Billing.on_demand(),
            removal_policy = RemovalPolicy.DESTROY,
            time_to_live_attribute = 'ttl',
            point_in_time_recovery_specification = _dynamodb.PointInTimeRecoverySpecification(
                point_in_time_recovery_enabled = True
            ),
            deletion_protection = True,
            dynamo_stream = _dynamodb.StreamViewType.NEW_AND_OLD_IMAGES,
            replicas = self._replicas_for_table(organization.string_value, 'dailyremove')
        )

        dailyremove.add_to_resource_policy(
            _iam.PolicyStatement(
                sid = 'AllowOrganizationGetItemAndQuery',
                effect = _iam.Effect.ALLOW,
                principals = [
                    _iam.OrganizationPrincipal(organization_id = organization.string_value)
                ],
                actions = [
                    'dynamodb:GetItem',
                    'dynamodb:Query'
                ],
                resources = [
                    self.format_arn(
                        service = 'dynamodb',
                        resource = 'table',
                        resource_name = 'dailyremove'
                    ),
                    self.format_arn(
                        service = 'dynamodb',
                        resource = 'table',
                        resource_name = 'dailyremove/index/*'
                    )
                ]
            )
        )


        dailyupdate = _dynamodb.TableV2(
            self, 'dailyupdate',
            table_name = 'dailyupdate',
            partition_key = {
                'name': 'pk',
                'type': _dynamodb.AttributeType.STRING
            },
            sort_key = {
                'name': 'sk',
                'type': _dynamodb.AttributeType.STRING
            },
            billing = _dynamodb.Billing.on_demand(),
            removal_policy = RemovalPolicy.DESTROY,
            time_to_live_attribute = 'ttl',
            point_in_time_recovery_specification = _dynamodb.PointInTimeRecoverySpecification(
                point_in_time_recovery_enabled = True
            ),
            deletion_protection = True,
            dynamo_stream = _dynamodb.StreamViewType.NEW_AND_OLD_IMAGES,
            replicas = self._replicas_for_table(organization.string_value, 'dailyupdate')
        )

        dailyupdate.add_to_resource_policy(
            _iam.PolicyStatement(
                sid = 'AllowOrganizationGetItemAndQuery',
                effect = _iam.Effect.ALLOW,
                principals = [
                    _iam.OrganizationPrincipal(organization_id = organization.string_value)
                ],
                actions = [
                    'dynamodb:GetItem',
                    'dynamodb:Query'
                ],
                resources = [
                    self.format_arn(
                        service = 'dynamodb',
                        resource = 'table',
                        resource_name = 'dailyupdate'
                    ),
                    self.format_arn(
                        service = 'dynamodb',
                        resource = 'table',
                        resource_name = 'dailyupdate/index/*'
                    )
                ]
            )
        )


        weeklyremove = _dynamodb.TableV2(
            self, 'weeklyremove',
            table_name = 'weeklyremove',
            partition_key = {
                'name': 'pk',
                'type': _dynamodb.AttributeType.STRING
            },
            sort_key = {
                'name': 'sk',
                'type': _dynamodb.AttributeType.STRING
            },
            billing = _dynamodb.Billing.on_demand(),
            removal_policy = RemovalPolicy.DESTROY,
            time_to_live_attribute = 'ttl',
            point_in_time_recovery_specification = _dynamodb.PointInTimeRecoverySpecification(
                point_in_time_recovery_enabled = True
            ),
            deletion_protection = True,
            dynamo_stream = _dynamodb.StreamViewType.NEW_AND_OLD_IMAGES,
            replicas = self._replicas_for_table(organization.string_value, 'weeklyremove')
        )

        weeklyremove.add_to_resource_policy(
            _iam.PolicyStatement(
                sid = 'AllowOrganizationGetItemAndQuery',
                effect = _iam.Effect.ALLOW,
                principals = [
                    _iam.OrganizationPrincipal(organization_id = organization.string_value)
                ],
                actions = [
                    'dynamodb:GetItem',
                    'dynamodb:Query'
                ],
                resources = [
                    self.format_arn(
                        service = 'dynamodb',
                        resource = 'table',
                        resource_name = 'weeklyremove'
                    ),
                    self.format_arn(
                        service = 'dynamodb',
                        resource = 'table',
                        resource_name = 'weeklyremove/index/*'
                    )
                ]
            )
        )


        weeklyupdate = _dynamodb.TableV2(
            self, 'weeklyupdate',
            table_name = 'weeklyupdate',
            partition_key = {
                'name': 'pk',
                'type': _dynamodb.AttributeType.STRING
            },
            sort_key = {
                'name': 'sk',
                'type': _dynamodb.AttributeType.STRING
            },
            billing = _dynamodb.Billing.on_demand(),
            removal_policy = RemovalPolicy.DESTROY,
            time_to_live_attribute = 'ttl',
            point_in_time_recovery_specification = _dynamodb.PointInTimeRecoverySpecification(
                point_in_time_recovery_enabled = True
            ),
            deletion_protection = True,
            dynamo_stream = _dynamodb.StreamViewType.NEW_AND_OLD_IMAGES,
            replicas = self._replicas_for_table(organization.string_value, 'weeklyupdate')
        )

        weeklyupdate.add_to_resource_policy(
            _iam.PolicyStatement(
                sid = 'AllowOrganizationGetItemAndQuery',
                effect = _iam.Effect.ALLOW,
                principals = [
                    _iam.OrganizationPrincipal(organization_id = organization.string_value)
                ],
                actions = [
                    'dynamodb:GetItem',
                    'dynamodb:Query'
                ],
                resources = [
                    self.format_arn(
                        service = 'dynamodb',
                        resource = 'table',
                        resource_name = 'weeklyupdate'
                    ),
                    self.format_arn(
                        service = 'dynamodb',
                        resource = 'table',
                        resource_name = 'weeklyupdate/index/*'
                    )
                ]
            )
        )


        monthlyremove = _dynamodb.TableV2(
            self, 'monthlyremove',
            table_name = 'monthlyremove',
            partition_key = {
                'name': 'pk',
                'type': _dynamodb.AttributeType.STRING
            },
            sort_key = {
                'name': 'sk',
                'type': _dynamodb.AttributeType.STRING
            },
            billing = _dynamodb.Billing.on_demand(),
            removal_policy = RemovalPolicy.DESTROY,
            time_to_live_attribute = 'ttl',
            point_in_time_recovery_specification = _dynamodb.PointInTimeRecoverySpecification(
                point_in_time_recovery_enabled = True
            ),
            deletion_protection = True,
            dynamo_stream = _dynamodb.StreamViewType.NEW_AND_OLD_IMAGES,
            replicas = self._replicas_for_table(organization.string_value, 'monthlyremove')
        )

        monthlyremove.add_to_resource_policy(
            _iam.PolicyStatement(
                sid = 'AllowOrganizationGetItemAndQuery',
                effect = _iam.Effect.ALLOW,
                principals = [
                    _iam.OrganizationPrincipal(organization_id = organization.string_value)
                ],
                actions = [
                    'dynamodb:GetItem',
                    'dynamodb:Query'
                ],
                resources = [
                    self.format_arn(
                        service = 'dynamodb',
                        resource = 'table',
                        resource_name = 'monthlyremove'
                    ),
                    self.format_arn(
                        service = 'dynamodb',
                        resource = 'table',
                        resource_name = 'monthlyremove/index/*'
                    )
                ]
            )
        )


        monthlyupdate = _dynamodb.TableV2(
            self, 'monthlyupdate',
            table_name = 'monthlyupdate',
            partition_key = {
                'name': 'pk',
                'type': _dynamodb.AttributeType.STRING
            },
            sort_key = {
                'name': 'sk',
                'type': _dynamodb.AttributeType.STRING
            },
            billing = _dynamodb.Billing.on_demand(),
            removal_policy = RemovalPolicy.DESTROY,
            time_to_live_attribute = 'ttl',
            point_in_time_recovery_specification = _dynamodb.PointInTimeRecoverySpecification(
                point_in_time_recovery_enabled = True
            ),
            deletion_protection = True,
            dynamo_stream = _dynamodb.StreamViewType.NEW_AND_OLD_IMAGES,
            replicas = self._replicas_for_table(organization.string_value, 'monthlyupdate')
        )

        monthlyupdate.add_to_resource_policy(
            _iam.PolicyStatement(
                sid = 'AllowOrganizationGetItemAndQuery',
                effect = _iam.Effect.ALLOW,
                principals = [
                    _iam.OrganizationPrincipal(organization_id = organization.string_value)
                ],
                actions = [
                    'dynamodb:GetItem',
                    'dynamodb:Query'
                ],
                resources = [
                    self.format_arn(
                        service = 'dynamodb',
                        resource = 'table',
                        resource_name = 'monthlyupdate'
                    ),
                    self.format_arn(
                        service = 'dynamodb',
                        resource = 'table',
                        resource_name = 'monthlyupdate/index/*'
                    )
                ]
            )
        )


        quarterlyremove = _dynamodb.TableV2(
            self, 'quarterlyremove',
            table_name = 'quarterlyremove',
            partition_key = {
                'name': 'pk',
                'type': _dynamodb.AttributeType.STRING
            },
            sort_key = {
                'name': 'sk',
                'type': _dynamodb.AttributeType.STRING
            },
            billing = _dynamodb.Billing.on_demand(),
            removal_policy = RemovalPolicy.DESTROY,
            time_to_live_attribute = 'ttl',
            point_in_time_recovery_specification = _dynamodb.PointInTimeRecoverySpecification(
                point_in_time_recovery_enabled = True
            ),
            deletion_protection = True,
            dynamo_stream = _dynamodb.StreamViewType.NEW_AND_OLD_IMAGES,
            replicas = self._replicas_for_table(organization.string_value, 'quarterlyremove')
        )

        quarterlyremove.add_to_resource_policy(
            _iam.PolicyStatement(
                sid = 'AllowOrganizationGetItemAndQuery',
                effect = _iam.Effect.ALLOW,
                principals = [
                    _iam.OrganizationPrincipal(organization_id = organization.string_value)
                ],
                actions = [
                    'dynamodb:GetItem',
                    'dynamodb:Query'
                ],
                resources = [
                    self.format_arn(
                        service = 'dynamodb',
                        resource = 'table',
                        resource_name = 'quarterlyremove'
                    ),
                    self.format_arn(
                        service = 'dynamodb',
                        resource = 'table',
                        resource_name = 'quarterlyremove/index/*'
                    )
                ]
            )
        )

        quarterlyupdate = _dynamodb.TableV2(
            self, 'quarterlyupdate',
            table_name = 'quarterlyupdate',
            partition_key = {
                'name': 'pk',
                'type': _dynamodb.AttributeType.STRING
            },
            sort_key = {
                'name': 'sk',
                'type': _dynamodb.AttributeType.STRING
            },
            billing = _dynamodb.Billing.on_demand(),
            removal_policy = RemovalPolicy.DESTROY,
            time_to_live_attribute = 'ttl',
            point_in_time_recovery_specification = _dynamodb.PointInTimeRecoverySpecification(
                point_in_time_recovery_enabled = True
            ),
            deletion_protection = True,
            dynamo_stream = _dynamodb.StreamViewType.NEW_AND_OLD_IMAGES,
            replicas = self._replicas_for_table(organization.string_value, 'quarterlyupdate')
        )

        quarterlyupdate.add_to_resource_policy(
            _iam.PolicyStatement(
                sid = 'AllowOrganizationGetItemAndQuery',
                effect = _iam.Effect.ALLOW,
                principals = [
                    _iam.OrganizationPrincipal(organization_id = organization.string_value)
                ],
                actions = [
                    'dynamodb:GetItem',
                    'dynamodb:Query'
                ],
                resources = [
                    self.format_arn(
                        service = 'dynamodb',
                        resource = 'table',
                        resource_name = 'quarterlyupdate'
                    ),
                    self.format_arn(
                        service = 'dynamodb',
                        resource = 'table',
                        resource_name = 'quarterlyupdate/index/*'
                    )
                ]
            )
        )

        full = _dynamodb.TableV2(
            self, 'full',
            table_name = 'full',
            partition_key = {
                'name': 'pk',
                'type': _dynamodb.AttributeType.STRING
            },
            sort_key = {
                'name': 'sk',
                'type': _dynamodb.AttributeType.STRING
            },
            billing = _dynamodb.Billing.on_demand(),
            removal_policy = RemovalPolicy.DESTROY,
            time_to_live_attribute = 'ttl',
            point_in_time_recovery_specification = _dynamodb.PointInTimeRecoverySpecification(
                point_in_time_recovery_enabled = True
            ),
            deletion_protection = True,
            dynamo_stream = _dynamodb.StreamViewType.NEW_AND_OLD_IMAGES,
            replicas = self._replicas_for_table(organization.string_value, 'full')
        )

        full.add_to_resource_policy(
            _iam.PolicyStatement(
                sid = 'AllowOrganizationGetItemAndQuery',
                effect = _iam.Effect.ALLOW,
                principals = [
                    _iam.OrganizationPrincipal(organization_id = organization.string_value)
                ],
                actions = [
                    'dynamodb:GetItem',
                    'dynamodb:Query'
                ],
                resources = [
                    self.format_arn(
                        service = 'dynamodb',
                        resource = 'table',
                        resource_name = 'full'
                    ),
                    self.format_arn(
                        service = 'dynamodb',
                        resource = 'table',
                        resource_name = 'full/index/*'
                    )
                ]
            )
        )

        malware = _dynamodb.TableV2(
            self, 'malware',
            table_name = 'malware',
            partition_key = {
                'name': 'pk',
                'type': _dynamodb.AttributeType.STRING
            },
            sort_key = {
                'name': 'sk',
                'type': _dynamodb.AttributeType.STRING
            },
            billing = _dynamodb.Billing.on_demand(),
            removal_policy = RemovalPolicy.DESTROY,
            time_to_live_attribute = 'ttl',
            point_in_time_recovery_specification = _dynamodb.PointInTimeRecoverySpecification(
                point_in_time_recovery_enabled = True
            ),
            deletion_protection = True,
            dynamo_stream = _dynamodb.StreamViewType.NEW_AND_OLD_IMAGES,
            replicas = self._replicas_for_table(organization.string_value, 'malware')
        )

        malware.add_to_resource_policy(
            _iam.PolicyStatement(
                sid = 'AllowOrganizationGetItemAndQuery',
                effect = _iam.Effect.ALLOW,
                principals = [
                    _iam.OrganizationPrincipal(organization_id = organization.string_value)
                ],
                actions = [
                    'dynamodb:GetItem',
                    'dynamodb:Query'
                ],
                resources = [
                    self.format_arn(
                        service = 'dynamodb',
                        resource = 'table',
                        resource_name = 'malware'
                    ),
                    self.format_arn(
                        service = 'dynamodb',
                        resource = 'table',
                        resource_name = 'malware/index/*'
                    )
                ]
            )
        )

        osint = _dynamodb.TableV2(
            self, 'osint',
            table_name = 'osint',
            partition_key = {
                'name': 'pk',
                'type': _dynamodb.AttributeType.STRING
            },
            sort_key = {
                'name': 'sk',
                'type': _dynamodb.AttributeType.STRING
            },
            billing = _dynamodb.Billing.on_demand(),
            removal_policy = RemovalPolicy.DESTROY,
            time_to_live_attribute = 'ttl',
            point_in_time_recovery_specification = _dynamodb.PointInTimeRecoverySpecification(
                point_in_time_recovery_enabled = True
            ),
            deletion_protection = True,
            dynamo_stream = _dynamodb.StreamViewType.NEW_AND_OLD_IMAGES,
            replicas = self._replicas_for_table(organization.string_value, 'osint')
        )

        osint.add_to_resource_policy(
            _iam.PolicyStatement(
                sid = 'AllowOrganizationGetItemAndQuery',
                effect = _iam.Effect.ALLOW,
                principals = [
                    _iam.OrganizationPrincipal(organization_id = organization.string_value)
                ],
                actions = [
                    'dynamodb:GetItem',
                    'dynamodb:Query'
                ],
                resources = [
                    self.format_arn(
                        service = 'dynamodb',
                        resource = 'table',
                        resource_name = 'osint'
                    ),
                    self.format_arn(
                        service = 'dynamodb',
                        resource = 'table',
                        resource_name = 'osint/index/*'
                    )
                ]
            )
        )

        state = _dynamodb.TableV2(
            self, 'state',
            table_name = 'state',
            partition_key = {
                'name': 'pk',
                'type': _dynamodb.AttributeType.STRING
            },
            sort_key = {
                'name': 'sk',
                'type': _dynamodb.AttributeType.STRING
            },
            billing = _dynamodb.Billing.on_demand(),
            removal_policy = RemovalPolicy.DESTROY,
            time_to_live_attribute = 'ttl',
            point_in_time_recovery_specification = _dynamodb.PointInTimeRecoverySpecification(
                point_in_time_recovery_enabled = True
            ),
            deletion_protection = True,
            dynamo_stream = _dynamodb.StreamViewType.NEW_AND_OLD_IMAGES,
            replicas = self._replicas_for_table(organization.string_value, 'state')
        )

        state.add_to_resource_policy(
            _iam.PolicyStatement(
                sid = 'AllowOrganizationGetItemAndQuery',
                effect = _iam.Effect.ALLOW,
                principals = [
                    _iam.OrganizationPrincipal(organization_id = organization.string_value)
                ],
                actions = [
                    'dynamodb:GetItem',
                    'dynamodb:Query'
                ],
                resources = [
                    self.format_arn(
                        service = 'dynamodb',
                        resource = 'table',
                        resource_name = 'state'
                    ),
                    self.format_arn(
                        service = 'dynamodb',
                        resource = 'table',
                        resource_name = 'state/index/*'
                    )
                ]
            )
        )
