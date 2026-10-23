import json
import random
import uuid
import urllib.request
import urllib.error
from datetime import datetime, timezone
from decimal import Decimal

import boto3

BASE_URL = "https://0iczavlx88.execute-api.ap-south-1.amazonaws.com"
HIGH_THRESHOLD_PCT = 85       # start rebalancing once an AP crosses this
MAX_DEVICES_PER_MIGRATION = 5

dynamodb = boto3.resource("dynamodb")
migrations_table = dynamodb.Table("CampusNetSim_Migrations")


def _get_aps():
    req = urllib.request.Request(f"{BASE_URL}/aps", method="GET")
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))["aps"]


def _post_event(device_id, ap_id, event_type):
    body = json.dumps({"device_id": device_id, "ap_id": ap_id, "event_type": event_type}).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE_URL}/events", data=body,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.read().decode('utf-8', 'ignore')}"}


def _get_devices():
    req = urllib.request.Request(f"{BASE_URL}/devices", method="GET")
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))["devices"]

def _post_device_join(device_id, ap_id, nickname):
    body = json.dumps({"device_id": device_id, "event_type": "JOIN", "ap_id": ap_id, "nickname": nickname}).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE_URL}/devices", data=body,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.read().decode('utf-8', 'ignore')}"}

def _record_migration(source, target, moved, s_before, s_after, t_before, t_after, reason):
    migrations_table.put_item(Item={
        "pk": "MIGRATION",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "migration_id": str(uuid.uuid4()),
        "source_ap_id": source,
        "target_ap_id": target,
        "devices_moved": moved,
        "source_utilization_before": Decimal(str(s_before)),
        "source_utilization_after": Decimal(str(s_after)),
        "target_utilization_before": Decimal(str(t_before)),
        "target_utilization_after": Decimal(str(t_after)),
        "status": "success",
        "reason": reason,
    })


def lambda_handler(event, context):
    for record in event.get("Records", []):
        if record.get("eventName") not in ("INSERT", "MODIFY"):
            continue

        new_image = record.get("dynamodb", {}).get("NewImage", {})
        ap_id = new_image.get("ap_id", {}).get("S")
        utilization_raw = new_image.get("utilization_pct", {}).get("N")
        device_id = new_image.get("device_id", {}).get("S", "") or ""

        if not ap_id or utilization_raw is None:
            continue

        # Don't react to events a migration itself just wrote -- avoids
        # feedback loops re-triggering this same Lambda via the stream.
        if device_id.startswith("migrated-"):
            continue

        if float(utilization_raw) < HIGH_THRESHOLD_PCT:
            continue

        try:
            aps = _get_aps()
        except Exception:
            continue

        source = next((a for a in aps if a["ap_id"] == ap_id), None)
        if not source or source["utilization_pct"] < HIGH_THRESHOLD_PCT:
            continue

        candidates = [a for a in aps if a["ap_id"] != ap_id]
        if not candidates:
            continue
        target = max(candidates, key=lambda a: a["capacity"] - a["connected_count"])
        target_spare = target["capacity"] - target["connected_count"]
        if target_spare <= 0:
            continue

        source_target_count = int(source["capacity"] * (HIGH_THRESHOLD_PCT - 5) / 100)
        need_to_move = max(1, source["connected_count"] - source_target_count)
        n = min(need_to_move, target_spare, MAX_DEVICES_PER_MIGRATION)
        if n <= 0:
            continue

        source_before = source["utilization_pct"]
        target_before = target["utilization_pct"]
        last_source_state, last_target_state = source, target
        moved = 0

        try:
            all_devices = _get_devices()
        except Exception:
            all_devices = []
        real_candidates = [
            d for d in all_devices
            if d.get("ap_id") == ap_id and d.get("status") == "CONNECTED"
        ]
        for i in range(n):
            real_dev = real_candidates[i] if i < len(real_candidates) else None
            if real_dev:
                dev_id = real_dev["device_id"]
            else:
                dev_id = f"migrated-{ap_id}-{random.randint(1000, 9999)}"
            disc = _post_event(dev_id, ap_id, "DISCONNECT")
            if "error" in disc:
                continue
            conn = _post_event(dev_id, target["ap_id"], "CONNECT")
            if "error" in conn:
                continue
            if real_dev:
                _post_device_join(dev_id, target["ap_id"], real_dev.get("nickname", "Guest"))
            moved += 1
            last_source_state, last_target_state = disc, conn
        if moved == 0:
            continue

        _record_migration(
            source=ap_id,
            target=target["ap_id"],
            moved=moved,
            s_before=source_before,
            s_after=last_source_state.get("utilization_pct", source_before),
            t_before=target_before,
            t_after=last_target_state.get("utilization_pct", target_before),
            reason=f"{ap_id} at {source_before}% (>= {HIGH_THRESHOLD_PCT}% threshold)",
        )

    return {"statusCode": 200}
