from simulator.analytics import calculate_utilization, get_status, available_capacity


def test_calculate_utilization_basic():
    assert calculate_utilization(50, 100) == 50
    assert calculate_utilization(0, 100) == 0
    assert calculate_utilization(10, 0) == 0  # avoid divide-by-zero


def test_get_status_thresholds():
    assert get_status(0) == "NORMAL"
    assert get_status(69.9) == "NORMAL"
    assert get_status(70) == "BUSY"
    assert get_status(89.9) == "BUSY"
    assert get_status(90) == "HIGH_LOAD"
    assert get_status(99.9) == "HIGH_LOAD"
    assert get_status(100) == "CONGESTED"
    assert get_status(150) == "CONGESTED"


def test_available_capacity():
    assert available_capacity(30, 50) == 20
    assert available_capacity(60, 50) == 0  # never negative
