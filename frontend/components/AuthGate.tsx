"use client";

import { useState, useRef } from "react";
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
  const [logs, setLogs] = useState<string[]>([]);
  const logRef = useRef<HTMLDivElement>(null);

  const log = (msg: string) => {
    const ts = new Date().toISOString().slice(11, 23);
    setLogs(prev => [`[${ts}] ${msg}`, ...prev].slice(0, 20));
  };

  if (access) return <>{children}</>;

  const isLight = theme === "light";

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    e.stopPropagation();
    log(`handleSubmit appele — mode=${mode} user=${username}`);
    setError("");
    setLoading(true);
    try {
      log("fetch en cours...");
      if (mode === "login") await login(username, password);
      else await register(username, email, password);
      log("succes !");
    } catch (err: any) {
      const msg = err.message ?? "Erreur inconnue";
      log(`ERREUR: ${msg}`);
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const inputStyle: React.CSSProperties = {
    padding: 12,
    borderRadius: 6,
    border: isLight ? "1px solid #4db8ff" : "1px solid #ff440055",
    background: isLight ? "#fff5f0" : "#0d0000",
    color: isLight ? "#1a0500" : "#fff",
    fontFamily: "monospace",
    fontSize: 16,
    width: "100%",
    minHeight: 44,
    boxSizing: "border-box" as const,
  };

  const btnBase: React.CSSProperties = {
    cursor: "pointer",
    WebkitTapHighlightColor: "rgba(255,255,255,0.15)",
    minHeight: 44,
    borderRadius: 6,
    fontFamily: "monospace",
    touchAction: "manipulation",
  };

  return (
    <div style={{
      position: "fixed",
      inset: 0,
      zIndex: 9999,
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      justifyContent: "center",
      background: isLight ? "#fff5f0" : "#0a0000",
      color: isLight ? "#1a0500" : "#fff",
      padding: "0 16px",
      gap: 16,
    }}>
      {/* Theme toggle */}
      <button
        type="button"
        onClick={() => { log("toggleTheme tap"); toggleTheme(); }}
        aria-label={isLight ? "Passer en mode sombre" : "Passer en mode clair"}
        style={{
          ...btnBase,
          position: "absolute", top: 16, right: 16,
          background: isLight ? "#ffe5d9" : "#1a0500",
          border: `1px solid ${isLight ? "#4db8ff" : "#ff4800"}`,
          minWidth: 44,
          padding: "6px 10px",
          fontSize: 18, lineHeight: 1,
          display: "flex", alignItems: "center", justifyContent: "center",
        }}
      >
        {isLight ? "🌙" : "☀️"}
      </button>

      <form
        onSubmit={handleSubmit}
        action="javascript:void(0)"
        noValidate
        className="auth-form"
        style={{
          background: isLight ? "#fff" : "#1a0500",
          border: "1px solid #ff440033",
          boxShadow: isLight ? "0 4px 24px #ff440011" : "0 4px 24px #00000088",
        }}
      >
        <h1 style={{ color: "#ff4800", fontFamily: "monospace", textAlign: "center", fontSize: 20, margin: 0 }}>
          ORBI7RACK
        </h1>

        <div style={{ display: "flex", gap: 8 }}>
          {(["login", "register"] as const).map(m => (
            <button
              key={m}
              type="button"
              onPointerUp={() => { log(`tab ${m} pointerUp`); setMode(m); }}
              style={{
                ...btnBase,
                flex: 1,
                padding: "10px 0",
                border: `1px solid ${isLight ? "#4db8ff" : "#ff4800"}`,
                background: mode === m ? `${isLight ? "#4db8ff" : "#ff4800"}` : "transparent",
                color: mode === m ? "#fff" : isLight ? "#1a0500" : "#fff",
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
          onFocus={() => log("focus: username")}
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
          onFocus={() => log("focus: password")}
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
          onPointerDown={() => log("submit pointerDown")}
          onPointerUp={() => log("submit pointerUp")}
          onClick={() => log("submit onClick")}
          style={{
            ...btnBase,
            padding: 12,
            width: "100%",
            border: "none",
            background: isLight ? "#4db8ff" : "#ff4800",
            color: "#fff",
            fontWeight: "bold",
            fontSize: 14,
            opacity: loading ? 0.7 : 1,
          }}
        >
          {loading ? "..." : mode === "login" ? "Se connecter" : "Créer le compte"}
        </button>
      </form>

      {/* Logger visuel — DEBUG MOBILE — retirer après diagnostic */}
      <div ref={logRef} style={{
        width: "calc(100vw - 32px)",
        maxWidth: 320,
        background: "#000",
        border: "1px solid #333",
        borderRadius: 8,
        padding: 10,
        fontFamily: "monospace",
        fontSize: 11,
        color: "#0f0",
        maxHeight: 160,
        overflowY: "auto",
        userSelect: "text",
      }}>
        {logs.length === 0
          ? <span style={{ color: "#555" }}>En attente de taps...</span>
          : logs.map((l, i) => <div key={i}>{l}</div>)
        }
      </div>
    </div>
  );
}
