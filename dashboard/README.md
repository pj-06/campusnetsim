# CampusNetSim Dashboard (Phase 5)

React + Vite frontend for CampusNetSim. Shows live per-AP utilization,
load-balancing recommendations, and a traffic trend chart, backed by the
Phase 2 API that's already deployed in AWS (Lambda + DynamoDB + API
Gateway, `ap-south-1`).

## Running locally

```
npm install
npm run dev
```

Then open the URL it prints (typically `http://localhost:5173`). There's
nothing to run locally for the backend -- the app talks straight to the
live API (`GET /aps`, polled every 5s), no credentials or local server
needed.

## Data

- **AP grid, recommendations, utilization bar chart** -- live, from
  `GET /aps`.
- **Traffic trend chart** -- seeded from `GET /aps/{ap_id}/history` where
  that's deployed, then extended live from the same poll loop as the AP
  grid. See [`docs/api.md`](../docs/api.md) for the full API contract
  (both endpoints' request/response shapes, error cases, and the campus
  layout) and for how to deploy the history endpoint if it isn't live yet
  (`infrastructure/setup_history_table.py` + the two Lambdas under
  `lambda/history_writer` and `lambda/history_reader`).

Traffic on the live backend may look flat (mostly 0%) if nothing is
actively generating events -- that's expected until a traffic generator
is wired up. You can manually POST a test event any time:

```
curl -X POST https://0iczavlx88.execute-api.ap-south-1.amazonaws.com/events \
  -H "Content-Type: application/json" \
  -d '{"device_id": "test", "ap_id": "AP03", "event_type": "CONNECT"}'
```

## Stack

React 19, Vite, Recharts, Tailwind, lucide-react. Linting via `npm run
lint` (oxlint).
