
import json
import os
from datetime import datetime, timezone
from decimal import Decimal

import boto3
from botocore.exceptions import ClientError

# --------------------------------------------------
# Configuration
# --------------------------------------------------

TABLE_NAME = os.environ.get(
    "TABLE_NAME", "CampusNetSim_APState"
)

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(TABLE_NAME)

THRESHOLD_BUSY = 70.0
THRESHOLD_HIGH_LOAD = 90.0
THRESHOLD_CONGESTED = 100.0

NORMAL = "NORMAL"
BUSY = "BUSY"
HIGH_LOAD = "HIGH_LOAD"
CONGESTED = "CONGESTED"


# --------------------------------------------------
# Helpers
# --------------------------------------------------

def response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(body, default=str),
    }


def floats_to_decimal(obj):
    """Convert floats to Decimal before writing to DynamoDB."""
    if isinstance(obj, float):
        return Decimal(str(obj))
    if isinstance(obj, dict):
        return {
            key: floats_to_decimal(value)
            for key, value in obj.items()
        }
    if isinstance(obj, list):
        return [floats_to_decimal(value) for value in obj]
    return obj


def status_for_utilization(utilization_pct):
    if utilization_pct >= THRESHOLD_CONGESTED:
        return CONGESTED
    if utilization_pct >= THRESHOLD_HIGH_LOAD:
        return HIGH_LOAD
    if utilization_pct >= THRESHOLD_BUSY:
        return BUSY
    return NORMAL


def load_ap_config():
    """Read current AP capacities, buildings and names from DynamoDB."""
    aps = {}
    scan_args = {}

    while True:
        result = table.scan(**scan_args)

        for item in result.get("Items", []):
            ap_id = item["ap_id"]
            capacity = int(item.get("capacity", 0))

            if capacity < 1:
                raise ValueError(
                    f"Invalid capacity configured for {ap_id}"
                )

            aps[ap_id] = {
                "capacity": capacity,
                "building": item.get("building", "unknown"),
                "ap_name": item.get("ap_name", ap_id),
                "connected_count": int(
                    item.get("connected_count", 0)
                ),
            }

        last_key = result.get("LastEvaluatedKey")
        if not last_key:
            break

        scan_args = {"ExclusiveStartKey": last_key}

    return aps


def recommend_for(congested_ap_id, aps, source_new_count):
    """Recommend an AP with spare capacity, preferring the same building."""
    source = aps[congested_ap_id]
    source_building = source["building"]

    def available(ap_id):
        count = aps[ap_id]["connected_count"]
        if ap_id == congested_ap_id:
            count = source_new_count

        return aps[ap_id]["capacity"] - count

    same_building = [
        ap_id for ap_id, ap in aps.items()
        if ap_id != congested_ap_id
        and ap["building"] == source_building
        and available(ap_id) > 0
    ]

    candidates = same_building or [
        ap_id for ap_id in aps
        if ap_id != congested_ap_id and available(ap_id) > 0
    ]

    if not candidates:
        return None

    best = max(candidates, key=available)
    target = aps[best]
    target_count = target["connected_count"]

    return {
        "recommended_ap_id": best,
        "building": target["building"],
        "available_capacity": available(best),
        "projected_utilization_pct": round(
            ((target_count + 1) / target["capacity"]) * 100,
            2,
        ),
    }


# --------------------------------------------------
# Main Lambda handler
# --------------------------------------------------

def lambda_handler(event, context):
    try:
        # Support API Gateway proxy events and direct Lambda test events.
        if isinstance(event, dict) and "body" in event:
            raw_body = event["body"]
            body = (
                json.loads(raw_body)
                if isinstance(raw_body, str)
                else raw_body
            )
        else:
            body = event

        if not isinstance(body, dict):
            return response(400, {"error": "Request body must be a JSON object"})

        device_id = body.get("device_id")
        ap_id = body.get("ap_id")
        event_type = body.get("event_type")

        if not device_id or not ap_id or not event_type:
            return response(400, {
                "error": "device_id, ap_id and event_type are required"
            })

        event_type = event_type.upper()

        if event_type not in ("CONNECT", "DISCONNECT"):
            return response(400, {
                "error": "event_type must be CONNECT or DISCONNECT"
            })

        # Load current AP configuration.
        aps = load_ap_config()

        if ap_id not in aps:
            return response(400, {
                "error": f"Unknown ap_id: {ap_id}"
            })

        ap = aps[ap_id]
        capacity = ap["capacity"]
        building = ap["building"]
        ap_name = ap["ap_name"]

        # Read the latest AP state.
        result = table.get_item(
            Key={"ap_id": ap_id},
            ConsistentRead=True,
        )
        current = result.get("Item")

        if not current:
            return response(404, {"error": "AP state not found"})

        current_count = int(current.get("connected_count", 0))

        # Prevent the stored count from exceeding capacity on CONNECT.
        if event_type == "CONNECT" and current_count >= capacity:
            return response(409, {
                "error": f"{ap_id} has reached its capacity",
                "capacity": capacity,
                "connected_count": current_count,
            })

        if event_type == "CONNECT":
            new_count = current_count + 1
        else:
            new_count = max(current_count - 1, 0)

        utilization_pct = round(
            (new_count / capacity) * 100, 2
        )
        status = status_for_utilization(utilization_pct)

        # Get a recommendation using current counts for all APs.
        recommendation = None

        if status == CONGESTED:
            # Use the latest count for this AP in the recommendation.
            aps[ap_id]["connected_count"] = new_count
            recommendation = recommend_for(
                ap_id, aps, new_count
            )

        timestamp = (
            body.get("timestamp")
            or datetime.now(timezone.utc).isoformat()
        )

        # Update only live-state fields so custom AP configuration
        # is not removed by a device event.
        try:
            table.update_item(
                Key={"ap_id": ap_id},
                UpdateExpression=(
                    "SET connected_count = :count, "
                    "utilization_pct = :util, "
                    "#st = :status, #ts = :timestamp, "
                    "device_id = :device, "
                    "building = :building, "
                    "#cap = :capacity, "
                    "ap_name = :name, "
                    "recommendation = :recommendation"
                ),
                ConditionExpression=(
                    "connected_count = :old_count "
                    "AND #cap = :capacity"
                ),
                ExpressionAttributeNames={
                    "#st": "status",
                    "#ts": "timestamp",
                    "#cap": "capacity",
                },
                ExpressionAttributeValues=floats_to_decimal({
                    ":count": new_count,
                    ":util": utilization_pct,
                    ":status": status,
                    ":timestamp": timestamp,
                    ":device": device_id,
                    ":building": building,
                    ":capacity": capacity,
                    ":name": ap_name,
                    ":recommendation": recommendation,
                    ":old_count": current_count,
                }),
            )

        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "")

            if code == "ConditionalCheckFailedException":
                return response(409, {
                    "error": "AP state changed concurrently; retry the event"
                })

            raise

        record = {
            "ap_id": ap_id,
            "timestamp": timestamp,
            "device_id": device_id,
            "event_type": event_type,
            "building": building,
            "ap_name": ap_name,
            "connected_count": new_count,
            "capacity": capacity,
            "utilization_pct": utilization_pct,
            "status": status,
            "recommendation": recommendation,
        }

        return response(200, record)

    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        print(f"Invalid event: {exc}")
        return response(400, {"error": "Invalid event payload or AP configuration"})

    except Exception as exc:
        print(f"EventProcessor error: {exc}")
        return response(500, {"error": "Unable to process event"})
