# webmonitor

webmonitor is an AWS CDK application that downloads domain intelligence feeds, converts them into dated SQLite datasets, reconciles matches into DynamoDB, and sends SES alerts for selected new records.

All stacks are instantiated in `us-east-2` from `app.py`. DynamoDB tables are then replicated to `us-east-1` and `us-west-2` where configured.

## Overview

The scheduled workflow is:

1. Download Domains Monitor feeds into S3 as `YYYY-MM-DD-*.csv` objects.
2. Convert each CSV into a corresponding `YYYY-MM-DD-*.sqlite3` database.
3. Copy a shared `dns.sqlite3` snapshot from `caretakerstaged` into the working bucket as `YYYY-MM-DD-osint.sqlite3`.
4. Read monitored search terms from the shared `lunker` table and invoke the search worker for each current-day SQLite object.
5. Reconcile SQLite matches against per-feed DynamoDB tables by inserting new domains and deleting stale ones.
6. Send SES email alerts from DynamoDB stream inserts on selected tables.

## Stacks

### `WebmonitorStorage`

- Creates S3 bucket `temporarywebmonitor`.
- Enables S3-managed encryption, blocks public access, enforces SSL, and expires objects after 1 day.
- Adds organization-scoped `s3:ListBucket` and `s3:GetObject` bucket policies using SSM parameter `/organization/id`.

### `WebmonitorDownload`

- Creates Lambda `download` using Python 3.13 on ARM64.
- Uses a prebuilt Lambda layer from `s3://packages-use2-lukach-io/requests.zip`.
- Creates Secrets Manager secret `webmonitor` with a placeholder `token` value.
- Downloads these feed types into `temporarywebmonitor`:
  - `dailyupdate`, `weeklyupdate`, `monthlyupdate`, `quarterlyupdate`
  - `dailyremove`, `weeklyremove`, `monthlyremove`, `quarterlyremove`
  - `detailed-update`, `malware`
- Runs daily at `01:00 UTC`.

### `WebmonitorSqlite`

- Creates Lambdas `list` and `make` from the `sqlite/` package.
- `list` scans current-day CSV objects and invokes `make` asynchronously for each file.
- `make` converts CSV rows into SQLite databases and uploads `YYYY-MM-DD-*.sqlite3` objects.
- `list` also copies `dns.sqlite3` from bucket `caretakerstaged` into `temporarywebmonitor` as `YYYY-MM-DD-osint.sqlite3`.
- Runs daily at `01:15 UTC`.

### `WebmonitorSearch`

- Creates Lambda `search` and Lambda `searchlist`.
- `searchlist` reads monitored values from the shared `lunker` table, records daily execution state in `state`, and invokes `search` for each current-day SQLite object.
- `search` optionally loads permutations from the shared `permutation` table, searches the SQLite database, and reconciles insert and delete deltas into the target DynamoDB table inferred from the S3 object key suffix.
- For missing dated SQLite objects, `search` falls back to the previous day by copying the prior key in S3 when available.
- Runs daily at `11:15 UTC`.

### `WebmonitorDynamoDB`

- Creates DynamoDB tables:
  - `dailyremove`, `dailyupdate`, `weeklyremove`, `weeklyupdate`
  - `monthlyremove`, `monthlyupdate`, `quarterlyremove`, `quarterlyupdate`
  - `malware`, `osint`, `state`
- Tables use on-demand billing, `ttl` for expiration, point-in-time recovery, DynamoDB streams, and deletion protection.
- Replicates each table to `us-east-1` and `us-west-2`.
- Creates Lambda `action` and subscribes DynamoDB streams for `dailyremove`, `dailyupdate`, `malware`, and `osint`.
- `action` looks up recipients in `lunker` by `pk/tk` GSI and sends SES raw email notifications.

### `WebmonitorGithub`

- Creates a GitHub OIDC provider for `https://token.actions.githubusercontent.com`.
- Creates an IAM role trust for `repo:jblukach/webmonitor:*`.
- Grants the permissions needed for GitHub Actions CDK deployment and asset publishing.

## Repository Layout

```text
app.py                      CDK app entrypoint
webmonitor/                 CDK stack definitions
download/download.py        feed downloader Lambda
sqlite/list.py              SQLite orchestration Lambda
sqlite/make.py              CSV-to-SQLite builder Lambda
search/list.py              search orchestration Lambda
search/search.py            SQLite matcher and DynamoDB reconciler
action/action.py            DynamoDB stream to SES notifier
```

## Requirements

This repository depends on both code in this repo and shared infrastructure that already exists.

### Local tooling

- Python `3.13`
- AWS CLI configured for the target account
- AWS CDK v2 CLI installed separately, for example `npm install -g aws-cdk`
- GitHub Actions runner capacity that matches `codebuild-webmonitor-*` labels (for repository CI/CD)

### Bootstrapped CDK environments

Bootstrap with qualifier `lukach` in:

- `us-east-2` for the primary stacks
- `us-east-1` and `us-west-2` for replicated DynamoDB resources and CDK assets

### Shared resources and parameters

- S3 bucket `packages-use2-lukach-io` containing `requests.zip`
- S3 bucket `caretakerstaged` containing `dns.sqlite3`
- SSM parameter `/account/lunker` with the AWS account ID that owns the shared `lunker` and `permutation` tables
- SSM parameter `/organization/id` with the AWS Organization ID used in bucket and table resource policies

