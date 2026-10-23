import json
from decimal import Decimal
import boto3
from boto3.dynamodb.conditions import Key

MAX_POINTS = 200

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("CampusNetSim_APHistory")


def _decimal_to_number(obj):
    if isinstance(obj, list):
        return [_decimal_to_number(v) for v in obj]
    if isinstance(obj, dict):
        return {k: _decimal_to_number(v) for k, v in obj.items()}
    if isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    return obj


def lambda_handler(event, context):
    ap_id = (event.get("pathParameters") or {}).get("ap_id")
    if not ap_id:
        return _response(400, {"error": "Missing path parameter: ap_id"})

    result = table.query(
        KeyConditionExpression=Key("ap_id").eq(ap_id),
        ScanIndexForward=True,
        Limit=MAX_POINTS,
    )
    items = _decimal_to_number(result.get("Items", []))
    return _response(200, {"ap_id": ap_id, "history": items})


def _response(status_code, body_dict):
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
        "body": json.dumps(body_dict),
    }
