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

export async function getMigrations() {
  const res = await fetch(`${API_BASE}/migrations`);
  if (!res.ok) throw new Error(`GET /migrations failed: ${res.status}`);
  const data = await res.json();
  return data.migrations;
}

// GET /devices -- the phone check-in roster (see CampusNetSim-DeviceRegistry).
// Each item's status is "CONNECTED" or "DISCONNECTED"; only connected phones
// are shown on the dashboard, newest join first.
export async function getDevices() {
  const res = await fetch(`${API_BASE}/devices`);
  if (!res.ok) throw new Error(`GET /devices failed: ${res.status}`);
  const data = await res.json();
  return data.devices
    .filter((d) => d.status === "CONNECTED")
    .map((d) => ({
      device_id: d.device_id,
      nickname: d.nickname || "Anonymous",
      ap_id: d.ap_id,
      joined_at: d.joined_at,
      last_seen: d.last_seen,
    }))
    .sort((a, b) => new Date(b.joined_at) - new Date(a.joined_at));
}

// POST /admin/reset -- CampusNetSim-AdminReset. Zeroes every AP's
// connected_count/utilization_pct/status and permanently deletes all rows
// from Migrations + APHistory. Irreversible -- callers must confirm with
// the user before calling this. Returns { aps_reset, migrations_deleted, history_deleted }.
export async function resetSimulation() {
  const res = await fetch(`${API_BASE}/admin/reset`, { method: "POST" });
  if (!res.ok) throw new Error(`POST /admin/reset failed: ${res.status}`);
  return res.json();
}


export async function updateAPCapacity(ap_id, capacity) {
  const res = await fetch(
    `${API_BASE}/aps/${encodeURIComponent(ap_id)}/config`,
    {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ capacity }),
    }
  );

  if (!res.ok) {
    let message = `Failed to update capacity: ${res.status}`;

    try {
      const error = await res.json();
      message = error.error || error.message || message;
    } catch {
      // Keep the original error message if the response isn't JSON.
    }

    throw new Error(message);
  }

  return res.json();
}
