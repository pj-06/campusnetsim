import json
import time
from boto3.dynamodb.types import TypeDeserializer
import boto3

HISTORY_TABLE_NAME = "CampusNetSim_APHistory"
HISTORY_RETENTION_HOURS = 24

dynamodb = boto3.resource("dynamodb")
history_table = dynamodb.Table(HISTORY_TABLE_NAME)
deserializer = TypeDeserializer()

HISTORY_FIELDS = ["ap_id", "timestamp", "building", "connected_count", "capacity", "utilization_pct", "status"]


def _deserialize(dynamodb_image):
    return {k: deserializer.deserialize(v) for k, v in dynamodb_image.items()}


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
