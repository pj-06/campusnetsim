"""
lambda_function.py
--------------------
AWS Lambda entry point for CampusNetSim. Triggered by API Gateway on
POST /events. Mirrors the exact logic already built and tested locally
in simulator/network_state.py and simulator/analytics.py -- the same
thresholds, the same recommendation heuristic -- just reading and
writing DynamoDB instead of an in-memory dict, since Lambda has no
memory of its own between invocations.

Design notes (worth keeping for the report):
- We use a straightforward read -> compute -> write pattern rather
  than an atomic DynamoDB counter update, matching the project's
  stated preference for a simple, explainable first implementation.
  A production system at real scale would use a conditional/atomic
  UpdateItem to avoid a race between two near-simultaneous events on
  the same AP; that's a natural documented limitation / future work.
- recommend_ap() uses a full table Scan, which is fine at 8 AP items.
  A Global Secondary Index on `building` would be the natural next
  step if the campus model grew much larger -- worth mentioning as a
  scalability discussion point in Review 3.
"""

import json
import os
from datetime import datetime, timezone
from decimal import Decimal

import boto3

dynamodb = boto3.resource("dynamodb")
TABLE_NAME = os.environ.get("TABLE_NAME", "CampusNetSim_APState")
table = dynamodb.Table(TABLE_NAME)


def _floats_to_decimal(obj):
    """DynamoDB's boto3 Table API rejects Python float outright ('Float
    types are not supported. Use Decimal types instead.'). Recursively
    convert any float in a dict/list to Decimal (via str() to avoid
    binary float imprecision) right before writing -- the JSON response
    keeps plain floats, since json.dumps can't serialize Decimal either."""
    if isinstance(obj, float):
        return Decimal(str(obj))
    if isinstance(obj, dict):
        return {k: _floats_to_decimal(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_floats_to_decimal(v) for v in obj]
    return obj

THRESHOLD_BUSY = 70.0
THRESHOLD_HIGH_LOAD = 90.0
THRESHOLD_CONGESTED = 100.0

REQUIRED_FIELDS = ["event_id", "timestamp", "device_id", "ap_id", "building", "event_type"]


def get_status(utilization):
    if utilization >= THRESHOLD_CONGESTED:
        return "CONGESTED"
    if utilization >= THRESHOLD_HIGH_LOAD:
        return "HIGH_LOAD"
    if utilization >= THRESHOLD_BUSY:
        return "BUSY"
    return "NORMAL"


def available_capacity(ap_item):
    return max(int(ap_item["capacity"]) - int(ap_item["current_users"]), 0)


def recommend_ap(congested_ap):
    """Same heuristic as simulator/analytics.py::recommend_ap -- prefer
    a same-building AP with spare capacity, widen to the whole campus
    if none has room, pick whichever candidate has the most available
    capacity."""
    all_aps = table.scan().get("Items", [])

    same_building = [
        ap for ap in all_aps
        if ap["building"] == congested_ap["building"]
        and ap["ap_id"] != congested_ap["ap_id"]
        and available_capacity(ap) > 0
    ]
    candidates = same_building or [
        ap for ap in all_aps
        if ap["ap_id"] != congested_ap["ap_id"] and available_capacity(ap) > 0
    ]

    if not candidates:
        return None

    best = max(candidates, key=available_capacity)
    projected = round(((int(best["current_users"]) + 1) / int(best["capacity"])) * 100, 2)

    return {
        "recommended_ap_id": best["ap_id"],
        "building": best["building"],
        "available_capacity": available_capacity(best),
        "projected_utilization": projected,
    }


def lambda_handler(event, context):
    try:
        body = json.loads(event.get("body") or "{}")
    except (TypeError, json.JSONDecodeError):
        return _response(400, {"error": "Invalid JSON body"})

    missing = [f for f in REQUIRED_FIELDS if f not in body]
    if missing:
        return _response(400, {"error": f"Missing fields: {missing}"})

    ap_id = body["ap_id"]
    event_type = body["event_type"]

    if event_type not in ("CONNECT", "DISCONNECT"):
        return _response(400, {"error": f"Unknown event_type: {event_type}"})

    ap_item = table.get_item(Key={"ap_id": ap_id}).get("Item")
    if ap_item is None:
        return _response(404, {"error": f"Unknown ap_id: {ap_id}"})

    current_users = int(ap_item["current_users"])
    capacity = int(ap_item["capacity"])

    if event_type == "CONNECT":
        current_users += 1
    else:
        current_users = max(current_users - 1, 0)

    utilization = round((current_users / capacity) * 100, 2) if capacity else 0
    status = get_status(utilization)

    updated_item = {
        "ap_id": ap_id,
        "building": body["building"],
        "capacity": capacity,
        "current_users": current_users,
        "utilization": utilization,
        "status": status,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    table.put_item(Item=_floats_to_decimal(updated_item))

    recommendation = recommend_ap(updated_item) if status == "CONGESTED" else None

    return _response(200, {
        "ap_id": ap_id,
        "building": updated_item["building"],
        "current_users": current_users,
        "capacity": capacity,
        "utilization": utilization,
        "status": status,
        "recommendation": recommendation,
    })


def _response(status_code, body_dict):
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body_dict),
    }
