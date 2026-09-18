import { colors } from "../theme.js";

export default function CustomTooltip({ active, payload, label }) {
  if (!active || !payload || !payload.length) return null;
  return (
    <div style={{ background: colors.bg, border: `1px solid ${colors.borderStrong}`, padding: "8px 12px" }}>
      <div style={{ color: colors.textSecondary, fontSize: 11, marginBottom: 2 }}>{label}</div>
      {payload.map((p, i) => (
        <div key={i} style={{ color: colors.textPrimary, fontSize: 12, fontFamily: "ui-monospace, monospace" }}>
          {p.name} {p.value}%
        </div>
      ))}
    </div>
  );
}
