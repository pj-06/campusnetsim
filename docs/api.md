# CampusNetSim API

HTTP API (Amazon API Gateway) in front of the CampusNetSim Lambda functions,
region `ap-south-1`.

**Base URL:** `https://0iczavlx88.execute-api.ap-south-1.amazonaws.com`

All responses are JSON and carry `Access-Control-Allow-Origin: *`, so the
dashboard and the phone check-in page call the API directly from the browser.
There is no authentication yet (see "Known limitations").

AP status values: `NORMAL` (< 70 %), `BUSY` (70 to < 90 %), `HIGH_LOAD`
(90 to < 100 %), `CONGESTED` (>= 100 %).

---

## GET /aps  (CampusNetSim-StatusReader)

Returns the live state of every AP, sorted by `ap_id`.

```json
{
  "aps": [
    {
      "ap_id": "AP01",
      "ap_name": "AP01",
      "building": "academic_block",
      "capacity": 3,
      "connected_count": 0,
      "utilization_pct": 0,
      "status": "NORMAL",
      "timestamp": "2026-10-20T17:04:54.384722+00:00"
    }
  ]
}
```

## POST /events  (CampusNetSim-EventProcessor)

Records one device CONNECT or DISCONNECT at an AP and returns the updated AP
record. Capacity, building and name are read from `CampusNetSim_APState` on
every call, so a capacity change through `PUT /aps/{ap_id}/config` takes effect
immediately.

Request body:

| field | type | required | notes |
|---|---|---|---|
| `device_id` | string | yes | any device identifier |
| `ap_id` | string | yes | must exist in `CampusNetSim_APState` |
| `event_type` | string | yes | `CONNECT` or `DISCONNECT` (case-insensitive) |
| `timestamp` | string | no | ISO 8601; server time is used if omitted |

Responses:

- `200` updated record (`connected_count`, `capacity`, `utilization_pct`,
  `status`, and `recommendation` when the AP is CONGESTED)
- `400` missing or invalid fields, or unknown `ap_id`
- `409` the AP is already at capacity (CONNECT rejected), or the AP state
  changed concurrently (conditional write failed; retry the event)

## PUT /aps/{ap_id}/config  (UpdateAPConfig)

Updates an AP's configuration without touching its live counters.

```json
{ "capacity": 4 }
```

Allowed fields: `capacity` (integer 1 to 1000), `building`, `ap_name`.

- `200` `{ "message": "AP configuration updated", "ap_id": "...", "updated": {...} }`
  (utilization is recalculated when capacity changes)
- `400` invalid or unsupported field
- `404` AP not found
- `409` capacity lower than the number of connected devices

## GET /aps/{ap_id}/history  (CampusNetSim-HistoryReader)

Up to 200 readings for one AP, oldest first. Readings expire after 24 hours
(DynamoDB TTL on `expires_at`).

```json
{ "ap_id": "AP03", "history": [ { "timestamp": "...", "utilization_pct": 33.33, "...": "..." } ] }
```

## GET /migrations  (CampusNetSim-MigrationReader)

The 50 most recent load-balancing actions, newest first.

```json
{
  "migrations": [
    {
      "source_ap_id": "AP04",
      "target_ap_id": "AP03",
      "devices_moved": 1,
      "source_utilization_before": 100,
      "source_utilization_after": 0,
      "target_utilization_before": 0,
      "target_utilization_after": 33.33,
      "reason": "AP04 at 100% (>= 85% threshold)",
      "status": "success",
      "timestamp": "2026-10-20T17:14:38.947803+00:00"
    }
  ]
}
```

## GET /devices and POST /devices  (CampusNetSim-DeviceRegistry)

`GET` returns the check-in roster:

```json
{ "devices": [ { "device_id": "...", "nickname": "...", "ap_id": "AP02", "status": "CONNECTED", "joined_at": "...", "last_seen": "..." } ] }
```

`POST` body: `{ "device_id": "...", "event_type": "JOIN", "ap_id": "AP02", "nickname": "..." }`
or `{ "device_id": "...", "event_type": "LEAVE" }`.

## POST /admin/reset  (CampusNetSim-AdminReset)

Zeroes every AP, deletes all rows in `CampusNetSim_Migrations` and
`CampusNetSim_APHistory`, and marks every connected device as disconnected.
**Irreversible.** Any other method returns `405`.

```json
{ "aps_reset": 4, "migrations_deleted": 1, "history_deleted": 12, "devices_disconnected": 0 }
```

---

## Stream-driven functions (no route)

- **CampusNetSim-LoadBalancer**: consumes the `CampusNetSim_APState` stream.
  When an AP reaches 85 % or more, it picks the AP with the most free capacity
  and moves up to 5 devices (enough to bring the source down to about 80 %) by
  posting DISCONNECT/CONNECT events, updates the roster for real phones, and
  writes a record to `CampusNetSim_Migrations`.
- **CampusNetSim-HistoryWriter**: consumes the same stream and appends each
  new AP state to `CampusNetSim_APHistory`.

## Known limitations

- No authentication or authorization on any route, including
  `/admin/reset` and `/aps/{ap_id}/config`.
- `CampusNetSim-TrafficGenerator` has no trigger; invoke it manually or attach
  an EventBridge schedule.
