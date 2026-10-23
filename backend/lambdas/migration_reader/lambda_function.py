import json
from decimal import Decimal
import boto3
from boto3.dynamodb.conditions import Key

MAX_ITEMS = 50

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("CampusNetSim_Migrations")


def _decimal_to_number(obj):
    if isinstance(obj, list):
        return [_decimal_to_number(v) for v in obj]
    if isinstance(obj, dict):
        return {k: _decimal_to_number(v) for k, v in obj.items()}
    if isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    return obj


def lambda_handler(event, context):
    result = table.query(
        KeyConditionExpression=Key("pk").eq("MIGRATION"),
        ScanIndexForward=False,
        Limit=MAX_ITEMS,
    )
    items = _decimal_to_number(result.get("Items", []))
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
        "body": json.dumps({"migrations": items}),
    }
