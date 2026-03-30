# webmonitor

`webmonitor` is an AWS CDK application that ingests domain intelligence feeds, builds searchable datasets, reconciles results into DynamoDB, and sends alert emails for selected events.

The project is designed around scheduled Lambda workflows and organization-scoped data access.

## What It Does

1. Downloads domain-monitor feed files (CSV + full ZIP) into S3.
2. Converts daily CSV files into SQLite snapshots.
3. Loads targeted domains from a source table and executes searches.
4. Reconciles matches into dedicated DynamoDB tables (`insert` / `delete` delta model).
5. Sends SES email alerts on inserts for selected tables.

## Architecture

The CDK app defines these stacks:

- `WebmonitorStorage`
	- Creates S3 bucket `temporarywebmonitor`.
	- Enforces SSL, blocks public access, and applies 1-day lifecycle expiration.
	- Adds org-scoped resource policies (via `/organization/id`) for `ListBucket` / `GetObject`.

- `WebmonitorDownload`
	- Creates `download` Lambda (Python 3.13, ARM64, 15 min timeout, 4 GiB ephemeral storage).
	- Stores API token in Secrets Manager secret `webmonitor`.
	- Downloads domain-monitor list types and full ZIP to S3 bucket `temporarywebmonitor`.
	- Runs daily at `01:00` (cron in `us-east-2`).

- `WebmonitorSqlite`
	- Creates `list` + `make` Lambdas.
	- `list` finds current-day CSV files and invokes `make` asynchronously.
	- `make` turns each CSV into a SQLite DB and uploads it back to S3.
	- Also copies `dns.sqlite3` from `caretakerstaged` into dated `*-osint.sqlite3` in `temporarywebmonitor`.
	- Runs daily at `01:15`.

- `WebmonitorZiplist`
	- Creates `ziplist` Lambda.
	- Scans the dated full ZIP for item matches and reconciles into DynamoDB table `full`.
	- If the requested dated object is missing, it attempts fallback to previous day by copying in S3.

- `WebmonitorSearch`
	- Creates `search` + `searchlist` Lambdas.
	- `searchlist` reads terms from a source DynamoDB table (`lunker`) and tracks daily status in `state`.
	- Invokes `ziplist` for full ZIP search and `search` for each SQLite file.
	- `search` queries SQLite (`domains` or `dns` table depending on dataset) and reconciles results into the target DynamoDB table derived from key name.
	- Runs daily at `11:15`.

- `WebmonitorDynamoDB`
	- Creates DynamoDB tables:
		- `dailyremove`, `dailyupdate`, `weeklyremove`, `weeklyupdate`
		- `monthlyremove`, `monthlyupdate`, `quarterlyremove`, `quarterlyupdate`
		- `full`, `malware`, `osint`, `state`
	- All tables use on-demand billing, TTL (`ttl`), PITR enabled, streams enabled, and deletion protection.
	- Replicates each table to `us-east-1` and `us-west-2`.
	- Creates `action` Lambda and subscribes it to streams from `dailyremove`, `dailyupdate`, `malware`, and `osint`.
	- `action` looks up recipients from the `lunker` table (GSI on `pk` + `tk`) and sends raw SES mail alerts.

- `WebmonitorGithub`
	- Creates GitHub OIDC provider + IAM role for `repo:jblukach/webmonitor:*`.
	- Grants permissions needed for CDK deployments and asset publishing.

## Repository Layout

```text
app.py                    # CDK app entrypoint
webmonitor/               # CDK stack definitions
download/download.py      # Feed downloader Lambda
sqlite/list.py            # SQLite orchestrator Lambda
sqlite/make.py            # CSV -> SQLite builder Lambda
search/list.py            # Search orchestrator Lambda
search/search.py          # SQLite matcher + DynamoDB reconciler
ziplist/ziplist.py        # ZIP matcher + DynamoDB reconciler
action/action.py          # DynamoDB stream -> SES notifications
```

## Prerequisites

- Python 3.13 (or a compatible local version for CDK synth/deploy)
- AWS CLI configured for your target account
- AWS CDK v2
- Bootstrap completed for qualifier `lukach` in target regions (`us-east-1`, `us-east-2`, `us-west-2`)
- Existing S3 bucket for Lambda layer artifact: `packages-use2-lukach-io` with `requests.zip`
- Existing SSM parameters:
	- `/account/lunker` (account ID that owns the `lunker` table)
	- `/organization/id` (AWS Organization ID)
- Existing DynamoDB table `lunker` with a GSI using:
	- hash key: `pk`
	- range key: `tk`
- Verified SES identity for `hello@lukach.io` and/or `lukach.io`

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

If this is a new account/region bootstrap:

```bash
cdk bootstrap --qualifier lukach aws://<ACCOUNT_ID>/us-east-1
cdk bootstrap --qualifier lukach aws://<ACCOUNT_ID>/us-east-2
cdk bootstrap --qualifier lukach aws://<ACCOUNT_ID>/us-west-2
```

## Deploy

Deploy everything:

```bash
cdk deploy --all --profile <aws-profile>
```

Useful CDK commands:

```bash
cdk synth
cdk diff
cdk ls
cdk destroy --all --profile <aws-profile>
```

## Post-Deploy Configuration

Update the generated Secrets Manager secret `webmonitor` with your real domain-monitor API token:

```json
{
	"token": "<YOUR_TOKEN>"
}
```

Without this value, the downloader cannot fetch upstream feed data.

## Manual Invocation Examples

Invoke downloader:

```bash
aws lambda invoke \
	--function-name download \
	--payload '{}' \
	--cli-binary-format raw-in-base64-out \
	/tmp/download.json
```

Run search list in scheduled mode:

```bash
aws lambda invoke \
	--function-name searchlist \
	--payload '{}' \
	--cli-binary-format raw-in-base64-out \
	/tmp/searchlist.json
```

Run search list for a single status/item:

```bash
aws lambda invoke \
	--function-name searchlist \
	--payload '{"Status":"example"}' \
	--cli-binary-format raw-in-base64-out \
	/tmp/searchlist-single.json
```

## Data Flow Summary

1. `download` writes dated files like:
	 - `YYYY-MM-DD-dailyupdate.csv`
	 - `YYYY-MM-DD-full.zip`
2. `sqlite/list` triggers `sqlite/make` to create `YYYY-MM-DD-*.sqlite3` files.
3. `search/list` selects search terms and invokes:
	 - `ziplist` against `YYYY-MM-DD-full.zip` -> table `full`
	 - `search` against each SQLite DB -> table inferred from key suffix
4. Reconciliation logic inserts new matches and deletes stale matches in DynamoDB.
5. DynamoDB stream inserts on selected tables trigger `action`, which sends SES alerts.

## Notes and Operational Considerations

- Lambdas are configured for Python 3.13 and ARM64.
- Several IAM policies in this project currently use broad resource scopes (`*`); tighten them if required by your security posture.
- Storage is intentionally short-lived in `temporarywebmonitor` (1-day expiration).
- Reconciliation code includes previous-day fallback for missing dated S3 objects in `search` and `ziplist` workflows.

## License

This repository is licensed under the terms in `LICENSE`.