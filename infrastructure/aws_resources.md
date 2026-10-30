# Deployed AWS resources (ap-south-1)

These are the resources that make up CampusNetSim in AWS. The settings were
read from the AWS console on 23 October 2026. `template.yaml` in this folder
recreates the same stack with AWS SAM.

## Lambda functions

All functions use the `lambda_function.lambda_handler` handler, x86_64, 128 MB
memory and 512 MB ephemeral storage. Source code: `backend/lambdas/<folder>/`.

| Function | Folder | Runtime | Timeout | Trigger |
|---|---|---|---|---|
| CampusNetSim-EventProcessor | `event_processor` | python3.13 | 3 s | HTTP API `ANY /events` (env `TABLE_NAME=CampusNetSim_APState`) |
| CampusNetSim-DeviceRegistry | `device_registry` | python3.13 | 3 s | HTTP API `ANY /devices` |
| CampusNetSim-StatusReader | `status_reader` | python3.13 | 3 s | HTTP API `ANY /aps` |
| UpdateAPConfig | `update_ap_config` | python3.14 | 3 s | HTTP API `ANY /aps/{ap_id}/config` |
| CampusNetSim-HistoryReader | `history_reader` | python3.13 | 3 s | HTTP API `ANY /aps/{ap_id}/history` |
| CampusNetSim-MigrationReader | `migration_reader` | python3.13 | 3 s | HTTP API `ANY /migrations` |
| CampusNetSim-AdminReset | `admin_reset` | python3.13 | 40 s | HTTP API `ANY /admin/reset` |
| CampusNetSim-LoadBalancer | `load_balancer` | python3.13 | 30 s | DynamoDB Stream on `CampusNetSim_APState` (batch 100, LATEST) |
| CampusNetSim-HistoryWriter | `history_writer` | python3.13 | 3 s | DynamoDB Stream on `CampusNetSim_APState` (batch 100, LATEST) |
| CampusNetSim-TrafficGenerator | `traffic_generator` | python3.13 | 30 s | none (manual invocation) |

## API Gateway

- HTTP API `CampusNetSim-API`, base URL
  `https://0iczavlx88.execute-api.ap-south-1.amazonaws.com`
- CORS enabled for browser access from the dashboard and the check-in page

## DynamoDB (on-demand capacity)

| Table | Partition key | Sort key | Notes |
|---|---|---|---|
| CampusNetSim_APState | `ap_id` (S) | none | Stream ON, view type NEW_IMAGE; consumers LoadBalancer + HistoryWriter |
| CampusNetSim_APHistory | `ap_id` (S) | `timestamp` (S) | TTL on `expires_at` (24 h retention) |
| CampusNetSim_Devices | `device_id` (S) | none | Phone check-in roster |
| CampusNetSim_Migrations | `pk` (S) | `timestamp` (S) | `pk` is always `MIGRATION` |
| CampusNetSim_Messages | `room` (S) | `sent_at` (S) | Legacy chat table, unused |

## Static hosting

- Phone check-in page: S3 bucket `campusnetsim-checkin-<account-id>`, object
  `index.html` (source: `checkin/index.html`). Each AP's QR code opens
  `index.html?ap=AP0n`.
- Dashboard: AWS Amplify Hosting, manual deployment of the Vite `dist/` build
  (see `dashboard/make_zip.py`).
