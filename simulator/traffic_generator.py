import random
import uuid
from datetime import datetime

from simulator.config import CAMPUS
from simulator.models import WiFiEvent


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


def generate_event():
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