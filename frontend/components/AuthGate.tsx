"use client";

import { useState } from "react";
import Image from "next/image";
import { useAuth } from "@/context/AuthContext";
import { useTheme } from "@/context/ThemeContext";

export default function AuthGate({ children }: { children: React.ReactNode }) {
  const { access, login, register } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  if (access) return <>{children}</>;

  const isDark = theme === "dark";
  const assetBase = isDark ? "/assets/dark" : "/assets/light";

  const accent      = isDark ? "#d14d00"              : "#0066cc";
  const accentBg    = isDark ? "rgba(255,68,0,0.12)"  : "rgba(0,102,204,0.1)";
  const accentBorder= isDark ? "rgba(255,102,0,0.55)" : "rgba(0,102,204,0.45)";
  const bg          = isDark ? "#000000"              : "#ffffff";
  const text        = isDark ? "#ffffff"              : "#1a1a2e";
  const inputBg     = isDark ? "#0d0000"              : "#f5f5ff";
  const inputBorder = isDark ? "rgba(255,68,0,0.35)"  : "rgba(0,102,204,0.35)";
  const switchBorder= isDark ? "rgba(255,102,0,0.55)" : "rgba(0,102,204,0.45)";
  const switchTrack = isDark ? "rgba(255,68,0,0.08)"  : "rgba(0,102,204,0.07)";
  const switchThumb = isDark ? "#ff6600"              : "#0066cc";

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setError("");
    setLoading(true);
    try {
      if (mode === "login") await login(username, password);
      else await register(username, email, password);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Erreur inconnue");
    } finally {
      setLoading(false);
    }
  };

  const inputStyle: React.CSSProperties = {
    padding: 12,
    borderRadius: 6,
    border: `1px solid ${inputBorder}`,
    background: inputBg,
    color: text,
    fontFamily: "monospace",
    fontSize: 16,
    width: "100%",
    minHeight: 44,
    boxSizing: "border-box",
  };

  const btnBase: React.CSSProperties = {
    cursor: "pointer",
    WebkitTapHighlightColor: "rgba(255,255,255,0.15)",
    minHeight: 44,
    borderRadius: 6,
    fontFamily: "monospace",
    touchAction: "manipulation",
  };

  const SunIcon = () => (
    <svg width="10" height="10" viewBox="0 0 24 24" fill="none"
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

  const MoonIcon = () => (
    <svg width="9" height="9" viewBox="0 0 24 24" fill="none"
      stroke="#ff6600" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
    </svg>
  );

  return (
    <div style={{
      position: "fixed", inset: 0, zIndex: 9999,
      display: "flex", flexDirection: "column",
      alignItems: "center", justifyContent: "center",
      background: bg,
      color: text,
      padding: "0 16px", gap: 24,
    }}>

      {/* Theme switch */}
      <button
        type="button"
        role="switch"
        aria-checked={isDark}
        aria-label={isDark ? "Passer en mode clair" : "Passer en mode sombre"}
        onClick={toggleTheme}
        style={{
          position: "absolute", top: 16, right: 16,
          width: 44,
          height: 44, /* 44px touch target — était 30, trop petit pour iOS */
          borderRadius: 999,
          border: `1.5px solid ${switchBorder}`,
          background: switchTrack,
          backdropFilter: "blur(16px)",
          WebkitBackdropFilter: "blur(16px)",
          cursor: "pointer",
          padding: 0,
          outline: "none",
          transition: "border-color 0.2s, background 0.2s",
          display: "flex",
          alignItems: "center",
          flexShrink: 0,
          touchAction: "manipulation",
        }}
      >
        <span style={{
          position: "absolute",
          top: "50%",
          transform: "translateY(-50%)",
          left: isDark ? 22 : 4,
          width: 16, height: 16,
          borderRadius: "50%",
          background: switchThumb,
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

      {/* Logo vidéo — pointer-events:none : iOS Safari AVKit interceptait
          tous les touch events dans la zone vidéo avant React,
          bloquant les boutons Connexion/Inscription et le toggle */}
      <video
        key={assetBase}
        autoPlay
        loop
        muted
        playsInline
        preload="auto"
        poster={`${assetBase}/login-poster.jpg`}
        style={{
          width: "min(640px, 90vw)",
          height: "auto",
          display: "block",
          pointerEvents: "none",
        }}
      >
        <source src={`${assetBase}/orbi7rack-video.mp4`} type="video/mp4" />
        <source src={`${assetBase}/orbi7rack-video.webm`} type="video/webm" />
      </video>

      {/* Formulaire */}
      <form
        onSubmit={handleSubmit}
        action="javascript:void(0)"
        noValidate
        className="auth-form"
        style={{
          background: isDark ? "rgba(20,8,0,0.95)" : "rgba(255,255,255,0.95)",
          border: `1px solid ${accentBorder}`,
        }}
      >
        <img
          src={`${assetBase}/logo.png`}
          alt="Orbi7rack"
          style={{ width: 425, height: 64, marginBottom: 10 }}
        />
        <div style={{ display: "flex", gap: 8 }}>
          {(["login", "register"] as const).map(m => (
            <button
              key={m}
              type="button"
              onPointerUp={() => setMode(m)}
              style={{
                ...btnBase, flex: 1, padding: "10px 0",
                border: `1px solid ${accentBorder}`,
                background: mode === m ? accent : "transparent",
                color: mode === m ? "#fff" : text,
                fontSize: 13,
              }}
            >
              {m === "login" ? "Connexion" : "Inscription"}
            </button>
          ))}
        </div>

        <input
          placeholder="Nom d'utilisateur"
          value={username}
          onChange={e => setUsername(e.target.value)}
          style={inputStyle}
          autoComplete="username"
          autoCapitalize="none"
          autoCorrect="off"
        />
        {mode === "register" && (
          <input
            type="email"
            placeholder="Email (optionnel)"
            value={email}
            onChange={e => setEmail(e.target.value)}
            style={inputStyle}
            autoComplete="email"
          />
        )}
        <input
          type="password"
          placeholder="Mot de passe"
          value={password}
          onChange={e => setPassword(e.target.value)}
          style={inputStyle}
          autoComplete="current-password"
        />

        {error && (
          <p style={{ color: "#ff4444", fontSize: 13, margin: 0, fontFamily: "monospace" }}>
            {error}
          </p>
        )}

        <button
          type="submit"
          disabled={loading}
          style={{
            ...btnBase, padding: 12, width: "100%",
            border: "none",
            background: accent,
            color: "#fff", fontWeight: "bold", fontSize: 14,
            opacity: loading ? 0.7 : 1,
          }}
        >
          {loading ? "..." : mode === "login" ? "Se connecter" : "Créer le compte"}
        </button>
      </form>
    </div>
  );
}
