
import { Wifi, Users, MapPin, Activity } from "lucide-react";
import { colors } from "../theme.js";

export default function APDetailsPanel({ ap, devices }) {
  if (!ap) return null;

  const statusColor = colors[ap.status] || colors.textSecondary;
  const utilization = Number(ap.utilization_pct) || 0;

  return (
    <section
      className="p-4 mb-4"
      style={{
        background: colors.panel,
        border: `1px solid ${colors.border}`,
      }}
    >
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Activity size={16} color={colors.accent} />
          <h2
            style={{
              color: colors.textPrimary,
              fontSize: 15,
              fontWeight: 700,
              margin: 0,
            }}
          >
            Access Point Details
          </h2>
        </div>

        <span
          className="flex items-center gap-2 px-2 py-1"
          style={{
            background: colors.panelAlt,
            color: statusColor,
            fontSize: 11,
            fontWeight: 600,
          }}
        >
          <span
            style={{
              width: 7,
              height: 7,
              background: statusColor,
              borderRadius: "50%",
            }}
          />
          {ap.status}
        </span>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5">
        <div className="p-3" style={{ background: colors.panelAlt }}>
          <div className="flex items-center gap-2 mb-2">
            <Wifi size={14} color={colors.accent} />
            <span style={{ color: colors.textSecondary, fontSize: 11 }}>
              Access Point
            </span>
          </div>
          <div style={{ color: colors.textPrimary, fontSize: 18, fontWeight: 700 }}>
            {ap.ap_id}
          </div>
        </div>

        <div className="p-3" style={{ background: colors.panelAlt }}>
          <div className="flex items-center gap-2 mb-2">
            <MapPin size={14} color={colors.accent} />
            <span style={{ color: colors.textSecondary, fontSize: 11 }}>
              Building
            </span>
          </div>
          <div style={{ color: colors.textPrimary, fontSize: 14, fontWeight: 600 }}>
            {ap.building.replaceAll("_", " ")}
          </div>
        </div>

        <div className="p-3" style={{ background: colors.panelAlt }}>
          <div className="flex items-center gap-2 mb-2">
            <Users size={14} color={colors.accent} />
            <span style={{ color: colors.textSecondary, fontSize: 11 }}>
              Connected Devices
            </span>
          </div>
          <div style={{ color: colors.textPrimary, fontSize: 18, fontWeight: 700 }}>
            {ap.connected_count} / {ap.capacity}
          </div>
        </div>

        <div className="p-3" style={{ background: colors.panelAlt }}>
          <div className="flex items-center gap-2 mb-2">
            <Activity size={14} color={statusColor} />
            <span style={{ color: colors.textSecondary, fontSize: 11 }}>
              Utilization
            </span>
          </div>
          <div style={{ color: statusColor, fontSize: 18, fontWeight: 700 }}>
            {utilization}%
          </div>
          <div
            style={{
              height: 4,
              background: colors.border,
              marginTop: 8,
            }}
          >
            <div
              style={{
                width: `${Math.min(utilization, 100)}%`,
                height: "100%",
                background: statusColor,
              }}
            />
          </div>
        </div>
      </div>

      <div>
        <div
          className="mb-3"
          style={{
            color: colors.textPrimary,
            fontSize: 13,
            fontWeight: 700,
          }}
        >
          Devices connected to {ap.ap_id} ({devices.length})
        </div>

        {devices.length === 0 ? (
          <p style={{ color: colors.textFaint, fontSize: 12 }}>
            No connected devices are currently listed for this access point.
          </p>
        ) : (
          <div className="flex flex-col gap-2">
            {devices.map((device) => (
              <div
                key={device.device_id}
                className="flex items-center justify-between p-3"
                style={{
                  background: colors.panelAlt,
                  borderLeft: `3px solid ${colors.Normal}`,
                }}
              >
                <div>
                  <div
                    style={{
                      color: colors.textPrimary,
                      fontSize: 12,
                      fontWeight: 600,
                    }}
                  >
                    {device.nickname}
                  </div>
                  <div
                    style={{
                      color: colors.textFaint,
                      fontSize: 10,
                      marginTop: 3,
                    }}
                  >
                    Device ID: {device.device_id}
                  </div>
                </div>

                <span
                  style={{
                    color: colors.Normal,
                    fontSize: 11,
                    fontWeight: 600,
                  }}
                >
                  Connected
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
