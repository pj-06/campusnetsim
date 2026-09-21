import { Repeat, ArrowRight } from "lucide-react";
import { colors } from "../theme.js";

function formatTime(timestamp) {
  return new Date(timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

export default function MigrationHistory({ migrations }) {
  return (
    <div className="p-4" style={{ background: colors.panel, border: `1px solid ${colors.border}` }}>
      <div className="flex items-center gap-2 mb-4">
        <Repeat size={14} color={colors.accent} strokeWidth={2.25} />
        <span style={{ color: colors.textPrimary, fontSize: 13, fontWeight: 600, fontFamily: "'Space Grotesk', sans-serif" }}>
          Automated load balancing
        </span>
      </div>
      {migrations.length === 0 && (
        <p style={{ color: colors.textFaint, fontSize: 13 }}>
          No migrations triggered yet — the system only acts once an AP crosses the load-balancing threshold.
        </p>
      )}
      <div className="flex flex-col gap-2">
        {migrations.map((m) => (
          <div key={m.migration_id} className="p-3" style={{ background: colors.panelAlt, borderLeft: `3px solid ${colors.accent}` }}>
            <div className="flex items-center justify-between mb-1">
              <div className="flex items-center gap-2" style={{ color: colors.textPrimary, fontSize: 13, fontWeight: 600, fontFamily: "ui-monospace, monospace" }}>
                <span>{m.source_ap_id}</span>
                <ArrowRight size={11} />
                <span>{m.target_ap_id}</span>
              </div>
              <span style={{ color: colors.textFaint, fontSize: 11 }}>{formatTime(m.timestamp)}</span>
            </div>
            <div style={{ color: colors.textSecondary, fontSize: 12 }}>
              {m.devices_moved} device{m.devices_moved === 1 ? "" : "s"} moved — {m.source_ap_id} {m.source_utilization_before}% → {m.source_utilization_after}%, {m.target_ap_id} {m.target_utilization_before}% → {m.target_utilization_after}%
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}