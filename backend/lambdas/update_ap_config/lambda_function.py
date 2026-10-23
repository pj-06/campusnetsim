
import json
import os
import boto3
from decimal import Decimal

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(
    os.environ.get("TABLE_NAME", "CampusNetSim_APState")
)

def response(code, data):
    return {
        "statusCode": code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
        },
        "body": json.dumps(data, default=str)
    }

def lambda_handler(event, context):
    try:
        path = event.get("pathParameters") or {}
        ap_id = path.get("ap_id")

        raw_body = event.get("body") or "{}"
        body = (
            json.loads(raw_body)
            if isinstance(raw_body, str)
            else raw_body
        )

        if not ap_id:
            return response(400, {"error": "Missing AP ID"})

        allowed = {"capacity", "building", "ap_name"}
        if not isinstance(body, dict) or not body:
            return response(400, {"error": "Provide configuration fields"})

        if set(body) - allowed:
            return response(400, {"error": "Unsupported configuration field"})

        result = table.get_item(
            Key={"ap_id": ap_id},
            ConsistentRead=True
        )
        item = result.get("Item")

        if not item:
            return response(404, {"error": "AP not found"})

        updates = {}

        if "capacity" in body:
            cap = body["capacity"]
            if (
                isinstance(cap, bool)
                or not isinstance(cap, int)
                or cap < 1
                or cap > 1000
            ):
                return response(400, {
                    "error": "Capacity must be an integer from 1 to 1000"
                })

            connected = int(item.get("connected_count", 0))
            if cap < connected:
                return response(409, {
                    "error": "Capacity cannot be below connected device count"
                })

            updates["capacity"] = cap

        if "building" in body:
            building = body["building"]
            if not isinstance(building, str) or not building.strip():
                return response(400, {"error": "Invalid building"})
            updates["building"] = building.strip().lower().replace(" ", "_")

        if "ap_name" in body:
            name = body["ap_name"]
            if not isinstance(name, str) or not name.strip():
                return response(400, {"error": "Invalid AP name"})
            updates["ap_name"] = name.strip()

        if not updates:
            return response(400, {"error": "No changes supplied"})

        # Recalculate utilisation if capacity changes.
        if "capacity" in updates:
            connected = int(item.get("connected_count", 0))
            updates["utilization_pct"] = Decimal(str(
                round(connected / updates["capacity"] * 100, 2)
            ))

        # Preserve other AP attributes instead of replacing the whole item.
        names = {}
        values = {}
        assignments = []

        for i, (key, value) in enumerate(updates.items()):
            names[f"#k{i}"] = key
            values[f":v{i}"] = value
            assignments.append(f"#k{i} = :v{i}")

        table.update_item(
            Key={"ap_id": ap_id},
            UpdateExpression="SET " + ", ".join(assignments),
            ExpressionAttributeNames=names,
            ExpressionAttributeValues=values
        )

        return response(200, {
            "message": "AP configuration updated",
            "ap_id": ap_id,
            "updated": updates
        })

    except Exception as exc:
        print(f"UpdateAPConfig error: {exc}")
        return response(500, {"error": "Unable to update AP configuration"})
