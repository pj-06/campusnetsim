"""
lambda_function.py -- CampusNetSim-Chat
-----------------------------------------
Handles POST/GET /chat: the real-time-feeling chat feature between
phones that are (simulated-)associated with different APs.

This chat is REAL -- messages genuinely travel phone -> API Gateway ->
this Lambda -> DynamoDB -> back out to every other phone's next poll.
What's simulated is only which AP a device is "connected to" (tracked
by CampusNetSim-DeviceRegistry / CampusNetSim-EventProcessor) -- the
phones themselves talk to this API over their real internet connection
(Wi-Fi or mobile data) the whole time, same as any normal web app.
Nothing here claims or requires the phones to be on the same physical
network.

Transport: plain HTTP polling (the check-in page calls GET /chat every
2-3s), not WebSockets. Simpler and more reliable for a short classroom
demo than standing up API Gateway WebSocket connection management, and
avoids extra IAM surface -- see docs/decisions.md.

DynamoDB table: CampusNetSim_Messages (override via TABLE_NAME env var)
  Partition key : room       (String) -- always "campus": one shared,
                              campus-wide room is enough for a demo
                              with a handful of devices; no per-AP
                              room switching to keep the UI simple.
  Sort key      : sent_at    (String) -- zero-padded 13-digit epoch
                              milliseconds + "#" + a short random
                              suffix, e.g. "1758369957123#a1b2c3".
                              Zero-padding makes plain string
                              comparison ("sent_at > :floor") sort and
                              range-filter correctly by time, and the
                              random suffix avoids collisions when two
                              messages land in the same millisecond.
"""

import json
import os
import time
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import boto3

TABLE_NAME = os.environ.get("TABLE_NAME", "CampusNetSim_Messages")
ROOM = "campus"
MAX_MESSAGE_LEN = 500
POLL_LIMIT = 50  # when polling with no "since", how much recent history to return

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(TABLE_NAME)


def _response(status_code, body_dict):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
        },
        "body": json.dumps(body_dict),
    }


def _decimal_to_number(obj):
    """Same conversion status_reader uses: DynamoDB hands back Decimal
    for every number, json.dumps can't serialize Decimal directly."""
    if isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    if isinstance(obj, dict):
        return {k: _decimal_to_number(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_decimal_to_number(v) for v in obj]
    return obj


def lambda_handler(event, context):
    method = (
        (event.get("requestContext", {}) or {}).get("http", {}).get("method")
        or event.get("httpMethod")
        or "GET"
    ).upper()

    if method == "OPTIONS":
        return _response(200, {})
    if method == "GET":
        return _handle_get(event)
    if method == "POST":
        return _handle_post(event)
    return _response(405, {"error": f"Unsupported method: {method}"})


def _handle_get(event):
    # ?since=<epoch_millis> -> only messages strictly newer than that
    # (used for the 2-3s poll loop after the first load). No "since" ->
    # most recent POLL_LIMIT messages (used for the initial page load).
    params = event.get("queryStringParameters") or {}
    since = params.get("since")

    if since:
        sk_floor = f"{int(since):013d}"
        resp = table.query(
            KeyConditionExpression="#r = :room AND sent_at > :floor",
            ExpressionAttributeNames={"#r": "room"},
            ExpressionAttributeValues={":room": ROOM, ":floor": sk_floor},
        )
        items = resp.get("Items", [])
    else:
        resp = table.query(
            KeyConditionExpression="#r = :room",
            ExpressionAttributeNames={"#r": "room"},
            ExpressionAttributeValues={":room": ROOM},
            ScanIndexForward=False,  # newest first from DynamoDB...
            Limit=POLL_LIMIT,
        )
        items = resp.get("Items", [])

    items = _decimal_to_number(items)
    items.sort(key=lambda m: m.get("sent_at", ""))  # ...then re-sort oldest-first for display

    return _response(200, {
        "messages": items,
        "server_time": int(time.time() * 1000),
    })


def _handle_post(event):
    if isinstance(event, dict) and "body" in event:
        body = json.loads(event["body"]) if isinstance(event["body"], str) else event["body"]
    else:
        body = event

    try:
        device_id = body["device_id"]
        message = body["message"]
    except KeyError as e:
        return _response(400, {"error": f"Missing field: {e}"})

    message = str(message).strip()[:MAX_MESSAGE_LEN]
    if not message:
        return _response(400, {"error": "message cannot be empty"})

    nickname = str(body.get("nickname") or "Guest")[:30]
    ap_id = body.get("ap_id")  # which simulated AP the sender was on -- for display only

    now_ms = int(time.time() * 1000)
    sent_at = f"{now_ms:013d}#{uuid.uuid4().hex[:6]}"

    record = {
        "room": ROOM,
        "sent_at": sent_at,
        "device_id": device_id,
        "nickname": nickname,
        "ap_id": ap_id,
        "message": message,
        "timestamp_iso": datetime.now(timezone.utc).isoformat(),
    }

    table.put_item(Item=record)
    return _response(200, record)
