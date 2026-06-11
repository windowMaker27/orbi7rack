"use client";

import { useState } from "react";
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

  const isLight = theme === "light";

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      if (mode === "login") await login(username, password);
      else await register(username, email, password);
    } catch (err: any) {
      setError(err.message ?? "Erreur réseau — vérifiez votre connexion");
    } finally {
      setLoading(false);
    }
  };

  /* font-size 16px sur tous les inputs : empêche le zoom auto Safari iOS */
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

  return (
    <div style={{
      display: "flex", alignItems: "center", justifyContent: "center",
      minHeight: "100dvh",      /* dvh = dynamic viewport height, correct sur iOS */
      background: isLight ? "#fff5f0" : "#0a0000",
      color: isLight ? "#1a0500" : "#fff",
      position: "relative",
      padding: "0 16px",
    }}>
      {/* Theme toggle */}
      <button
        onClick={toggleTheme}
        aria-label={isLight ? "Passer en mode sombre" : "Passer en mode clair"}
        style={{
          position: "absolute", top: 16, right: 16,
          background: isLight ? "#ffe5d9" : "#1a0500",
          border: `1px solid ${isLight ? "#4db8ff" : "#ff4800"}`,
          borderRadius: 8,
          /* touch target 44px */
          minWidth: 44, minHeight: 44,
          padding: "6px 10px",
          cursor: "pointer", fontSize: 18, lineHeight: 1,
          display: "flex", alignItems: "center", justifyContent: "center",
        }}
      >
        {isLight ? "🌙" : "☀️"}
      </button>

      {/* Classe .auth-form : width responsive via globals.css */}
      <form onSubmit={handleSubmit} className="auth-form" style={{
        background: isLight ? "#fff" : "#1a0500",
        border: "1px solid #ff440033",
        boxShadow: isLight ? "0 4px 24px #ff440011" : "0 4px 24px #00000088",
      }}>
        <h1 style={{ color: "#ff4800", fontFamily: "monospace", textAlign: "center", fontSize: 20, margin: 0 }}>
          ORBI7RACK
        </h1>

        <div style={{ display: "flex", gap: 8 }}>
          {(["login", "register"] as const).map(m => (
            <button key={m} type="button" onClick={() => setMode(m)} style={{
              flex: 1,
              padding: "10px 0",
              minHeight: 44,
              borderRadius: 6,
              border: `1px solid ${isLight ? "#4db8ff" : "#ff4800"}`,
              background: mode === m ? `${isLight ? "#4db8ff" : "#ff4800"}` : "transparent",
              color: mode === m ? "#fff" : isLight ? "#1a0500" : "#fff",
              cursor: "pointer", fontFamily: "monospace",
              fontSize: 13,
            }}>
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
            padding: 12,
            minHeight: 44,
            borderRadius: 6,
            border: "none",
            background: isLight ? "#4db8ff" : "#ff4800",
            color: "#fff",
            cursor: loading ? "not-allowed" : "pointer",
            fontFamily: "monospace",
            fontWeight: "bold",
            fontSize: 14,
            opacity: loading ? 0.7 : 1,
          }}
        >
          {loading ? "..." : mode === "login" ? "Se connecter" : "Créer le compte"}
        </button>
      </form>
    </div>
  );
}
