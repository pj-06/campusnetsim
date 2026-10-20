
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  LineChart,
  Line,
  ReferenceLine,
  Cell,
} from "recharts";
import { Radio, RotateCcw } from "lucide-react";
import { colors } from "./theme.js";
import {
  getAPs,
  getServerHistory,
  getMigrations,
  getDevices,
  resetSimulation,
} from "./data/api.js";
import APCard from "./components/APCard.jsx";
import APDetailsPanel from "./components/APDetailsPanel.jsx";
import CustomTooltip from "./components/CustomTooltip.jsx";
import MigrationHistory from "./components/MigrationHistory.jsx";
import RosterPanel from "./components/RosterPanel.jsx";

const API_BASE =
  "https://0iczavlx88.execute-api.ap-south-1.amazonaws.com";

const POLL_INTERVAL_MS = 5000;
const MAX_HISTORY_POINTS = 60;

// Update the capacity stored by the existing AWS API.
async function updateAPCapacity(apId, capacity) {
  const response = await fetch(
    `${API_BASE}/aps/${encodeURIComponent(apId)}/config`,
    {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ capacity }),
    }
  );

  if (!response.ok) {
    let message = `HTTP ${response.status}`;

    try {
      const data = await response.json();
      message = data.error || data.message || message;
    } catch {
      // Keep the HTTP status if the response isn't JSON.
    }

    throw new Error(message);
  }

  return response.json();
}

