"use client";

import { useState } from "react";
import { useAuth } from "@/context/AuthContext";

export default function AuthGate({ children }: { children: React.ReactNode }) {
  const { access, login, register } = useAuth();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  if (access) return <>{children}</>;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      if (mode === "login") await login(email, password);
      else await register(username, email, password);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const inputStyle = {
    padding: 10, borderRadius: 6, border: "1px solid #ff440055",
    background: "#0d0000", color: "#fff", fontFamily: "monospace",
  };

  return (
    <div style={{
      display: "flex", alignItems: "center", justifyContent: "center",
      minHeight: "100vh", background: "#0a0000", color: "#fff",
    }}>
      <form onSubmit={handleSubmit} style={{
        background: "#1a0500", border: "1px solid #ff440033",
        borderRadius: 12, padding: 32, width: 320, display: "flex",
        flexDirection: "column", gap: 16,
      }}>
        <h1 style={{ color: "#ff6600", fontFamily: "monospace", textAlign: "center" }}>
          ORBI7RACK
        </h1>

        <div style={{ display: "flex", gap: 8 }}>
          {(["login", "register"] as const).map(m => (
            <button key={m} type="button" onClick={() => setMode(m)} style={{
              flex: 1, padding: "6px 0", borderRadius: 6, border: "1px solid #ff4400",
              background: mode === m ? "#ff4400" : "transparent",
              color: "#fff", cursor: "pointer", fontFamily: "monospace",
            }}>
              {m === "login" ? "Connexion" : "Inscription"}
            </button>
          ))}
        </div>

        {/* Champ username uniquement en inscription */}
        {mode === "register" && (
          <input
            placeholder="Nom d'utilisateur" value={username}
            onChange={e => setUsername(e.target.value)}
            style={inputStyle}
          />
        )}

        {/* Email toujours visible (login + inscription) */}
        <input
          type="email" placeholder="Email" value={email}
          onChange={e => setEmail(e.target.value)}
          style={inputStyle}
        />

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
