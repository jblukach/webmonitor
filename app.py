#!/usr/bin/env python3
import os

import aws_cdk as cdk

from webmonitor.webmonitor_stackuse1 import WebmonitorStackUse1
from webmonitor.webmonitor_stackuse2 import WebmonitorStackUse2
from webmonitor.webmonitor_stackusw2 import WebmonitorStackUsw2

app = cdk.App()

WebmonitorStackUse1(
    app, 'WebmonitorStackUse1',
    env = cdk.Environment(
        account = os.getenv('CDK_DEFAULT_ACCOUNT'),
        region = 'us-east-1'
    ),
    synthesizer = cdk.DefaultStackSynthesizer(
        qualifier = 'lukach'
    )
)

WebmonitorStackUse2(
    app, 'WebmonitorStackUse2',
    env = cdk.Environment(
        account = os.getenv('CDK_DEFAULT_ACCOUNT'),
        region = 'us-east-2'
    ),
    synthesizer = cdk.DefaultStackSynthesizer(
        qualifier = 'lukach'
    )
)

WebmonitorStackUsw2(
    app, 'WebmonitorStackUsw2',
    env = cdk.Environment(
        account = os.getenv('CDK_DEFAULT_ACCOUNT'),
        region = 'us-west-2'
    ),
    synthesizer = cdk.DefaultStackSynthesizer(
        qualifier = 'lukach'
    )
)

cdk.Tags.of(app).add('Alias','webmonitor')
cdk.Tags.of(app).add('GitHub','https://github.com/jblukach/webmonitor')
cdk.Tags.of(app).add('Org','lukach.io')

app.synth()