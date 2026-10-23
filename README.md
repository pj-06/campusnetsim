# CampusNetSim

Cloud-native campus Wi-Fi congestion simulation and automated load balancing
on AWS.

CampusNetSim models four access points (APs) across three campus buildings.
Phones join the simulation by scanning an AP's QR code, and a serverless
backend tracks each AP's utilization. When an AP gets too busy, the backend
moves simulated devices to the AP with the most spare capacity and logs the
move. A React dashboard shows everything live.

Team: Priyanka J, Sumedha Phadnis

## Architecture

| Layer | Service |
|---|---|
| Client | React + Vite dashboard (AWS Amplify Hosting); phone check-in page (Amazon S3) |
| Edge | Amazon API Gateway HTTP API (`CampusNetSim-API`) |
| Compute | 10 AWS Lambda functions (Python) |
| Storage | 4 Amazon DynamoDB tables (on-demand) with DynamoDB Streams |
| Monitoring | Amazon CloudWatch Logs |

See `infrastructure/aws_resources.md` for every deployed resource, and
`docs/api.md` for the API contract.

## Repository layout

```
backend/
  lambdas/              Source of every deployed Lambda function
    event_processor/      POST /events          (CampusNetSim-EventProcessor)
    device_registry/      GET|POST /devices     (CampusNetSim-DeviceRegistry)
    status_reader/        GET /aps              (CampusNetSim-StatusReader)
    update_ap_config/     PUT /aps/{id}/config  (UpdateAPConfig)
    history_reader/       GET /aps/{id}/history (CampusNetSim-HistoryReader)
    migration_reader/     GET /migrations       (CampusNetSim-MigrationReader)
    admin_reset/          POST /admin/reset     (CampusNetSim-AdminReset)
    load_balancer/        APState stream        (CampusNetSim-LoadBalancer)
    history_writer/       APState stream        (CampusNetSim-HistoryWriter)
    traffic_generator/    manual invocation     (CampusNetSim-TrafficGenerator)
  legacy/chat/          Retired chat function (not used by the final system)
checkin/index.html      Phone check-in page served from S3
dashboard/              React + Vite dashboard (deployed to AWS Amplify)
infrastructure/
  template.yaml         AWS SAM template recreating the whole stack
  aws_resources.md      Deployed resource inventory
  seed_ap_state.json    AP layout and capacities used in the final demo
  seed_dynamodb.py      Seeds CampusNetSim_APState from simulator/config.py
  setup_history_table.py  Creates APHistory and enables the APState stream
simulator/              Local Python traffic simulator and analytics
tests/                  Unit tests for the local simulator
docs/api.md             API reference
reports/                Final IEEE report
```

## Running the dashboard locally

```
cd dashboard
npm install
npm run dev
```

The dashboard talks straight to the deployed API, so no local backend is
needed.

To deploy it to Amplify, run `npm run build`, then `python make_zip.py` (it
builds a ZIP with forward-slash paths), and upload the ZIP in the Amplify
console.

## Deploying the backend

With the AWS SAM CLI installed and AWS credentials configured:

```
cd infrastructure
sam build
sam deploy --guided
```

Then load the AP layout (`seed_ap_state.json`) into `CampusNetSim_APState`,
upload `checkin/index.html` to an S3 bucket with static access, and point
`API_BASE` in `checkin/index.html` and `dashboard/src/data/api.js` at the new
API URL.

## Running the local simulator and tests

```
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt pytest
python -m simulator.main
python -m pytest tests
```

## License

MIT (see `LICENSE`).
