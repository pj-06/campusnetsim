import { Users } from "lucide-react";
import { colors } from "../theme.js";

// Based on last_seen (refreshed on every JOIN), not joined_at -- joined_at
// only reflects a device's very first-ever join, so a phone whose device_id
// was already known (e.g. it reconnected after a while) would otherwise show
// a stale, confusing "18m ago" the instant someone taps Join.
function activeAgo(iso) {
  const diffMs = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diffMs / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  return `${hrs}h ago`;
}

export default function RosterPanel({ devices }) {
  return (
    <div className="p-4 h-full" style={{ background: colors.panel, border: `1px solid ${colors.border}` }}>
      <div className="flex items-center gap-2 mb-4">
        <Users size={14} color={colors.accent} strokeWidth={2.25} />
        <span style={{ color: colors.textPrimary, fontSize: 13, fontWeight: 600, fontFamily: "'Space Grotesk', sans-serif" }}>
          Connected devices ({devices.length})
        </span>
      </div>
      {devices.length === 0 && (
        <p style={{ color: colors.textFaint, fontSize: 13 }}>
          No phones checked in yet — scan an AP's QR code and hit Join to appear here live.
        </p>
      )}
      <div className="flex flex-col gap-2" style={{ maxHeight: 220, overflowY: "auto" }}>
        {devices.map((d) => (
          <div
            key={d.device_id}
            className="p-2.5 flex items-center justify-between"
            style={{ background: colors.panelAlt, borderLeft: `3px solid ${colors.Normal}` }}
          >
            <div>
              <span style={{ color: colors.textPrimary, fontSize: 13, fontWeight: 600 }}>{d.nickname}</span>
              <span style={{ color: colors.textFaint, fontSize: 11, marginLeft: 8, fontFamily: "ui-monospace, monospace" }}>
                {d.ap_id}
              </span>
            </div>
            <span style={{ color: colors.textFaint, fontSize: 11 }}>{activeAgo(d.last_seen)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
