import { useCallback, useEffect, useMemo, useState } from "react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  LineChart, Line, ReferenceLine, Cell,
} from "recharts";
import { Radio, RotateCcw } from "lucide-react";
import { colors } from "./theme.js";
import { getAPs, getServerHistory, getMigrations, getDevices, resetSimulation } from "./data/api.js";
import APCard from "./components/APCard.jsx";
import CustomTooltip from "./components/CustomTooltip.jsx";
import MigrationHistory from "./components/MigrationHistory.jsx";
import RosterPanel from "./components/RosterPanel.jsx";

const POLL_INTERVAL_MS = 5000;
// The trend chart is seeded from GET /aps/{ap_id}/history (real stored
// readings -- see docs/api.md) below, and kept moving between poll
// cycles by appending each GET /aps snapshot as it comes in. Capped to
// keep a bounded window in memory either way.
const MAX_HISTORY_POINTS = 60;

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

  // Shared by the poll loop below and the Reset button, so a manual reset
  // can pull fresh (zeroed) data immediately instead of waiting for the
  // next 5s tick.
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
            time: new Date(ap.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }),
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

  // Reset clears server-side state (AP counts, Migrations, APHistory) via
  // POST /admin/reset, but the trend chart's history is accumulated
  // client-side (see MAX_HISTORY_POINTS above) -- without wiping local
  // state too, old pre-reset points would keep dragging the line chart
  // down/up even though the server now says 0%. This is also what fixes
  // the "changed capacity/count but the graph doesn't reflect it" issue:
  // a stale in-memory history array, not a backend problem.
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

  useEffect(() => {
    if (!selectedAP || seededFromServer.has(selectedAP)) return;
    let cancelled = false;

    getServerHistory(selectedAP)
      .then((serverPoints) => {
        if (cancelled || serverPoints.length === 0) return;
        setHistory((prev) => ({
          ...prev,
          [selectedAP]: [...serverPoints, ...(prev[selectedAP] ?? [])].slice(-MAX_HISTORY_POINTS),
        }));
      })
      .catch(() => {
        // History endpoint not deployed yet (see docs/api.md) -- fall back
        // to whatever's been accumulated client-side from live polls.
      })
      .finally(() => {
        if (!cancelled) setSeededFromServer((prev) => new Set(prev).add(selectedAP));
      });

    return () => {
      cancelled = true;
    };
  }, [selectedAP, seededFromServer]);

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

  const historyData = useMemo(() => (selectedAP ? history[selectedAP] ?? [] : []), [selectedAP, history]);

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
        <div style={{ color: error ? colors.Congested : colors.textFaint, fontSize: 13 }}>
          {error ? `Failed to load access points: ${error}` : "Loading access points…"}
        </div>
      </div>
    );
  }

  const congestedCount = aps.filter((a) => a.status === "Congested" || a.status === "High Load").length;
  const avgUtil = Math.round(aps.reduce((s, a) => s + a.utilization_pct, 0) / aps.length);

  const barData = aps.map((a) => ({ name: a.ap_id, utilization_pct: a.utilization_pct, status: a.status }));

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
      <div className="flex items-center justify-between mb-6 pb-4" style={{ borderBottom: `2px solid ${colors.borderStrong}` }}>
        <div className="flex items-center gap-3">
          <Radio size={19} color={colors.accent} strokeWidth={2.25} />
          <div>
            <div style={{ color: colors.textPrimary, fontSize: 17, fontWeight: 700, fontFamily: "'Space Grotesk', sans-serif", letterSpacing: -0.3 }}>
              CampusNetSim
            </div>
            <div style={{ color: colors.textFaint, fontSize: 11.5 }}>Smart campus WiFi congestion monitor</div>
          </div>
        </div>
        <div className="flex items-center gap-7">
          <div>
            <div style={{ color: colors.textFaint, fontSize: 11.5 }}>Access points</div>
            <div style={{ color: colors.textPrimary, fontSize: 15, fontFamily: "ui-monospace, monospace", fontWeight: 600 }}>{aps.length}</div>
          </div>
          <div>
            <div style={{ color: colors.textFaint, fontSize: 11.5 }}>Avg. utilization</div>
            <div style={{ color: colors.textPrimary, fontSize: 15, fontFamily: "ui-monospace, monospace", fontWeight: 600 }}>{avgUtil}%</div>
          </div>
          <div>
            <div style={{ color: colors.textFaint, fontSize: 11.5 }}>Needs attention</div>
            <div style={{ color: congestedCount ? colors["High Load"] : colors.Normal, fontSize: 15, fontFamily: "ui-monospace, monospace", fontWeight: 600 }}>
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

      {resetMsg && (
        <div
          className="mb-4 px-3 py-2"
          style={{
            background: colors.panelAlt,
            border: `1px solid ${resetMsg.startsWith("Reset failed") ? colors.Congested : colors.Normal}`,
            color: resetMsg.startsWith("Reset failed") ? colors.Congested : colors.Normal,
            fontSize: 12,
          }}
        >
          {resetMsg}
        </div>
      )}

      {/* AP grid */}
      <div className="grid grid-cols-4 gap-3 mb-4">
        {aps.map((ap) => (
          <APCard key={ap.ap_id} ap={ap} selected={ap.ap_id === selectedAP} onSelect={setSelectedAP} />
        ))}
      </div>

      {/* Bar chart */}
      <div className="p-4 mb-4" style={{ background: colors.panel, border: `1px solid ${colors.border}` }}>
        <div className="mb-3">
          <span style={{ color: colors.textPrimary, fontSize: 13, fontWeight: 600, fontFamily: "'Space Grotesk', sans-serif" }}>Utilization across access points</span>
        </div>
        <ResponsiveContainer width="100%" height={180}>
          <BarChart data={barData} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke={colors.border} vertical={false} />
            <XAxis dataKey="name" tick={{ fill: colors.textFaint, fontSize: 11 }} axisLine={{ stroke: colors.border }} tickLine={false} />
            <YAxis tick={{ fill: colors.textFaint, fontSize: 11 }} axisLine={false} tickLine={false} domain={[0, 120]} />
            <Tooltip content={<CustomTooltip />} cursor={{ fill: colors.panelAlt }} />
            <ReferenceLine y={70} stroke={colors.Busy} strokeDasharray="4 4" strokeOpacity={0.6} />
            <ReferenceLine y={90} stroke={colors["High Load"]} strokeDasharray="4 4" strokeOpacity={0.6} />
            <Bar dataKey="utilization_pct" name="Utilization" radius={[0, 0, 0, 0]}>
              {barData.map((d, i) => (
                <Cell key={i} fill={colors[d.status]} />
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

      {/* Trend line */}
      <div className="p-4" style={{ background: colors.panel, border: `1px solid ${colors.border}` }}>
        <div className="flex items-center justify-between mb-3">
          <span style={{ color: colors.textPrimary, fontSize: 13, fontWeight: 600, fontFamily: "'Space Grotesk', sans-serif" }}>Traffic trend</span>
          <select
            value={selectedAP}
            onChange={(e) => setSelectedAP(e.target.value)}
            className="px-2 py-1"
            style={{ background: colors.panel, border: `1px solid ${colors.border}`, color: colors.textPrimary, fontSize: 12 }}
          >
            {aps.map((a) => (
              <option key={a.ap_id} value={a.ap_id}>{a.ap_id} — {a.building}</option>
            ))}
          </select>
        </div>
        <ResponsiveContainer width="100%" height={180}>
          <LineChart data={historyData} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke={colors.border} vertical={false} />
            <XAxis dataKey="time" tick={{ fill: colors.textFaint, fontSize: 11 }} axisLine={{ stroke: colors.border }} tickLine={false} />
            <YAxis tick={{ fill: colors.textFaint, fontSize: 11 }} axisLine={false} tickLine={false} domain={[0, 120]} />
            <Tooltip content={<CustomTooltip />} />
            <ReferenceLine y={70} stroke={colors.Busy} strokeDasharray="4 4" strokeOpacity={0.6} />
            <ReferenceLine y={90} stroke={colors["High Load"]} strokeDasharray="4 4" strokeOpacity={0.6} />
            <Line type="monotone" dataKey="utilization_pct" name="Utilization" stroke={colors.accent} strokeWidth={2} dot={{ r: 3, fill: colors.accent }} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div style={{ color: colors.textFaint, fontSize: 10.5, marginTop: 14 }}>
        Access point data is live, polled every {POLL_INTERVAL_MS / 1000}s from GET /aps. Traffic trend loads stored history from GET /aps/{"{ap_id}"}/history where available, then stays live via the same poll. Connected devices poll the same cadence from GET /devices.
      </div>
    </div>
  );
}
