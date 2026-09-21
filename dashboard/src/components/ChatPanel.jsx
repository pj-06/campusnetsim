import { useEffect, useRef } from "react";
import { MessageCircle } from "lucide-react";
import { colors } from "../theme.js";

export default function ChatPanel({ messages }) {
  const listRef = useRef(null);

  useEffect(() => {
    if (listRef.current) listRef.current.scrollTop = listRef.current.scrollHeight;
  }, [messages]);

  return (
    <div className="p-4 h-full" style={{ background: colors.panel, border: `1px solid ${colors.border}` }}>
      <div className="flex items-center gap-2 mb-4">
        <MessageCircle size={14} color={colors.accent} strokeWidth={2.25} />
        <span style={{ color: colors.textPrimary, fontSize: 13, fontWeight: 600, fontFamily: "'Space Grotesk', sans-serif" }}>
          Campus chat
        </span>
      </div>
      {messages.length === 0 && (
        <p style={{ color: colors.textFaint, fontSize: 13 }}>
          No messages yet — send one from a checked-in phone to see it appear here live.
        </p>
      )}
      <div ref={listRef} className="flex flex-col gap-2" style={{ maxHeight: 220, overflowY: "auto" }}>
        {messages.map((m) => (
          <div key={m.id} className="p-2.5" style={{ background: colors.panelAlt }}>
            <div className="flex items-center gap-2 mb-0.5">
              <span style={{ color: colors.textPrimary, fontSize: 12.5, fontWeight: 600 }}>{m.nickname}</span>
              <span style={{ color: colors.textFaint, fontSize: 10.5, fontFamily: "ui-monospace, monospace" }}>
                {m.ap_id}
              </span>
              <span style={{ color: colors.textFaint, fontSize: 10.5, marginLeft: "auto" }}>{m.time}</span>
            </div>
            <div style={{ color: colors.textSecondary, fontSize: 12.5 }}>{m.message}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
