#!/usr/bin/env python3
import os

import aws_cdk as cdk

from webmonitor.webmonitor_database import WebmonitorDatabase
from webmonitor.webmonitor_download import WebmonitorDownload
from webmonitor.webmonitor_dynamodb import WebmonitorDynamoDB
from webmonitor.webmonitor_github import WebmonitorGithub
from webmonitor.webmonitor_search import WebmonitorSearch
from webmonitor.webmonitor_sqlite import WebmonitorSqlite
from webmonitor.webmonitor_storage import WebmonitorStorage
from webmonitor.webmonitor_zipfile import WebmonitorZipfile

app = cdk.App()

WebmonitorDatabase(
    app, 'WebmonitorDatabase',
    env = cdk.Environment(
        account = os.getenv('CDK_DEFAULT_ACCOUNT'),
        region = 'us-east-2'
    ),
    synthesizer = cdk.DefaultStackSynthesizer(
        qualifier = 'lukach'
    )
)

WebmonitorDownload(
    app, 'WebmonitorDownload',
    env = cdk.Environment(
        account = os.getenv('CDK_DEFAULT_ACCOUNT'),
        region = 'us-east-2'
    ),
    synthesizer = cdk.DefaultStackSynthesizer(
        qualifier = 'lukach'
    )
)

WebmonitorDynamoDB(
    app, 'WebmonitorDynamoDB',
    env = cdk.Environment(
        account = os.getenv('CDK_DEFAULT_ACCOUNT'),
        region = 'us-east-2'
    ),
    synthesizer = cdk.DefaultStackSynthesizer(
        qualifier = 'lukach'
    )
)

WebmonitorGithub(
    app, 'WebmonitorGithub',
    env = cdk.Environment(
        account = os.getenv('CDK_DEFAULT_ACCOUNT'),
        region = 'us-east-2'
    ),
    synthesizer = cdk.DefaultStackSynthesizer(
        qualifier = 'lukach'
    )
)

WebmonitorSearch(
    app, 'WebmonitorSearch',
    env = cdk.Environment(
        account = os.getenv('CDK_DEFAULT_ACCOUNT'),
        region = 'us-east-2'
    ),
    synthesizer = cdk.DefaultStackSynthesizer(
        qualifier = 'lukach'
    )
)

WebmonitorSqlite(
    app, 'WebmonitorSqlite',
    env = cdk.Environment(
        account = os.getenv('CDK_DEFAULT_ACCOUNT'),
        region = 'us-east-2'
    ),
    synthesizer = cdk.DefaultStackSynthesizer(
        qualifier = 'lukach'
    )
)

WebmonitorStorage(
    app, 'WebmonitorStorage',
    env = cdk.Environment(
        account = os.getenv('CDK_DEFAULT_ACCOUNT'),
        region = 'us-east-2'
    ),
    synthesizer = cdk.DefaultStackSynthesizer(
        qualifier = 'lukach'
    )
)

WebmonitorZipfile(
    app, 'WebmonitorZipfile',
    env = cdk.Environment(
        account = os.getenv('CDK_DEFAULT_ACCOUNT'),
        region = 'us-east-2'
    ),
    synthesizer = cdk.DefaultStackSynthesizer(
        qualifier = 'lukach'
    )
)

cdk.Tags.of(app).add('Alias','webmonitor')
cdk.Tags.of(app).add('GitHub','https://github.com/jblukach/webmonitor')
cdk.Tags.of(app).add('Org','lukach.io')

app.synth()