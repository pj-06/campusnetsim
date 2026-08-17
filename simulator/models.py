from dataclasses import dataclass
from datetime import datetime


@dataclass
class WiFiEvent:
    event_id: str
    timestamp: str
    device_id: str
    ap_id: str
    building: str
    event_type: str

    def to_dict(self):
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "device_id": self.device_id,
            "ap_id": self.ap_id,
            "building": self.building,
            "event_type": self.event_type
        }