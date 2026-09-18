import { Wifi } from "lucide-react";
import { colors } from "../theme.js";

function StatusTag({ status }) {
  return (
    <span
      style={{
        display: "inline-block",
        width: 7,
        height: 7,
        background: colors[status],
        marginRight: 7,
      }}
    />
  );
}

export default function APCard({ ap, selected, onSelect }) {
  const pctCapped = Math.min(ap.utilization_pct, 100);
  return (
    <button
      onClick={() => onSelect(ap.ap_id)}
      className="text-left p-3"
      style={{
        background: selected ? colors.panelAlt : colors.panel,
        border: `1px solid ${selected ? colors.borderStrong : colors.border}`,
        cursor: "pointer",
      }}
    >
      <div className="flex items-center justify-between mb-3">
        <div>
          <div style={{ color: colors.textFaint, fontSize: 11, fontFamily: "ui-monospace, monospace" }}>{ap.ap_id}</div>
          <div style={{ color: colors.textPrimary, fontSize: 13.5, fontWeight: 600, fontFamily: "'Space Grotesk', sans-serif" }}>{ap.building}</div>
        </div>
        <Wifi size={15} color={colors[ap.status]} strokeWidth={2.25} />
      </div>

      <div className="flex items-baseline gap-1 mb-2">
        <span style={{ fontFamily: "ui-monospace, monospace", fontSize: 24, color: colors.textPrimary, fontWeight: 600 }}>
          {ap.utilization_pct}
        </span>
        <span style={{ color: colors.textSecondary, fontSize: 12 }}>%</span>
      </div>

      <div className="w-full mb-3" style={{ height: 3, background: colors.border, overflow: "hidden" }}>
        <div style={{ width: `${pctCapped}%`, height: "100%", background: colors[ap.status] }} />
      </div>

      <div className="flex items-center justify-between">
        <div className="flex items-center">
          <StatusTag status={ap.status} />
          <span style={{ color: colors.textSecondary, fontSize: 12 }}>{ap.status}</span>
        </div>
        <span style={{ color: colors.textFaint, fontSize: 11, fontFamily: "ui-monospace, monospace" }}>
          {ap.connected_count}/{ap.capacity}
        </span>
      </div>
    </button>
  );
}