### Shared DynamoDB tables

The account referenced by `/account/lunker` must already contain:

- `lunker`
  - partition key `pk`
  - sort key `sk`
  - a GSI with `pk` as the hash key and `tk` as the range key
- `permutation`
  - partition key `pk`
  - sort key `sk`
  - optional `perm` attribute containing related search terms

### SES prerequisites

- Verified SES identity for `hello@lukach.io` and/or domain identity `lukach.io` in `us-east-2`
- The `action` Lambda sender defaults are set by stack configuration, so changing sender identity requires a stack/code change

## Local Setup

Create and activate a virtual environment, then install Python dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Install the CDK CLI if it is not already available:

```bash
npm install -g aws-cdk
```

Bootstrap the required regions:

```bash
cdk bootstrap --qualifier lukach aws://<ACCOUNT_ID>/us-east-1
cdk bootstrap --qualifier lukach aws://<ACCOUNT_ID>/us-east-2
cdk bootstrap --qualifier lukach aws://<ACCOUNT_ID>/us-west-2
```

## Deploy

The application always synthesizes stacks for `us-east-2`, using `CDK_DEFAULT_ACCOUNT` for the account. Deploy all stacks with:

```bash
cdk deploy --all --profile <aws-profile>
```

Useful commands:

```bash
cdk ls
cdk synth
cdk diff --profile <aws-profile>
cdk destroy --all --profile <aws-profile>
```

## Post-Deploy Configuration

Update Secrets Manager secret `webmonitor` with your real Domains Monitor token:

```json
{
  "token": "<YOUR_TOKEN>"
}
```

Without this value, the download Lambda cannot fetch upstream feed data.

## Manual Operations

Invoke the download Lambda:

```bash
DOWNLOAD_FN=$(aws lambda list-functions \
  --query "Functions[?starts_with(FunctionName, 'WebmonitorDownload') && ends_with(FunctionName, 'download')].FunctionName | [0]" \
  --output text)

aws lambda invoke \
  --function-name "$DOWNLOAD_FN" \
  --payload '{}' \
  --cli-binary-format raw-in-base64-out \
  /tmp/download.json
```

Run `searchlist` in scheduled mode for all tracked items:

```bash
aws lambda invoke \
  --function-name searchlist \
  --payload '{}' \
  --cli-binary-format raw-in-base64-out \
  /tmp/searchlist.json
```

Run `searchlist` for a single status or search term:

```bash
aws lambda invoke \
  --function-name searchlist \
  --payload '{"Status":"example"}' \
  --cli-binary-format raw-in-base64-out \
  /tmp/searchlist-single.json
```

## Data Flow

1. `download` writes dated CSV files such as `YYYY-MM-DD-dailyupdate.csv`.
2. `sqlite/list` invokes `sqlite/make` to build `YYYY-MM-DD-*.sqlite3` objects.
3. `sqlite/list` copies `dns.sqlite3` into `YYYY-MM-DD-osint.sqlite3`.
4. `searchlist` selects search terms, records state, and invokes `search` once per SQLite object.
5. `search` compares SQLite results with DynamoDB and inserts or deletes rows as needed.
6. DynamoDB stream inserts on selected tables invoke `action`, which looks up recipients and sends SES email.

## CI/CD

GitHub Actions workflow `.github/workflows/webmonitor.yaml`:

- deploys on every push to `main`
- runs on a monthly schedule at `02:00 UTC` on the first day of the month
- assumes the IAM role stored in GitHub secret `ROLE`
- installs CDK globally, installs Python dependencies, and runs `cdk deploy --all --require-approval never`

## Operational Notes

- The primary deployment region is hard-coded to `us-east-2` in `app.py`.
- S3 bucket name `temporarywebmonitor` is fixed in code and must be globally unique across AWS.
- `temporarywebmonitor` is intentionally short-lived and configured for 1-day retention.
- The search worker uses SQLite FTS when available and falls back to `LIKE` queries for short search terms.
- Some IAM policies remain broad (`resources = ['*']`). Tighten them if you need stricter least-privilege controls.

## Quick Runbook

1. Validate CDK bootstrap.
Run:
```bash
cdk bootstrap --qualifier lukach aws://<ACCOUNT_ID>/us-east-1
cdk bootstrap --qualifier lukach aws://<ACCOUNT_ID>/us-east-2
cdk bootstrap --qualifier lukach aws://<ACCOUNT_ID>/us-west-2
```

2. Validate download dependencies.
Check that secret `webmonitor` has a non-empty `token`, and confirm `s3://packages-use2-lukach-io/requests.zip` exists.

3. Validate search dependencies.
Confirm `/account/lunker` points to the correct account and table `lunker` has a GSI with hash key `pk` and range key `tk`.

4. Validate alerting prerequisites.
Confirm `hello@lukach.io` and/or domain identity `lukach.io` is verified in SES for `us-east-2`.

5. Validate daily data availability.
Confirm `caretakerstaged/dns.sqlite3` exists and daily objects matching `YYYY-MM-DD-*.csv` are present in `temporarywebmonitor`.

## License

This project is licensed under Apache License 2.0. See `LICENSE`.