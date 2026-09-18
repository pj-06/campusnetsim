import { AlertTriangle, ArrowRight } from "lucide-react";
import { colors } from "../theme.js";

export default function RecommendationsPanel({ aps }) {
  const active = aps.filter((a) => a.recommendation);
  return (
    <div className="p-4 h-full" style={{ background: colors.panel, border: `1px solid ${colors.border}` }}>
      <div className="flex items-center gap-2 mb-4">
        <AlertTriangle size={14} color={colors.accent} strokeWidth={2.25} />
        <span style={{ color: colors.textPrimary, fontSize: 13, fontWeight: 600, fontFamily: "'Space Grotesk', sans-serif" }}>
          Load-balancing recommendations
        </span>
      </div>
      {active.length === 0 && (
        <p style={{ color: colors.textFaint, fontSize: 13 }}>No congestion detected across any access point right now.</p>
      )}
      <div className="flex flex-col gap-2">
        {active.map((a) => (
          <div
            key={a.ap_id}
            className="p-3"
            style={{ background: colors.panelAlt, borderLeft: `3px solid ${colors[a.status]}` }}
          >
            <div className="flex items-center justify-between mb-1">
              <span style={{ color: colors.textPrimary, fontSize: 13, fontWeight: 600, fontFamily: "ui-monospace, monospace" }}>{a.ap_id}</span>
              <span style={{ color: colors[a.status], fontSize: 11 }}>{a.status}</span>
            </div>
            <div className="flex items-center gap-2" style={{ color: colors.textSecondary, fontSize: 12 }}>
              <span>{a.building}</span>
              <ArrowRight size={11} />
              <span>{a.recommendation.replace("Redirect new connections to ", "")}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
