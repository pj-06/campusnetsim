# CampusNetSim API

Live backend for Phase 2 -- deployed on AWS (Lambda + DynamoDB + API Gateway,
region `ap-south-1`). This is what the dashboard (Phase 5) talks to; you
should not need to touch DynamoDB or Lambda directly.

**Base URL:** `https://0iczavlx88.execute-api.ap-south-1.amazonaws.com`

No authentication. `GET /aps` has CORS enabled (`Access-Control-Allow-Origin: *`)
so it's safe to call directly from browser JS. `POST /events` does not have
CORS configured -- it's meant to be called by the simulator/backend, not
from browser code.

---

## GET /aps

Returns the current live state of all 8 APs, sorted by `ap_id`. **This is
the endpoint the dashboard should poll** (e.g. every few seconds) to render
the live status grid.

Request: no body, no params.

```
curl https://0iczavlx88.execute-api.ap-south-1.amazonaws.com/aps
```

Response `200`:

```json
{
  "aps": [
    {
      "ap_id": "AP01",
      "building": "academic_block",
      "capacity": 50,
      "connected_count": 0,
      "utilization_pct": 0,
      "status": "NORMAL",
      "timestamp": "2026-08-31T19:45:32.434279+00:00",
      "event_id": null,
      "device_id": null,
      "recommendation": null
    }
  ]
}
```

(all 8 AP items come back in one array, same shape as above)

---

## POST /events

Records a single device CONNECT/DISCONNECT event at an AP. Updates that
AP's live state in DynamoDB and returns the full updated record. This is
what the traffic simulator calls for every event it generates; the
dashboard does not need to call this directly.

Request body (JSON):

| field        | type   | required | notes                                              |
|--------------|--------|----------|-----------------------------------------------------|
| `device_id`  | string | yes      | any identifier for the device                       |
| `ap_id`      | string | yes      | one of `AP01`..`AP08` (see campus layout below)      |
| `event_type` | string | yes      | `"CONNECT"` or `"DISCONNECT"`                        |
| `timestamp`  | string | no       | ISO 8601; server fills in current UTC time if omitted |
| `event_id`   | string | no       | any identifier for the event                         |

```
curl -X POST https://0iczavlx88.execute-api.ap-south-1.amazonaws.com/events \
  -H "Content-Type: application/json" \
  -d '{"device_id": "device-42", "ap_id": "AP03", "event_type": "CONNECT"}'
```

Response `200`:

```json
{
  "ap_id": "AP03",
  "timestamp": "2026-08-31T19:50:42.132284+00:00",
  "event_id": null,
  "device_id": "device-42",
  "building": "academic_block",
  "connected_count": 12,
  "capacity": 75,
  "utilization_pct": 16.0,
  "status": "NORMAL",
  "recommendation": null
}
```

`status` is one of `NORMAL` (<70%), `BUSY` (<90%), `HIGH_LOAD` (<100%),
`CONGESTED` (>=100%). `recommendation` is populated only when `status` is
`CONGESTED`, and looks like:

```json
{
  "recommended_ap_id": "AP04",
  "building": "hostel",
  "available_capacity": 23,
  "projected_utilization_pct": 78.0
}
```

Error responses (all `400`):

```json
{"error": "Missing field: 'device_id'"}
{"error": "Unknown ap_id: AP99"}
{"error": "Unknown event_type: PING"}
```

---

## Campus layout (for reference)

| Building         | APs                         |
|-------------------|------------------------------|
| `academic_block`  | AP01 (50), AP02 (50), AP03 (75) |
| `hostel`           | AP04 (100), AP05 (100), AP06 (75) |
| `library`          | AP07 (75), AP08 (50)          |

(numbers in parens are each AP's device capacity)

---

## Resetting demo data

To reset all 8 APs back to zero traffic (e.g. before a demo run), from the
repo root with AWS credentials configured:

```
python -m infrastructure.seed_dynamodb
```
