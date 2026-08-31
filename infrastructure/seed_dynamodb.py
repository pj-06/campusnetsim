"""
seed_dynamodb.py
------------------
One-time (or repeatable) setup script: writes one item per AP into the
CampusNetSim_APState DynamoDB table, using the exact same CAMPUS layout
the local simulator already uses (simulator/config.py) -- so the cloud
table starts out matching local reality instead of being typed by hand
in the console.

Safe to re-run any time you want to reset the table back to zero
traffic (e.g. before a demo), since put_item overwrites existing items
with the same ap_id.

Requires the AWS CLI to be configured first (`aws configure`), using
an access key created for your own IAM user.

Usage:
    python -m infrastructure.seed_dynamodb
"""

import boto3
from datetime import datetime, timezone

from simulator.config import CAMPUS

TABLE_NAME = "CampusNetSim_APState"
REGION = "ap-south-1"


def seed():
    dynamodb = boto3.resource("dynamodb", region_name=REGION)
    table = dynamodb.Table(TABLE_NAME)

    now = datetime.now(timezone.utc).isoformat()
    count = 0

    for building, aps in CAMPUS.items():
        for ap_id, capacity in aps.items():
            table.put_item(Item={
                "ap_id": ap_id,
                "timestamp": now,
                "event_id": None,
                "device_id": None,
                "building": building,
                "connected_count": 0,
                "capacity": capacity,
                "utilization_pct": 0,
                "status": "NORMAL",
                "recommendation": None,
            })
            count += 1
            print(f"  seeded {ap_id} ({building}, capacity={capacity})")

    print(f"\nDone. {count} AP items written to {TABLE_NAME}.")


if __name__ == "__main__":
    seed()
