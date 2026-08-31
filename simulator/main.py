"""
main.py
--------
Phase 1 entry point: run the simulator for a stretch of simulated time,
print periodic AP status snapshots, flag congestion + recommendations
as they happen, and log every event to data/generated/events.jsonl.

This replaces the earlier bootstrap version, which only printed 10
random events and one hardcoded utilization example (72/75) -- there
was no live state behind it yet. Now every number printed here comes
from actual simulated CONNECT/DISCONNECT events applied to NetworkState.

Usage:
    python -m simulator.main
"""

import json
import os
import random
from datetime import datetime, timedelta

from simulator.network_state import NetworkState
from simulator.traffic_generator import generate_events_for_minute

NUM_DEVICES = 300
SIM_MINUTES = 120
START_HOUR = 8
SEED = 42
SUMMARY_EVERY_N_MINUTES = 15
EVENTS_OUT_PATH = "data/generated/events.jsonl"


def build_device_pool():
    return [f"device_{i:04d}" for i in range(NUM_DEVICES)]


def build_ap_popularity(state, rng):
    return {ap_id: rng.uniform(0.6, 1.6) for ap_id in state.ap_info}


def log_event(event):
    os.makedirs(os.path.dirname(EVENTS_OUT_PATH), exist_ok=True)
    with open(EVENTS_OUT_PATH, "a") as f:
        f.write(json.dumps(event.to_dict()) + "\n")


def print_snapshot(state, minute_offset):
    print(f"\n--- t+{minute_offset} min ---")
    for row in state.snapshot():
        flag = " <==" if row["status"] in ("HIGH_LOAD", "CONGESTED") else ""
        print(
            f"  {row['ap_id']:5s} ({row['building']:14s}) "
            f"{row['current_users']:3d}/{row['capacity']:3d} = "
            f"{row['utilization']:6.2f}%  {row['status']:10s}{flag}"
        )


def main():
    random.seed(SEED)
    rng = random.Random(SEED)

    os.makedirs(os.path.dirname(EVENTS_OUT_PATH), exist_ok=True)
    open(EVENTS_OUT_PATH, "w").close()  # truncate any previous run's events

    device_pool = build_device_pool()
    state = NetworkState(device_pool=device_pool)
    ap_popularity = build_ap_popularity(state, rng)

    sim_start = datetime(2026, 8, 17, START_HOUR, 0, 0)

    print("=== CampusNetSim ===")
    print(f"devices={NUM_DEVICES}  minutes={SIM_MINUTES}  start_hour={START_HOUR}\n")

    total_events = 0
    congestion_hits = 0

    for minute_offset in range(SIM_MINUTES):
        sim_time = sim_start + timedelta(minutes=minute_offset)
        results = generate_events_for_minute(state, sim_time, ap_popularity)

        for event, record in results:
            log_event(event)
            total_events += 1

            if record["status"] == "CONGESTED" and record["recommendation"]:
                congestion_hits += 1
                rec = record["recommendation"]
                print(
                    f"  [CONGESTION] t+{minute_offset}min {record['ap_id']} "
                    f"({record['building']}) at {record['utilization']}% -> "
                    f"recommend {rec['recommended_ap_id']} "
                    f"(avail {rec['available_capacity']}, "
                    f"projected {rec['projected_utilization']}%)"
                )

        if minute_offset % SUMMARY_EVERY_N_MINUTES == 0:
            print_snapshot(state, minute_offset)

    print_snapshot(state, SIM_MINUTES)
    print(f"\nDone. {total_events} events generated, "
          f"{congestion_hits} congestion recommendations fired.")
    print(f"Events written to: {EVENTS_OUT_PATH}")


if __name__ == "__main__":
    main()
