"""
lambda_function.py
--------------------
AWS Lambda entry point for CampusNetSim's read/status API. Triggered by
API Gateway on GET /aps. Returns the current state of every AP in
CampusNetSim_APState as a JSON array -- this is what the dashboard
(Phase 5) polls to render live status, without ever touching DynamoDB
directly.

Kept as its own separate Lambda (rather than a branch inside
event_processor's lambda_handler) so read and write paths have
independent, minimally-scoped IAM permissions: this function only ever
needs dynamodb:Scan, never PutItem/GetItem for a single key.
"""

import json
from decimal import Decimal

import boto3

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("CampusNetSim_APState")


def _decimal_to_number(obj):
    """Reverse of event_processor's float->Decimal conversion: DynamoDB
    hands back Decimal for every number, but json.dumps can't serialize
    Decimal directly. Convert to int where the value is whole, float
    otherwise."""
    if isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    if isinstance(obj, dict):
        return {k: _decimal_to_number(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_decimal_to_number(v) for v in obj]
    return obj


def lambda_handler(event, context):
    items = table.scan().get("Items", [])
    items = _decimal_to_number(items)
    items.sort(key=lambda ap: ap.get("ap_id", ""))

    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            # Dashboard runs in a browser and calls this directly (unlike
            # POST /events, which the simulator calls server-to-server) --
            # needs CORS or every browser fetch() to this endpoint fails.
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps({"aps": items}),
    }
