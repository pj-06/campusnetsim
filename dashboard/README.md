# Dashboard (Phase 5)

This folder is yours — build the frontend dashboard here with whatever stack
you're comfortable with (plain HTML/JS, React, Vite, etc). It's empty on
purpose.

## Start here

Read [`docs/api.md`](../docs/api.md) first, before writing any dashboard
code. That's the whole contract — the live base URL, both endpoints' exact
request/response shapes, error cases, and the campus layout (which APs
exist, which building each is in, their capacities). Everything the
dashboard needs to know about the backend is in that one file.

## There is nothing to run locally for the backend

The API is already live in AWS, 24/7. You don't need Python, boto3, AWS
credentials, or to run any server. You just need to fetch a URL like any
other public API.

You can ignore these folders entirely — they're either backend internals or
empty unused scaffolding, and none of it is relevant to dashboard work:

- `backend/local/`
- `cloud/`
- `simulator/`
- `infrastructure/`
- `lambda/`

## Fetching data

Point your data fetching at the live endpoint, replacing any mock data:

```js
fetch("https://0iczavlx88.execute-api.ap-south-1.amazonaws.com/aps")
  .then(res => res.json())
  .then(data => console.log(data.aps));
```

That's a plain public `GET`, no auth, CORS already enabled — it'll work
straight from browser JS on localhost or wherever you're developing.

## Heads-up: the data looks flat right now

The table currently mostly shows zero traffic (nothing's continuously
generating live events yet), so the dashboard will look "flat" until a
traffic generator is wired up later. You can still build and test the full
UI against real data shapes — you just won't see numbers actively changing
yet.

If you want to see some movement while building, you can manually POST a
test event any time:

```
curl -X POST https://0iczavlx88.execute-api.ap-south-1.amazonaws.com/events \
  -H "Content-Type: application/json" \
  -d '{"device_id": "test", "ap_id": "AP03", "event_type": "CONNECT"}'
```

## TL;DR

Clone, read `docs/api.md`, build in `dashboard/`, fetch the live URL.
Nothing else in the repo should block you.
