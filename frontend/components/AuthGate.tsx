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
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const inputStyle: React.CSSProperties = {
    padding: 10, borderRadius: 6,
    border: isLight ? "1px solid #ff440055" : "1px solid #ff440055",
    background: isLight ? "#fff5f0" : "#0d0000",
    color: isLight ? "#1a0500" : "#fff",
    fontFamily: "monospace",
  };

  return (
    <div style={{
      display: "flex", alignItems: "center", justifyContent: "center",
      minHeight: "100vh",
      background: isLight ? "#fff5f0" : "#0a0000",
      color: isLight ? "#1a0500" : "#fff",
      position: "relative",
    }}>
      {/* Theme toggle — coin supérieur droit */}
      <button
        onClick={toggleTheme}
        aria-label={isLight ? "Passer en mode sombre" : "Passer en mode clair"}
        title={isLight ? "Mode sombre" : "Mode clair"}
        style={{
          position: "absolute", top: 20, right: 20,
          background: isLight ? "#ffe5d9" : "#1a0500",
          border: "1px solid #ff440044",
          borderRadius: 8, padding: "6px 10px",
          cursor: "pointer", fontSize: 18, lineHeight: 1,
        }}
      >
        {isLight ? "🌙" : "☀️"}
      </button>

      <form onSubmit={handleSubmit} style={{
        background: isLight ? "#fff" : "#1a0500",
        border: isLight ? "1px solid #ff440033" : "1px solid #ff440033",
        borderRadius: 12, padding: 32, width: 320, display: "flex",
        flexDirection: "column", gap: 16,
        boxShadow: isLight ? "0 4px 24px #ff440011" : "0 4px 24px #00000088",
      }}>
        <h1 style={{ color: "#ff6600", fontFamily: "monospace", textAlign: "center" }}>
          ORBI7RACK
        </h1>

        <div style={{ display: "flex", gap: 8 }}>
          {(["login", "register"] as const).map(m => (
            <button key={m} type="button" onClick={() => setMode(m)} style={{
              flex: 1, padding: "6px 0", borderRadius: 6, border: "1px solid #ff4400",
              background: mode === m ? "#ff4400" : "transparent",
              color: mode === m ? "#fff" : isLight ? "#1a0500" : "#fff",
              cursor: "pointer", fontFamily: "monospace",
            }}>
              {m === "login" ? "Connexion" : "Inscription"}
            </button>
          ))}
        </div>

        <input
          placeholder="Nom d'utilisateur" value={username}
          onChange={e => setUsername(e.target.value)}
          style={inputStyle}
        />

        {mode === "register" && (
          <input
            type="email" placeholder="Email (optionnel)" value={email}
            onChange={e => setEmail(e.target.value)}
            style={inputStyle}
          />
        )}

        <input
          type="password" placeholder="Mot de passe" value={password}
          onChange={e => setPassword(e.target.value)}
          style={inputStyle}
        />

        {error && <p style={{ color: "#ff4444", fontSize: 13, margin: 0 }}>{error}</p>}

        <button type="submit" disabled={loading} style={{
          padding: 10, borderRadius: 6, border: "none",
          background: "#ff4400", color: "#fff", cursor: "pointer",
          fontFamily: "monospace", fontWeight: "bold",
        }}>
          {loading ? "..." : mode === "login" ? "Se connecter" : "Créer le compte"}
        </button>
      </form>
    </div>
  );
}
