"""
setup_history_table.py
------------------------
One-time setup script for AP traffic history storage (Phase 5 dashboard
trend chart). Does two things:

1. Creates CampusNetSim_APHistory -- a new table, separate from
   CampusNetSim_APState, keyed on (ap_id, timestamp) so a Query for one
   AP returns its readings in time order. On-demand billing, no capacity
   to plan for at this scale. TTL is enabled on `expires_at` so old
   readings age out on their own (default 24h of retention -- see
   HISTORY_RETENTION_HOURS) instead of needing a cleanup job.

2. Turns on a DynamoDB Stream (NEW_IMAGE) on the existing
   CampusNetSim_APState table, if it isn't already on. history_writer
   (lambda/history_writer) subscribes to that stream and is what
   actually populates APHistory -- this script only flips the table
   setting on, it doesn't touch event_processor at all. That's
   deliberate: event_processor's deployed code doesn't match what's in
   this repo (see docs/api.md / the dashboard handoff notes), so this
   history feature is built to need zero changes to it.

Requires the AWS CLI to be configured first (`aws configure`), same as
seed_dynamodb.py.

Usage:
    python -m infrastructure.setup_history_table
"""

import boto3
from botocore.exceptions import ClientError

REGION = "ap-south-1"
STATE_TABLE_NAME = "CampusNetSim_APState"
HISTORY_TABLE_NAME = "CampusNetSim_APHistory"
HISTORY_RETENTION_HOURS = 24


def ensure_history_table(dynamodb_client):
    try:
        dynamodb_client.create_table(
            TableName=HISTORY_TABLE_NAME,
            AttributeDefinitions=[
                {"AttributeName": "ap_id", "AttributeType": "S"},
                {"AttributeName": "timestamp", "AttributeType": "S"},
            ],
            KeySchema=[
                {"AttributeName": "ap_id", "KeyType": "HASH"},
                {"AttributeName": "timestamp", "KeyType": "RANGE"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        print(f"Creating {HISTORY_TABLE_NAME} ...")
        dynamodb_client.get_waiter("table_exists").wait(TableName=HISTORY_TABLE_NAME)
        print(f"  {HISTORY_TABLE_NAME} created.")
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceInUseException":
            print(f"  {HISTORY_TABLE_NAME} already exists, skipping create.")
        else:
            raise

    dynamodb_client.update_time_to_live(
        TableName=HISTORY_TABLE_NAME,
        TimeToLiveSpecification={"Enabled": True, "AttributeName": "expires_at"},
    )
    print(f"  TTL enabled on {HISTORY_TABLE_NAME}.expires_at ({HISTORY_RETENTION_HOURS}h retention).")


def ensure_state_table_stream(dynamodb_client):
    desc = dynamodb_client.describe_table(TableName=STATE_TABLE_NAME)["Table"]
    stream_spec = desc.get("StreamSpecification", {})

    if stream_spec.get("StreamEnabled"):
        stream_arn = desc["LatestStreamArn"]
        print(f"  Stream already enabled on {STATE_TABLE_NAME}.")
        print(f"  Stream ARN: {stream_arn}")
        return stream_arn

    dynamodb_client.update_table(
        TableName=STATE_TABLE_NAME,
        StreamSpecification={"StreamEnabled": True, "StreamViewType": "NEW_IMAGE"},
    )
    dynamodb_client.get_waiter("table_exists").wait(TableName=STATE_TABLE_NAME)
    stream_arn = dynamodb_client.describe_table(TableName=STATE_TABLE_NAME)["Table"]["LatestStreamArn"]
    print(f"  Stream enabled on {STATE_TABLE_NAME}.")
    print(f"  Stream ARN: {stream_arn}")
    return stream_arn


def setup():
    client = boto3.client("dynamodb", region_name=REGION)

    print(f"1. {HISTORY_TABLE_NAME}")
    ensure_history_table(client)

    print(f"\n2. {STATE_TABLE_NAME} stream")
    stream_arn = ensure_state_table_stream(client)

    print(
        "\nDone. Next: create the history_writer Lambda "
        "(lambda/history_writer/lambda_function.py), add the stream ARN "
        f"above as its DynamoDB trigger, and create the history_reader "
        "Lambda + its API Gateway route -- see docs/api.md."
    )
    return stream_arn


if __name__ == "__main__":
    setup()
