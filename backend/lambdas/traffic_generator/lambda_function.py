import json
import random
import urllib.request
import urllib.error

BASE_URL = "https://0iczavlx88.execute-api.ap-south-1.amazonaws.com"
SPIKE_CHANCE = 0.12       # ~12% chance per AP per run to deliberately congest it
MAX_EVENTS_PER_AP = 4     # cap events sent per AP per invocation


def _get(path):
    req = urllib.request.Request(f"{BASE_URL}{path}", method="GET")
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _post_event(device_id, ap_id, event_type):
    body = json.dumps({
        "device_id": device_id,
        "ap_id": ap_id,
        "event_type": event_type,
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE_URL}/events",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.read().decode('utf-8', 'ignore')}"}


def lambda_handler(event, context):
    state = _get("/aps")
    aps = state.get("aps", [])
    results = []

    for ap in aps:
        ap_id = ap["ap_id"]
        capacity = ap["capacity"]
        current = ap["connected_count"]

        if random.random() < SPIKE_CHANCE:
            # Deliberate congestion spike so the recommendations panel has something to show
            target = int(capacity * random.uniform(1.0, 1.35))
        else:
            # Gentle wobble around a moderate baseline
            baseline = capacity * random.uniform(0.2, 0.85)
            wobble = capacity * random.uniform(-0.1, 0.1)
            target = max(0, int(baseline + wobble))

        delta = target - current
        n_events = min(abs(delta), MAX_EVENTS_PER_AP)
        event_type = "CONNECT" if delta > 0 else "DISCONNECT"

        sent = 0
        for _ in range(n_events):
            device_id = f"sim-{ap_id}-{random.randint(1000, 9999)}"
            outcome = _post_event(device_id, ap_id, event_type)
            if "error" not in outcome:
                sent += 1

        results.append({"ap_id": ap_id, "event_type": event_type, "sent": sent, "target": target})

    return {
        "statusCode": 200,
        "body": json.dumps({"ok": True, "results": results}),
    }
