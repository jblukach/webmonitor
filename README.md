# webmonitor

webmonitor is an AWS CDK application that ingests domain intelligence feeds, converts them to local SQLite datasets, reconciles findings into DynamoDB, and sends SES alerts for selected insert events.

The system is implemented as scheduled Lambda workflows with organization-scoped read access policies for S3 and DynamoDB.

## What It Does

1. Downloads multiple domains-monitor feed types to S3 as dated CSV files.
2. Converts daily CSV files into SQLite files.
3. Copies a shared DNS SQLite file into a dated osint snapshot.
4. Reads monitored search terms from DynamoDB and runs matching across daily SQLite files.
5. Reconciles insert and delete deltas into per-feed DynamoDB tables.
6. Sends SES notifications for inserts from selected tables.

## Stacks

- WebmonitorStorage
	- Creates S3 bucket temporarywebmonitor.
	- Enforces SSL, blocks public access, and applies 1-day lifecycle expiration.
	- Adds organization-scoped bucket and object read policies using /organization/id.

- WebmonitorDownload
	- Creates Lambda download (Python 3.13, ARM64, 15-minute timeout, 4 GiB ephemeral storage).
	- Creates Secrets Manager secret webmonitor containing token placeholder.
	- Downloads feed types to temporarywebmonitor:
		- dailyupdate, weeklyupdate, monthlyupdate, quarterlyupdate
		- dailyremove, weeklyremove, monthlyremove, quarterlyremove
		- detailed-update, malware
	- Scheduled daily at 01:00 UTC.

- WebmonitorSqlite
	- Creates Lambdas list and make.
	- list scans current-day CSV files and invokes make asynchronously.
	- make builds a domains SQLite database per CSV and uploads dated sqlite3 objects.
	- list also copies dns.sqlite3 from caretakerstaged into YYYY-MM-DD-osint.sqlite3 in temporarywebmonitor.
	- Scheduled daily at 01:15 UTC.

- WebmonitorSearch
	- Creates Lambdas search and searchlist.
	- searchlist pulls search terms from lunker, tracks per-day execution in state, and invokes search for each daily sqlite3 object.
	- search loads optional permutation terms, queries SQLite, and reconciles insert/delete deltas in DynamoDB.
	- Target DynamoDB table is inferred from the SQLite object key suffix.
	- Scheduled daily at 11:15 UTC.

- WebmonitorDynamoDB
	- Creates DynamoDB tables:
		- dailyremove, dailyupdate, weeklyremove, weeklyupdate
		- monthlyremove, monthlyupdate, quarterlyremove, quarterlyupdate
		- malware, osint, state
	- Table settings: on-demand billing, ttl attribute, PITR enabled, stream enabled, deletion protection enabled.
	- Replicates each table to us-east-1 and us-west-2.
	- Creates Lambda action and subscribes DynamoDB streams for dailyremove, dailyupdate, malware, and osint.
	- action resolves recipients from lunker and sends SES raw emails.

- WebmonitorGithub
	- Creates GitHub OIDC provider and IAM role for repo:jblukach/webmonitor:*.
	- Grants deployment and asset publishing permissions used by CI/CD.

## Repository Layout

```text
app.py                      CDK app entrypoint
webmonitor/                 CDK stack definitions
download/download.py        feed downloader Lambda
sqlite/list.py              SQLite orchestration Lambda
sqlite/make.py              CSV to SQLite builder Lambda
search/list.py              search orchestration Lambda
search/search.py            SQLite matcher and DynamoDB reconciler
action/action.py            DynamoDB stream to SES notifier
```

## Prerequisites

- Python 3.13 recommended for local synth/deploy workflows.
- AWS CLI configured for the target account.
- AWS CDK v2 installed.
- CDK bootstrap completed with qualifier lukach in us-east-1, us-east-2, and us-west-2.
- Existing S3 bucket packages-use2-lukach-io containing requests.zip for the Lambda layer.
- Existing SSM parameters:
	- /account/lunker: account id that owns shared lunker and permutation tables.
	- /organization/id: AWS organization id for resource policies.
- Existing DynamoDB table lunker in the account specified by /account/lunker:
	- partition key: pk
	- sort key: sk
	- a GSI with pk as hash key and tk as range key.
- Existing DynamoDB table permutation in the account specified by /account/lunker:
	- partition key: pk
	- sort key: sk
	- optional perm attribute containing related search terms.
- Verified SES identity for hello@lukach.io and/or lukach.io in the deploy region.

## Local Setup

Create and activate a virtual environment, then install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Bootstrap (new account or first-time regions):

```bash
cdk bootstrap --qualifier lukach aws://<ACCOUNT_ID>/us-east-1
cdk bootstrap --qualifier lukach aws://<ACCOUNT_ID>/us-east-2
cdk bootstrap --qualifier lukach aws://<ACCOUNT_ID>/us-west-2
```

## Deploy

Deploy all stacks:

```bash
cdk deploy --all --profile <aws-profile>
```

Useful commands:

```bash
cdk synth
cdk diff
cdk ls
cdk destroy --all --profile <aws-profile>
```

## Post-Deploy Configuration

Update Secrets Manager secret webmonitor with your real domains-monitor token:

```json
{
  "token": "<YOUR_TOKEN>"
}
```

Without this value, the download Lambda cannot fetch upstream feed data.

## Manual Invocation Examples

Invoke downloader:

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

Run searchlist in scheduled mode (all tracked items):

```bash
aws lambda invoke \
  --function-name searchlist \
  --payload '{}' \
  --cli-binary-format raw-in-base64-out \
  /tmp/searchlist.json
```

Run searchlist for a single status value:

```bash
aws lambda invoke \
  --function-name searchlist \
  --payload '{"Status":"example"}' \
  --cli-binary-format raw-in-base64-out \
  /tmp/searchlist-single.json
```

## Data Flow

1. download writes dated CSV files such as YYYY-MM-DD-dailyupdate.csv.
2. sqlite/list triggers sqlite/make to create YYYY-MM-DD-*.sqlite3 files.
3. sqlite/list also copies dns.sqlite3 into YYYY-MM-DD-osint.sqlite3.
4. search/list selects terms, tracks state, then invokes search per sqlite3 file.
5. search reconciles SQLite matches against DynamoDB by inserting new and deleting stale records.
6. DynamoDB stream inserts on selected tables invoke action, which sends SES alerts to lunker recipients.

## CI/CD

GitHub Actions workflow .github/workflows/webmonitor.yaml deploys on push to main and runs on a monthly schedule.

## Operational Notes

- Search includes a previous-day S3 fallback: if a requested dated sqlite3 key is missing, it attempts to copy the prior day key.
- Some IAM policies are broad (resource *). Restrict these to least privilege if required for your environment.
- temporarywebmonitor is intentionally short-lived with a 1-day retention policy.

## License

This project is licensed under Apache License 2.0. See LICENSE.