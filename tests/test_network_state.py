from simulator.network_state import NetworkState
from simulator.models import WiFiEvent


def connect(state, device_id, ap_id, building):
    event = WiFiEvent("evt", "2026-08-17T10:00:00", device_id, ap_id, building, "CONNECT")
    return state.apply_event(event)


def disconnect(state, device_id, ap_id, building):
    event = WiFiEvent("evt", "2026-08-17T10:05:00", device_id, ap_id, building, "DISCONNECT")
    return state.apply_event(event)


def test_connect_increases_utilization():
    state = NetworkState()
    record = connect(state, "d1", "AP01", "academic_block")
    assert record["current_users"] == 1
    assert record["status"] == "NORMAL"


def test_disconnect_frees_capacity():
    state = NetworkState()
    connect(state, "d1", "AP01", "academic_block")
    record = disconnect(state, "d1", "AP01", "academic_block")
    assert record["current_users"] == 0


def test_congestion_triggers_recommendation():
    state = NetworkState()
    last = None
    for i in range(50):  # AP01 capacity is 50 in config.py
        last = connect(state, f"d{i}", "AP01", "academic_block")

    assert last["status"] == "CONGESTED"
    assert last["recommendation"] is not None
    assert last["recommendation"]["recommended_ap_id"] in ("AP02", "AP03")
