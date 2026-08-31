import random
import uuid
from datetime import datetime

from simulator.config import CAMPUS
from simulator.models import WiFiEvent


# Hour-of-day activity weight (0.0-1.0) per building, for a "normal
# weekday". This is a simplified, explainable stand-in for the
# spatio-temporal patterns reported in our literature review (Ruiz et
# al. 2024; Oliveira et al. 2016) -- academic block peaks during class
# hours, library stays moderate through the day, hostel is busiest at
# night. NOT a fitted statistical model, just a shape that avoids the
# "purely random events" pitfall the proposal explicitly calls out.
HOURLY_WEIGHT = {
    "academic_block": {
        0: 0.05, 1: 0.05, 2: 0.05, 3: 0.05, 4: 0.05, 5: 0.05,
        6: 0.10, 7: 0.25, 8: 0.55, 9: 0.85, 10: 0.90, 11: 0.90,
        12: 0.70, 13: 0.60, 14: 0.85, 15: 0.85, 16: 0.70, 17: 0.45,
        18: 0.25, 19: 0.15, 20: 0.10, 21: 0.10, 22: 0.05, 23: 0.05,
    },
    "library": {
        0: 0.05, 1: 0.05, 2: 0.05, 3: 0.05, 4: 0.05, 5: 0.05,
        6: 0.10, 7: 0.20, 8: 0.35, 9: 0.45, 10: 0.55, 11: 0.55,
        12: 0.45, 13: 0.45, 14: 0.55, 15: 0.60, 16: 0.60, 17: 0.55,
        18: 0.50, 19: 0.55, 20: 0.60, 21: 0.55, 22: 0.35, 23: 0.15,
    },
    "hostel": {
        0: 0.20, 1: 0.10, 2: 0.05, 3: 0.05, 4: 0.05, 5: 0.10,
        6: 0.20, 7: 0.25, 8: 0.20, 9: 0.15, 10: 0.15, 11: 0.15,
        12: 0.25, 13: 0.20, 14: 0.15, 15: 0.15, 16: 0.20, 17: 0.30,
        18: 0.55, 19: 0.75, 20: 0.90, 21: 0.95, 22: 0.85, 23: 0.55,
    },
}


def get_all_aps():
    aps = []

    for building, building_aps in CAMPUS.items():
        for ap_id, capacity in building_aps.items():
            aps.append({
                "ap_id": ap_id,
                "building": building,
                "capacity": capacity
            })

    return aps


def generate_random_event():
    """Original Phase-1 bootstrap generator: a fully random event, no
    notion of time-of-day and no awareness of which devices are already
    connected. Kept only as a quick smoke-test / demo helper --
    generate_events_for_minute() below is what the simulator actually
    runs now, and is what satisfies the "realistic, not purely random
    traffic" requirement from the proposal."""
    aps = get_all_aps()

    ap = random.choice(aps)

    event_type = random.choice([
        "CONNECT",
        "DISCONNECT"
    ])

    event = WiFiEvent(
        event_id=str(uuid.uuid4()),
        timestamp=datetime.now().isoformat(),
        device_id=f"device_{random.randint(1, 1000)}",
        ap_id=ap["ap_id"],
        building=ap["building"],
        event_type=event_type
    )

    return event


def building_total_capacity(building):
    return sum(CAMPUS[building].values())


def generate_events_for_minute(state, sim_time, ap_popularity):
    """Generate + apply every event for one simulated minute, driven by
    HOURLY_WEIGHT. Returns a list of (event, analytics_record) tuples,
    already applied to `state` -- the same shape main.py will get back
    later whether an event came from this local loop or from a real
    API Gateway request.
    """
    results = []
    hour = sim_time.hour

    for building in CAMPUS:
        weight = HOURLY_WEIGHT[building].get(hour, 0.1)
        target = round(weight * building_total_capacity(building))
        current = sum(
            len(state.connected_devices[ap_id]) for ap_id in CAMPUS[building]
        )
        diff = target - current

        if diff > 0:
            results += _connect_devices(state, building, diff, sim_time, ap_popularity)
        elif diff < 0:
            results += _disconnect_devices(state, building, -diff, sim_time)

    return results


def _connect_devices(state, building, count, sim_time, ap_popularity):
    idle_devices = [d for d in state.device_pool if not state.is_connected(d)]
    random.shuffle(idle_devices)
    chosen_devices = idle_devices[:count]

    aps_in_building = list(CAMPUS[building].keys())
    weights = [ap_popularity[ap_id] for ap_id in aps_in_building]

    results = []
    for device_id in chosen_devices:
        # Devices don't pick the *least loaded* AP -- they pick using a
        # fixed per-AP popularity weight, same as real life (some APs
        # are just nearer a doorway/lecture hall). That's what creates
        # uneven load across APs of similar capacity, matching the
        # AP1=50/AP2=15/AP3=70 example from the proposal, instead of
        # congestion only ever happening when EVERY AP is full.
        ap_id = random.choices(aps_in_building, weights=weights, k=1)[0]
        event = WiFiEvent(
            event_id=str(uuid.uuid4()),
            timestamp=sim_time.isoformat(),
            device_id=device_id,
            ap_id=ap_id,
            building=building,
            event_type="CONNECT",
        )
        record = state.apply_event(event)
        results.append((event, record))
    return results


def _disconnect_devices(state, building, count, sim_time):
    connected = [
        d for d, ap_id in state.device_location.items() if ap_id in CAMPUS[building]
    ]
    random.shuffle(connected)
    chosen_devices = connected[:count]

    results = []
    for device_id in chosen_devices:
        ap_id = state.device_location[device_id]
        event = WiFiEvent(
            event_id=str(uuid.uuid4()),
            timestamp=sim_time.isoformat(),
            device_id=device_id,
            ap_id=ap_id,
            building=building,
            event_type="DISCONNECT",
        )
        record = state.apply_event(event)
        results.append((event, record))
    return results
