"""
lambda_function.py
--------------------
AWS Lambda entry point for AP traffic history. Triggered by a DynamoDB
Stream on CampusNetSim_APState (NEW_IMAGE view) -- runs once per write
event_processor makes, and copies the relevant fields into
CampusNetSim_APHistory as a new (ap_id, timestamp) row.

Deliberately a separate Lambda subscribed to the state table's stream,
rather than a code change inside event_processor: event_processor's
deployed code doesn't match what's committed to this repo (field names
differ -- see docs/api.md, which reflects the live/deployed contract),
so touching it directly risks silently changing the live API's
response shape. Reading its output via a stream needs no changes to it
at all and no knowledge of its internals beyond the item shape it
writes to DynamoDB, which is the same shape GET /aps already returns.

Field names below intentionally match the live API contract
(connected_count, utilization_pct, timestamp) documented in
docs/api.md and confirmed against the real endpoint, not the stale
names in the committed event_processor source.
"""

import time

import boto3
from boto3.dynamodb.types import TypeDeserializer

HISTORY_TABLE_NAME = "CampusNetSim_APHistory"
HISTORY_RETENTION_HOURS = 24

dynamodb = boto3.resource("dynamodb")
history_table = dynamodb.Table(HISTORY_TABLE_NAME)
deserializer = TypeDeserializer()

# Fields worth keeping per history row -- everything else in the state
# item (device_id, event_id, recommendation, ...) is per-event detail
# the trend chart doesn't need.
HISTORY_FIELDS = ["ap_id", "timestamp", "building", "connected_count", "capacity", "utilization_pct", "status"]


def _deserialize(dynamodb_json):
    return {k: deserializer.deserialize(v) for k, v in dynamodb_json.items()}


def lambda_handler(event, context):
    written = 0
    skipped = 0

    for record in event.get("Records", []):
        if record.get("eventName") not in ("INSERT", "MODIFY"):
            continue

        new_image = record.get("dynamodb", {}).get("NewImage")
        if not new_image:
            continue

        item = _deserialize(new_image)

        if "ap_id" not in item or "timestamp" not in item:
            skipped += 1
            continue

        history_item = {field: item[field] for field in HISTORY_FIELDS if field in item}
        history_item["expires_at"] = int(time.time()) + HISTORY_RETENTION_HOURS * 3600

        history_table.put_item(Item=history_item)
        written += 1

    return {"written": written, "skipped": skipped}
