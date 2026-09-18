const API_BASE = "https://0iczavlx88.execute-api.ap-south-1.amazonaws.com";

// Live status values (docs/api.md) are upper-snake-case; components expect
// the same casing the mock data uses.
const STATUS_LABEL = {
  NORMAL: "Normal",
  BUSY: "Busy",
  HIGH_LOAD: "High Load",
  CONGESTED: "Congested",
};

function normalizeAP(raw) {
  return {
    ap_id: raw.ap_id,
    building: raw.building,
    capacity: raw.capacity,
    connected_count: raw.connected_count,
    utilization_pct: raw.utilization_pct,
    status: STATUS_LABEL[raw.status] ?? raw.status,
    timestamp: raw.timestamp,
    recommendation: raw.recommendation
      ? `Redirect new connections to ${raw.recommendation.recommended_ap_id}`
      : null,
  };
}

export async function getAPs() {
  const res = await fetch(`${API_BASE}/aps`);
  if (!res.ok) throw new Error(`GET /aps failed: ${res.status}`);
  const data = await res.json();
  return data.aps.map(normalizeAP);
}

function formatHistoryTime(timestamp) {
  return new Date(timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

// GET /aps/{ap_id}/history doesn't exist until infrastructure/setup_history_table.py
// (see docs/api.md) has been run and the history_writer/history_reader Lambdas are
// deployed. Until then this 404s (or the fetch just fails) and callers should fall
// back to whatever history they've accumulated client-side from live polls.
export async function getServerHistory(ap_id) {
  const res = await fetch(`${API_BASE}/aps/${ap_id}/history`);
  if (!res.ok) throw new Error(`GET /aps/${ap_id}/history failed: ${res.status}`);
  const data = await res.json();
  return data.history.map((point) => ({
    time: formatHistoryTime(point.timestamp),
    utilization_pct: point.utilization_pct,
  }));
}
