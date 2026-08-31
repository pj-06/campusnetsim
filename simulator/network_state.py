"""
network_state.py
------------------
The piece that was missing between models.py (event shape) and
analytics.py (utilization/status math): something that actually keeps
track of which devices are connected to which AP right now.

Before this file existed, main.py computed utilization from a hardcoded
example (72/75) because there was no live state to read it from.
NetworkState.apply_event() is the function that will later become the
core of the Lambda handler in backend/local/event_processor.py (and
eventually lambda/event_processor -- same logic, different trigger).
"""

from simulator.config import CAMPUS
from simulator.analytics import calculate_utilization, get_status, recommend_ap


def build_ap_capacity_lookup():
    lookup = {}
    for building, aps in CAMPUS.items():
        for ap_id, capacity in aps.items():
            lookup[ap_id] = {"building": building, "capacity": capacity}
    return lookup


class NetworkState:
    """In-memory record of every AP's connected devices.

    This mirrors what will later live in DynamoDB: one item per AP,
    keyed by ap_id, with current_users/capacity/status as attributes.
    """

    def __init__(self, device_pool=None):
        self.ap_info = build_ap_capacity_lookup()
        self.connected_devices = {ap_id: set() for ap_id in self.ap_info}
        self.device_location = {}  # device_id -> ap_id, for CONNECT/DISCONNECT lookups
        self.device_pool = device_pool or []

    def is_connected(self, device_id):
        return device_id in self.device_location

    def apply_event(self, event):
        """Apply one WiFiEvent and return the resulting AP status record.

        This is the function signature we will reuse almost unchanged
        inside the Lambda handler once API Gateway exists.
        """
        ap_id = event.ap_id
        device_id = event.device_id
        event_type = event.event_type

        if ap_id not in self.ap_info:
            raise ValueError(f"Unknown ap_id: {ap_id}")

        if event_type == "CONNECT":
            prev_ap = self.device_location.get(device_id)
            if prev_ap and prev_ap != ap_id:
                self.connected_devices[prev_ap].discard(device_id)
            self.connected_devices[ap_id].add(device_id)
            self.device_location[device_id] = ap_id

        elif event_type == "DISCONNECT":
            self.connected_devices[ap_id].discard(device_id)
            if self.device_location.get(device_id) == ap_id:
                del self.device_location[device_id]

        else:
            raise ValueError(f"Unknown event_type: {event_type}")

        return self.get_ap_status(ap_id)

    def get_ap_status(self, ap_id):
        info = self.ap_info[ap_id]
        current_users = len(self.connected_devices[ap_id])
        capacity = info["capacity"]

        utilization = calculate_utilization(current_users, capacity)
        status = get_status(utilization)

        record = {
            "ap_id": ap_id,
            "building": info["building"],
            "current_users": current_users,
            "capacity": capacity,
            "utilization": round(utilization, 2),
            "status": status,
            "recommendation": None,
        }

        if status == "CONGESTED":
            record["recommendation"] = recommend_ap(self, ap_id)

        return record

    def snapshot(self):
        return [self.get_ap_status(ap_id) for ap_id in sorted(self.ap_info)]
