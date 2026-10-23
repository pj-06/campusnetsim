import json
import os
import datetime
import boto3

APSTATE_TABLE = os.environ.get("APSTATE_TABLE", "CampusNetSim_APState")
MIGRATIONS_TABLE = os.environ.get("MIGRATIONS_TABLE", "CampusNetSim_Migrations")
APHISTORY_TABLE = os.environ.get("APHISTORY_TABLE", "CampusNetSim_APHistory")
DEVICES_TABLE = os.environ.get("DEVICES_TABLE", "CampusNetSim_Devices")

dynamodb = boto3.resource("dynamodb")
apstate_table = dynamodb.Table(APSTATE_TABLE)
migrations_table = dynamodb.Table(MIGRATIONS_TABLE)
aphistory_table = dynamodb.Table(APHISTORY_TABLE)
devices_table = dynamodb.Table(DEVICES_TABLE)

CORS_HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "*",
    "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
}


def _response(status_code, body_dict):
    return {"statusCode": status_code, "headers": CORS_HEADERS, "body": json.dumps(body_dict)}


def _clear_table(table, key_names):
    deleted = 0
    names = {f"#k{i}": k for i, k in enumerate(key_names)}
    scan_kwargs = {"ProjectionExpression": ", ".join(names.keys()), "ExpressionAttributeNames": names}
    while True:
        resp = table.scan(**scan_kwargs)
        items = resp.get("Items", [])
        if items:
            with table.batch_writer() as batch:
                for item in items:
                    batch.delete_item(Key={k: item[k] for k in key_names})
            deleted += len(items)
        last_key = resp.get("LastEvaluatedKey")
        if not last_key:
            break
        scan_kwargs["ExclusiveStartKey"] = last_key
    return deleted


def _reset_ap_state():
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    reset_count = 0
    scan_kwargs = {}
    names = {"#status": "status", "#ts": "timestamp"}
    expr = "SET connected_count = :zero, utilization_pct = :zero, #status = :normal, #ts = :now REMOVE device_id, event_id, recommendation"
    while True:
        resp = apstate_table.scan(**scan_kwargs)
        for item in resp.get("Items", []):
            values = {":zero": 0, ":normal": "NORMAL", ":now": now}
            apstate_table.update_item(Key={"ap_id": item["ap_id"]}, UpdateExpression=expr, ExpressionAttributeNames=names, ExpressionAttributeValues=values)
            reset_count += 1
        last_key = resp.get("LastEvaluatedKey")
        if not last_key:
            break
        scan_kwargs["ExclusiveStartKey"] = last_key
    return reset_count


def _disconnect_all_devices():
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    disconnected_count = 0
    scan_kwargs = {}
    while True:
        resp = devices_table.scan(**scan_kwargs)
        for item in resp.get("Items", []):
            if item.get("status") != "CONNECTED":
                continue
            updated = dict(item)
            updated["status"] = "DISCONNECTED"
            updated["ap_id"] = None
            updated["last_seen"] = now
            devices_table.put_item(Item=updated)
            disconnected_count += 1
        last_key = resp.get("LastEvaluatedKey")
        if not last_key:
            break
        scan_kwargs["ExclusiveStartKey"] = last_key
    return disconnected_count


def lambda_handler(event, context):
    method = (event.get("requestContext", {}) or {}).get("http", {}).get("method") or event.get("httpMethod")
    if method == "OPTIONS":
        return _response(200, {})
    if method != "POST":
        return _response(405, {"error": "Use POST to trigger a reset"})
    aps_reset = _reset_ap_state()
    migrations_deleted = _clear_table(migrations_table, ["pk", "timestamp"])
    history_deleted = _clear_table(aphistory_table, ["ap_id", "timestamp"])
    devices_disconnected = _disconnect_all_devices()
    result = {"aps_reset": aps_reset, "migrations_deleted": migrations_deleted, "history_deleted": history_deleted, "devices_disconnected": devices_disconnected}
    return _response(200, result)
