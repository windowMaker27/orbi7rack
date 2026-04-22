"use client";

import { useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { useTheme } from "@/context/ThemeContext";

export default function TopBar() {
  const { username, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const [open, setOpen] = useState(false);

  const isDark = theme === "dark";
  const initials = (username ?? "?").slice(0, 2).toUpperCase();

  const colors = {
    bg:      isDark ? "rgba(10,0,0,0.75)"         : "rgba(240,237,232,0.85)",
    border:  isDark ? "rgba(255,68,0,0.2)"         : "rgba(0,102,204,0.2)",
    accent:  isDark ? "#ff6600"                    : "#0066cc",
    accentBg:isDark ? "rgba(255,68,0,0.12)"        : "rgba(0,102,204,0.1)",
    text:    isDark ? "#ffffff"                    : "#1a1a2e",
    muted:   isDark ? "#ffffff66"                  : "#1a1a2e99",
    divider: isDark ? "rgba(255,68,0,0.15)"        : "rgba(0,102,204,0.15)",
    danger:  isDark ? "#ff4444"                    : "#cc2200",
    dangerBg:isDark ? "rgba(255,68,0,0.1)"         : "rgba(204,34,0,0.08)",
  };

  return (
    <div style={{
      position: "fixed", top: 16, right: 16,
      zIndex: 300,
      display: "flex", alignItems: "center", gap: 8,
      pointerEvents: "auto",
    }}>
      {/* Toggle dark/light */}
      <button
        onClick={toggleTheme}
        title={isDark ? "Mode clair" : "Mode sombre"}
        style={{
          background: colors.bg,
          backdropFilter: "blur(16px)",
          WebkitBackdropFilter: "blur(16px)",
          border: `1px solid ${colors.border}`,
          borderRadius: 8,
          color: colors.accent,
          cursor: "pointer",
          width: 36, height: 36,
          display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: 16, transition: "all 0.2s",
        }}
      >
        {isDark ? "☀️" : "🌙"}
      </button>

      {/* Avatar */}
      <div style={{ position: "relative" }}>
        <button
          onClick={() => setOpen(o => !o)}
          style={{
            background: colors.accentBg,
            backdropFilter: "blur(16px)",
            WebkitBackdropFilter: "blur(16px)",
            border: `1px solid ${colors.border}`,
            borderRadius: 8,
            color: colors.accent,
            cursor: "pointer",
            width: 36, height: 36,
            display: "flex", alignItems: "center", justifyContent: "center",
            fontFamily: "monospace", fontSize: 13, fontWeight: "bold",
            letterSpacing: 1,
            transition: "all 0.2s",
          }}
        >
          {initials}
        </button>

        {/* Dropdown */}
        {open && (
          <div
            style={{
              position: "absolute", top: 44, right: 0,
              background: colors.bg,
              backdropFilter: "blur(20px)",
              WebkitBackdropFilter: "blur(20px)",
              border: `1px solid ${colors.border}`,
              borderRadius: 10,
              minWidth: 180,
              overflow: "hidden",
              boxShadow: isDark
                ? "0 8px 32px rgba(0,0,0,0.6)"
                : "0 8px 32px rgba(0,0,0,0.12)",
            }}
          >
            {/* Username */}
            <div style={{
              padding: "12px 16px",
              borderBottom: `1px solid ${colors.divider}`,
            }}>
              <div style={{ color: colors.muted, fontFamily: "monospace", fontSize: 9, letterSpacing: 2, marginBottom: 4 }}>
                CONNECTÉ EN TANT QUE
              </div>
              <div style={{ color: colors.accent, fontFamily: "monospace", fontSize: 13, fontWeight: "bold" }}>
                {username ?? "—"}
              </div>
            </div>

            {/* Déconnexion */}
            <button
              onClick={() => { setOpen(false); logout(); }}
              style={{
                width: "100%",
                background: "transparent",
                border: "none",
                color: colors.danger,
                fontFamily: "monospace",
                fontSize: 12,
                padding: "12px 16px",
                textAlign: "left",
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                gap: 8,
                transition: "background 0.15s",
              }}
              onMouseEnter={e => (e.currentTarget.style.background = colors.dangerBg)}
              onMouseLeave={e => (e.currentTarget.style.background = "transparent")}
            >
              <span>⏻</span> Déconnexion
            </button>
          </div>
        )}
      </div>

      {/* Fermer dropdown au clic extérieur */}
      {open && (
        <div
          onClick={() => setOpen(false)}
          style={{ position: "fixed", inset: 0, zIndex: -1 }}
        />
      )}
    </div>
  );
}