export default function App() {
  const [aps, setAps] = useState([]);
  const [history, setHistory] = useState({});
  const [seededFromServer, setSeededFromServer] = useState(new Set());
  const [selectedAP, setSelectedAP] = useState(null);
  const [error, setError] = useState(null);
  const [migrations, setMigrations] = useState([]);
  const [devices, setDevices] = useState([]);
  const [resetting, setResetting] = useState(false);
  const [resetMsg, setResetMsg] = useState(null);

  // Capacity editor state.
  const [editingCapacity, setEditingCapacity] = useState(false);
  const [capacityDraft, setCapacityDraft] = useState("");
  const [capacityMsg, setCapacityMsg] = useState(null);
  const [savingCapacity, setSavingCapacity] = useState(false);

  // Fetch live AP data, migration history and connected devices.
  const refreshAll = useCallback(async () => {
    try {
      const data = await getAPs();

      setAps(data);
      setError(null);

      setSelectedAP((prev) => prev ?? data[0]?.ap_id ?? null);

      setHistory((prev) => {
        const next = { ...prev };

        for (const ap of data) {
          const point = {
            time: new Date(ap.timestamp).toLocaleTimeString([], {
              hour: "2-digit",
              minute: "2-digit",
              second: "2-digit",
            }),
            utilization_pct: ap.utilization_pct,
          };

          const series = [...(next[ap.ap_id] ?? []), point];
          next[ap.ap_id] = series.slice(-MAX_HISTORY_POINTS);
        }

        return next;
      });

      setMigrations(await getMigrations().catch(() => []));
      setDevices(await getDevices().catch(() => []));
    } catch (err) {
      setError(err.message);
    }
  }, []);

  // Save the selected AP's new capacity.
  async function handleSaveCapacity() {
    if (!selectedAPData || savingCapacity) return;

    const newCapacity = Number(capacityDraft);

    if (!Number.isInteger(newCapacity) || newCapacity < 1) {
      setCapacityMsg("Enter a valid positive whole number.");
      return;
    }

    if (newCapacity < selectedAPData.connected_count) {
      setCapacityMsg(
        `Capacity cannot be lower than the ${selectedAPData.connected_count} currently connected devices.`
      );
      return;
    }

    setSavingCapacity(true);
    setCapacityMsg(null);

    try {
      await updateAPCapacity(selectedAP, newCapacity);

      // Refresh AP data so the cards show the saved capacity.
      await refreshAll();

      setEditingCapacity(false);
      setCapacityMsg(
        `${selectedAP} capacity updated to ${newCapacity}.`
      );
    } catch (err) {
      setCapacityMsg(`Update failed: ${err.message}`);
    } finally {
      setSavingCapacity(false);
    }
  }

  // Reset simulation and refresh the dashboard.
  async function handleReset() {
    if (resetting) return;

    const confirmed = window.confirm(
      "Reset the simulation?\n\nThis permanently deletes all migration history and AP traffic history, and sets every access point back to 0 connected devices / 0% utilization. This cannot be undone."
    );

    if (!confirmed) return;

    setResetting(true);
    setResetMsg(null);

    try {
      const result = await resetSimulation();

      setHistory({});
      setSeededFromServer(new Set());

      await refreshAll();

      setResetMsg(
        `Reset complete — ${result.aps_reset} APs cleared, ${result.migrations_deleted} migrations deleted, ${result.history_deleted} history rows deleted.`
      );
    } catch (err) {
      setResetMsg(`Reset failed: ${err.message}`);
    } finally {
      setResetting(false);
    }
  }

  // Load stored server history for the selected AP.
  useEffect(() => {
    if (!selectedAP || seededFromServer.has(selectedAP)) return;

    let cancelled = false;

    getServerHistory(selectedAP)
      .then((serverPoints) => {
        if (cancelled || serverPoints.length === 0) return;

        setHistory((prev) => ({
          ...prev,
          [selectedAP]: [
            ...serverPoints,
            ...(prev[selectedAP] ?? []),
          ].slice(-MAX_HISTORY_POINTS),
        }));
      })
      .catch(() => {
        // Fall back to history accumulated by live polling.
      })
      .finally(() => {
        if (!cancelled) {
          setSeededFromServer((prev) => new Set(prev).add(selectedAP));
        }
      });

    return () => {
      cancelled = true;
    };
  }, [selectedAP, seededFromServer]);

  // Poll live data every five seconds.
  useEffect(() => {
    let cancelled = false;

    async function poll() {
      if (cancelled) return;
      await refreshAll();
    }

    poll();

    const interval = setInterval(poll, POLL_INTERVAL_MS);

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [refreshAll]);

  // Current selected AP and its devices.
  const historyData = useMemo(
    () => (selectedAP ? history[selectedAP] ?? [] : []),
    [selectedAP, history]
  );

  const selectedAPData = aps.find(
    (ap) => ap.ap_id === selectedAP
  );

  const selectedAPDevices = devices.filter(
    (device) => device.ap_id === selectedAP
  );

  // Loading and API error state.
  if (aps.length === 0) {
    return (
      <div
        style={{
          background: colors.bg,
          minHeight: "100svh",
          fontFamily: "'Inter', system-ui, sans-serif",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <div
          style={{
            color: error ? colors.Congested : colors.textFaint,
            fontSize: 13,
          }}
        >
          {error
            ? `Failed to load access points: ${error}`
            : "Loading access points…"}
        </div>
      </div>
    );
  }

  const congestedCount = aps.filter(
    (a) => a.status === "Congested" || a.status === "High Load"
  ).length;

  const avgUtil = Math.round(
    aps.reduce((sum, ap) => sum + ap.utilization_pct, 0) / aps.length
  );

  const barData = aps.map((ap) => ({
    name: ap.ap_id,
    utilization_pct: ap.utilization_pct,
    status: ap.status,
  }));

  return (
    <div
      style={{
        background: colors.bg,
        minHeight: "100%",
        fontFamily: "'Inter', system-ui, sans-serif",
        backgroundImage: `radial-gradient(${colors.border} 1px, transparent 1px)`,
        backgroundSize: "22px 22px",
      }}
      className="p-6"
    >
      {/* Header */}
      <div
        className="flex items-center justify-between mb-6 pb-4"
        style={{ borderBottom: `2px solid ${colors.borderStrong}` }}
      >
        <div className="flex items-center gap-3">
          <Radio size={19} color={colors.accent} strokeWidth={2.25} />

          <div>
            <div
              style={{
                color: colors.textPrimary,
                fontSize: 17,
                fontWeight: 700,
                fontFamily: "'Space Grotesk', sans-serif",
                letterSpacing: -0.3,
              }}
            >
              CampusNetSim
            </div>

            <div style={{ color: colors.textFaint, fontSize: 11.5 }}>
              Smart campus WiFi congestion monitor
            </div>
          </div>
        </div>

        <div className="flex items-center gap-7">
          <div>
            <div style={{ color: colors.textFaint, fontSize: 11.5 }}>
              Access points
            </div>
            <div
              style={{
                color: colors.textPrimary,
                fontSize: 15,
                fontFamily: "ui-monospace, monospace",
                fontWeight: 600,
              }}
            >
              {aps.length}
            </div>
          </div>

          <div>
            <div style={{ color: colors.textFaint, fontSize: 11.5 }}>
              Avg. utilization
            </div>
            <div
              style={{
                color: colors.textPrimary,
                fontSize: 15,
                fontFamily: "ui-monospace, monospace",
                fontWeight: 600,
              }}
            >
              {avgUtil}%
            </div>
          </div>

          <div>
            <div style={{ color: colors.textFaint, fontSize: 11.5 }}>
              Needs attention
            </div>
            <div
              style={{
                color: congestedCount
                  ? colors["High Load"]
                  : colors.Normal,
                fontSize: 15,
                fontFamily: "ui-monospace, monospace",
                fontWeight: 600,
              }}
            >
              {congestedCount}
            </div>
          </div>

          <button
            onClick={handleReset}
            disabled={resetting}
            className="flex items-center gap-1.5 px-3 py-1.5"
            style={{
              background: colors.panel,
              border: `1px solid ${colors.Congested}`,
              color: colors.Congested,
              fontSize: 12,
              fontWeight: 600,
              fontFamily: "'Space Grotesk', sans-serif",
              cursor: resetting ? "not-allowed" : "pointer",
              opacity: resetting ? 0.55 : 1,
            }}
            title="Wipe migration + traffic history and zero out all APs"
          >
            <RotateCcw size={13} strokeWidth={2.25} />
            {resetting ? "Resetting…" : "Reset simulation"}
          </button>
        </div>
      </div>

      {/* Reset message */}
      {resetMsg && (
        <div
          className="mb-4 px-3 py-2"
          style={{
            background: colors.panelAlt,
            border: `1px solid ${
              resetMsg.startsWith("Reset failed")
                ? colors.Congested
                : colors.Normal
            }`,
            color: resetMsg.startsWith("Reset failed")
              ? colors.Congested
              : colors.Normal,
            fontSize: 12,
          }}
        >
          {resetMsg}
        </div>
      )}

      {/* Access point cards */}
      <div className="grid grid-cols-4 gap-3 mb-4">
        {aps.map((ap) => (
          <APCard
            key={ap.ap_id}
            ap={ap}
            selected={ap.ap_id === selectedAP}
            onSelect={setSelectedAP}
          />
        ))}
      </div>

      {/* Capacity editor */}
      <div
        className="p-4 mb-4"
        style={{
          background: colors.panel,
          border: `1px solid ${colors.border}`,
        }}
      >
        <div
          style={{
            color: colors.textPrimary,
            fontSize: 14,
            fontWeight: 600,
            marginBottom: 10,
          }}
        >
          Access Point Capacity
        </div>

        <div
          className="flex items-center gap-3 flex-wrap"
          style={{ color: colors.textFaint, fontSize: 12 }}
        >
          <span>
            Selected AP:{" "}
            <strong style={{ color: colors.textPrimary }}>
              {selectedAPData?.ap_id}
            </strong>
          </span>

          <span>
            Current capacity:{" "}
            <strong style={{ color: colors.textPrimary }}>
              {selectedAPData?.capacity}
            </strong>
          </span>

          {!editingCapacity && selectedAPData && (
            <button
              onClick={() => {
                setCapacityDraft(String(selectedAPData.capacity));
                setCapacityMsg(null);
                setEditingCapacity(true);
              }}
              style={{
                padding: "7px 12px",
                border: `1px solid ${colors.accent}`,
                color: colors.accent,
                background: colors.panel,
                cursor: "pointer",
                fontSize: 12,
                fontWeight: 600,
              }}
            >
              Edit capacity
            </button>
          )}
        </div>

        {editingCapacity && selectedAPData && (
          <form
            onSubmit={(event) => {
              event.preventDefault();
              handleSaveCapacity();
            }}
            className="flex items-center gap-2 flex-wrap mt-3"
          >
            <label
              htmlFor="capacity-input"
              style={{ color: colors.textPrimary, fontSize: 12 }}
            >
              New maximum devices:
            </label>

            <input
              id="capacity-input"
              type="number"
              min={Math.max(1, selectedAPData.connected_count)}
              step="1"
              required
              value={capacityDraft}
              onChange={(event) => setCapacityDraft(event.target.value)}
              style={{
                width: 100,
                padding: "7px",
                border: `1px solid ${colors.border}`,
                background: colors.panel,
                color: colors.textPrimary,
              }}
            />

            <button
              type="submit"
              disabled={savingCapacity}
              style={{
                padding: "7px 12px",
                background: colors.Normal,
                color: "#ffffff",
                border: "none",
                cursor: savingCapacity ? "wait" : "pointer",
                opacity: savingCapacity ? 0.6 : 1,
              }}
            >
              {savingCapacity ? "Saving..." : "Save"}
            </button>

            <button
              type="button"
              disabled={savingCapacity}
              onClick={() => {
                setEditingCapacity(false);
                setCapacityMsg(null);
              }}
              style={{
                padding: "7px 12px",
                border: `1px solid ${colors.border}`,
                color: colors.textPrimary,
                background: colors.panel,
                cursor: "pointer",
              }}
            >
              Cancel
            </button>
          </form>
        )}

        {capacityMsg && (
          <p
            style={{
              marginTop: 10,
              fontSize: 12,
              color: capacityMsg.startsWith("Update failed")
                ? colors.Congested
                : colors.Normal,
            }}
          >
            {capacityMsg}
          </p>
        )}
      </div>

      {/* Selected access point details */}
      <APDetailsPanel
        ap={selectedAPData}
        devices={selectedAPDevices}
      />

      {/* Utilization bar chart */}
      <div
        className="p-4 mb-4"
        style={{
          background: colors.panel,
          border: `1px solid ${colors.border}`,
        }}
      >
        <div className="mb-3">
          <span
            style={{
              color: colors.textPrimary,
              fontSize: 13,
              fontWeight: 600,
              fontFamily: "'Space Grotesk', sans-serif",
            }}
          >
            Utilization across access points
          </span>
        </div>

        <ResponsiveContainer width="100%" height={180}>
          <BarChart
            data={barData}
            margin={{ top: 5, right: 5, left: -20, bottom: 0 }}
          >
            <CartesianGrid
              strokeDasharray="3 3"
              stroke={colors.border}
              vertical={false}
            />
            <XAxis
              dataKey="name"
              tick={{ fill: colors.textFaint, fontSize: 11 }}
              axisLine={{ stroke: colors.border }}
              tickLine={false}
            />
            <YAxis
              tick={{ fill: colors.textFaint, fontSize: 11 }}
              axisLine={false}
              tickLine={false}
              domain={[0, 120]}
            />
            <Tooltip
              content={<CustomTooltip />}
              cursor={{ fill: colors.panelAlt }}
            />
            <ReferenceLine
              y={70}
              stroke={colors.Busy}
              strokeDasharray="4 4"
              strokeOpacity={0.6}
            />
            <ReferenceLine
              y={90}
              stroke={colors["High Load"]}
              strokeDasharray="4 4"
              strokeOpacity={0.6}
            />
            <Bar
              dataKey="utilization_pct"
              name="Utilization"
              radius={[0, 0, 0, 0]}
            >
              {barData.map((data, index) => (
                <Cell key={index} fill={colors[data.status]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Automated load balancing history */}
      <div className="mb-4">
        <MigrationHistory migrations={migrations} />
      </div>

      {/* Live phone check-in roster */}
      <div className="mb-4">
        <RosterPanel devices={devices} />
      </div>

      {/* Traffic trend */}
      <div
        className="p-4"
        style={{
          background: colors.panel,
          border: `1px solid ${colors.border}`,
        }}
      >
        <div className="flex items-center justify-between mb-3">
          <span
            style={{
              color: colors.textPrimary,
              fontSize: 13,
              fontWeight: 600,
              fontFamily: "'Space Grotesk', sans-serif",
            }}
          >
            Traffic trend
          </span>

          <select
            value={selectedAP ?? ""}
            onChange={(event) => setSelectedAP(event.target.value)}
            className="px-2 py-1"
            style={{
              background: colors.panel,
              border: `1px solid ${colors.border}`,
              color: colors.textPrimary,
              fontSize: 12,
            }}
          >
            {aps.map((ap) => (
              <option key={ap.ap_id} value={ap.ap_id}>
                {ap.ap_id} — {ap.building}
              </option>
            ))}
          </select>
        </div>

        <ResponsiveContainer width="100%" height={180}>
          <LineChart
            data={historyData}
            margin={{ top: 5, right: 5, left: -20, bottom: 0 }}
          >
            <CartesianGrid
              strokeDasharray="3 3"
              stroke={colors.border}
              vertical={false}
            />
            <XAxis
              dataKey="time"
              tick={{ fill: colors.textFaint, fontSize: 11 }}
              axisLine={{ stroke: colors.border }}
              tickLine={false}
            />
            <YAxis
              tick={{ fill: colors.textFaint, fontSize: 11 }}
              axisLine={false}
              tickLine={false}
              domain={[0, 120]}
            />
            <Tooltip content={<CustomTooltip />} />
            <ReferenceLine
              y={70}
              stroke={colors.Busy}
              strokeDasharray="4 4"
              strokeOpacity={0.6}
            />
            <ReferenceLine
              y={90}
              stroke={colors["High Load"]}
              strokeDasharray="4 4"
              strokeOpacity={0.6}
            />
            <Line
              type="monotone"
              dataKey="utilization_pct"
              name="Utilization"
              stroke={colors.accent}
              strokeWidth={2}
              dot={{ r: 3, fill: colors.accent }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Data source information */}
      <div
        style={{
          color: colors.textFaint,
          fontSize: 10.5,
          marginTop: 14,
        }}
      >
        Access point data is live, polled every {POLL_INTERVAL_MS / 1000}s
        from GET /aps. Traffic trend loads stored history from GET
        /aps/{"{ap_id}"}/history where available, then stays live via the
        same poll. Connected devices poll the same cadence from GET /devices.
      </div>
    </div>
  );
}
