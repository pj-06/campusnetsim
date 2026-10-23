"""
lambda_function.py -- CampusNetSim-DeviceRegistry
--------------------------------------------------
Handles POST/GET /devices for the phone check-in feature.

This is a NEW Lambda (not a modification of EventProcessor). It tracks
"who is this real phone, what nickname did they pick, and which
simulated AP are they currently associated with" -- separate from
EventProcessor's job of updating AP congestion counters.

The QR check-in page calls BOTH APIs on join/leave:
  1. POST /events  (existing EventProcessor) -> updates the AP's
     connected_count / utilization / congestion status.
  2. POST /devices (this Lambda)             -> upserts this device's
     roster entry (nickname + current ap_id) so the dashboard can show
     a human-readable "who's where" panel and the chat feature can look
     up a sender's nickname/AP.

IMPORTANT: joining an AP here is a SIMULATED association only. It does
NOT connect the phone to any real Wi-Fi network -- the phone stays on
whatever network it already has (Wi-Fi/mobile data) and talks to this
API over the internet the whole time. See docs/qr-checkin.md.

DynamoDB table: CampusNetSim_Devices (override via TABLE_NAME env var)
  Partition key : device_id (String)
  No sort key -- one item per device, holding its current state only,
  same "one row per entity" shape as CampusNetSim_APState.

One Lambda handles both POST and GET (unlike the AP-state read/write
split) to keep the resource count low for a student project -- see
docs/decisions.md for the tradeoff (this function needs both
dynamodb:PutItem/GetItem and dynamodb:Scan on its own table).
"""

import json
import os
from datetime import datetime, timezone

import boto3

TABLE_NAME = os.environ.get("TABLE_NAME", "CampusNetSim_Devices")
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(TABLE_NAME)

MAX_NICKNAME_LEN = 30


def _response(status_code, body_dict):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            # Browser JS on the check-in page and the dashboard both call
            # this directly -- needs CORS the same way GET /aps does.
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
        },
        "body": json.dumps(body_dict),
    }


def lambda_handler(event, context):
    # HTTP API (payload format 2.0) puts the method at
    # requestContext.http.method; REST API / a hand-typed console test
    # event may use the older top-level httpMethod instead. Support both.
    method = (
        (event.get("requestContext", {}) or {}).get("http", {}).get("method")
        or event.get("httpMethod")
        or "GET"
    ).upper()

    if method == "OPTIONS":
        # Preflight request from the browser -- just needs the CORS
        # headers above, no body.
        return _response(200, {})
    if method == "GET":
        return _handle_get()
    if method == "POST":
        return _handle_post(event)
    return _response(405, {"error": f"Unsupported method: {method}"})


def _handle_get():
    items = table.scan().get("Items", [])
    items.sort(key=lambda d: d.get("joined_at", ""))
    return _response(200, {"devices": items})


def _handle_post(event):
    if isinstance(event, dict) and "body" in event:
        body = json.loads(event["body"]) if isinstance(event["body"], str) else event["body"]
    else:
        body = event

    try:
        device_id = body["device_id"]
        event_type = body["event_type"]  # "JOIN" or "LEAVE"
    except KeyError as e:
        return _response(400, {"error": f"Missing field: {e}"})

    if event_type not in ("JOIN", "LEAVE"):
        return _response(400, {"error": f"Unknown event_type: {event_type}"})

    now = datetime.now(timezone.utc).isoformat()

    if event_type == "JOIN":
        ap_id = body.get("ap_id")
        if not ap_id:
            return _response(400, {"error": "ap_id required for JOIN"})
        nickname = str(body.get("nickname") or "Guest")[:MAX_NICKNAME_LEN]

        existing = table.get_item(Key={"device_id": device_id}).get("Item")
        joined_at = existing["joined_at"] if existing and existing.get("joined_at") else now

        record = {
            "device_id": device_id,
            "nickname": nickname,
            "ap_id": ap_id,
            "status": "CONNECTED",
            "joined_at": joined_at,
            "last_seen": now,
        }
    else:  # LEAVE
        existing = table.get_item(Key={"device_id": device_id}).get("Item")
        if not existing:
            return _response(404, {"error": "device not found"})
        record = dict(existing)
        record["status"] = "DISCONNECTED"
        record["ap_id"] = None
        record["last_seen"] = now

    table.put_item(Item=record)
    return _response(200, record)
