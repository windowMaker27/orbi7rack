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
    bg:       isDark ? "rgba(10,0,0,0.75)"    : "rgba(240,237,232,0.85)",
    border:   isDark ? "rgba(255,68,0,0.2)"   : "rgba(0,102,204,0.2)",
    accent:   isDark ? "#ff6600"              : "#0066cc",
    accentBg: isDark ? "rgba(255,68,0,0.12)" : "rgba(0,102,204,0.1)",
    text:     isDark ? "#ffffff"              : "#1a1a2e",
    muted:    isDark ? "#ffffff66"            : "#1a1a2e99",
    divider:  isDark ? "rgba(255,68,0,0.15)" : "rgba(0,102,204,0.15)",
    danger:   isDark ? "#ff4444"             : "#cc2200",
    dangerBg: isDark ? "rgba(255,68,0,0.1)"  : "rgba(204,34,0,0.08)",
    // switch-specific
    switchBorder:  isDark ? "rgba(255,102,0,0.55)" : "rgba(0,102,204,0.45)",
    switchTrack:   isDark ? "rgba(255,68,0,0.08)"  : "rgba(0,102,204,0.07)",
    switchThumb:   isDark ? "#ff6600"              : "#0066cc",
    switchIcon:    isDark ? "#ff6600"              : "#0066cc",
  };

  // Sun SVG (light mode thumb)
  const SunIcon = () => (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none"
      stroke="#0066cc" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="5"/>
      <line x1="12" y1="1" x2="12" y2="3"/>
      <line x1="12" y1="21" x2="12" y2="23"/>
      <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/>
      <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>
      <line x1="1" y1="12" x2="3" y2="12"/>
      <line x1="21" y1="12" x2="23" y2="12"/>
      <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/>
      <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
    </svg>
  );

  // Moon SVG (dark mode thumb)
  const MoonIcon = () => (
    <svg width="11" height="11" viewBox="0 0 24 24" fill="none"
      stroke="#ff6600" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
    </svg>
  );

  return (
    <div style={{
      position: "fixed", top: 16, right: 16,
      zIndex: 300,
      display: "flex", alignItems: "center", gap: 8,
      pointerEvents: "auto",
    }}>

      {/* ── Theme switch ── */}
      <button
        role="switch"
        aria-checked={isDark}
        aria-label={isDark ? "Passer en mode clair" : "Passer en mode sombre"}
        onClick={toggleTheme}
        style={{
          // pill track
          position: "relative",
          width: 54,
          height: 28,
          borderRadius: 999,
          border: `1.5px solid ${colors.switchBorder}`,
          background: colors.switchTrack,
          backdropFilter: "blur(16px)",
          WebkitBackdropFilter: "blur(16px)",
          cursor: "pointer",
          padding: 0,
          outline: "none",
          transition: "border-color 0.2s, background 0.2s",
          flexShrink: 0,
        }}
      >
        {/* thumb */}
        <span style={{
          position: "absolute",
          top: 3,
          left: isDark ? 26 : 3,
          width: 20,
          height: 20,
          borderRadius: "50%",
          background: colors.switchThumb,
          boxShadow: isDark
            ? "0 0 6px rgba(255,102,0,0.5)"
            : "0 0 6px rgba(0,102,204,0.35)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          transition: "left 0.2s cubic-bezier(0.4,0,0.2,1), background 0.2s",
          pointerEvents: "none",
        }}>
          {isDark ? <MoonIcon /> : <SunIcon />}
        </span>
      </button>

      {/* ── Avatar ── */}
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
          <div style={{
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
          }}>
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
