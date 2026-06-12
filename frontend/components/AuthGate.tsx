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
  const assetBase = isLight ? "/assets/light" : "/assets/dark";

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setError("");
    setLoading(true);
    try {
      if (mode === "login") await login(username, password);
      else await register(username, email, password);
    } catch (err: any) {
      setError(err.message ?? "Erreur inconnue");
    } finally {
      setLoading(false);
    }
  };

  const inputStyle: React.CSSProperties = {
    padding: 12, borderRadius: 6,
    border: isLight ? "1px solid #4db8ff" : "1px solid #ff440055",
    background: isLight ? "#fff5f0" : "#0d0000",
    color: isLight ? "#1a0500" : "#fff",
    fontFamily: "monospace", fontSize: 16,
    width: "100%", minHeight: 44,
    boxSizing: "border-box" as const,
  };

  const btnBase: React.CSSProperties = {
    cursor: "pointer",
    WebkitTapHighlightColor: "rgba(255,255,255,0.15)",
    minHeight: 44, borderRadius: 6,
    fontFamily: "monospace",
    touchAction: "manipulation",
  };

  return (
    <div style={{
      position: "fixed", inset: 0, zIndex: 9999,
      display: "flex", flexDirection: "column",
      alignItems: "center", justifyContent: "center",
      background: isLight ? "#fff5f0" : "#0a0000",
      color: isLight ? "#1a0500" : "#fff",
      padding: "0 16px", gap: 24,
    }}>
      {/* Theme toggle */}
      <button type="button"
        onClick={toggleTheme}
        aria-label={isLight ? "Passer en mode sombre" : "Passer en mode clair"}
        style={{
          ...btnBase, position: "absolute", top: 16, right: 16,
          background: isLight ? "#ffe5d9" : "#1a0500",
          border: `1px solid ${isLight ? "#4db8ff" : "#ff4800"}`,
          minWidth: 44, padding: "6px 10px", fontSize: 18,
        }}
      >{isLight ? "🌙" : "☀️"}</button>

      {/*
        Logo vidéo
        - <source> avec type explicite : le navigateur choisit le premier format supporté
        - webm en premier (Chromium/Firefox/Android)
        - mp4 en fallback (Safari iOS/macOS — ne supporte pas webm)
        - muted + playsInline OBLIGATOIRES pour l'autoplay iOS
        - key={assetBase} force le rechargement quand le thème change
      */}
      <video
        key={assetBase}
        autoPlay
        loop
        muted
        playsInline
        preload="metadata"
        poster={`${assetBase}/login-poster.jpg`}
        style={{ width: "min(640px, 160vw)", height: "auto", display: "block" }}
      >
        <source src={`${assetBase}/orbi7rack-video.mp4`} type="video/mp4" />
        <source src={`${assetBase}/orbi7rack-video.webm`} type="video/webm" />
      </video>

      {/* Formulaire */}
      <form onSubmit={handleSubmit} action="javascript:void(0)" noValidate
        className="auth-form"
        style={{
          background: isLight ? "#fff" : "#1a0500",
          border: "1px solid #ff440033",
        }}
      >
        <div style={{ display: "flex", gap: 8 }}>
          {(["login", "register"] as const).map(m => (
            <button key={m} type="button"
              onPointerUp={() => setMode(m)}
              style={{
                ...btnBase, flex: 1, padding: "10px 0",
                border: `1px solid ${isLight ? "#4db8ff" : "#ff4800"}`,
                background: mode === m ? (isLight ? "#4db8ff" : "#ff4800") : "transparent",
                color: mode === m ? "#fff" : isLight ? "#1a0500" : "#fff",
                fontSize: 13,
              }}
            >{m === "login" ? "Connexion" : "Inscription"}</button>
          ))}
        </div>

        <input placeholder="Nom d'utilisateur" value={username}
          onChange={e => setUsername(e.target.value)}
          style={inputStyle} autoComplete="username"
          autoCapitalize="none" autoCorrect="off"
        />
        {mode === "register" && (
          <input type="email" placeholder="Email (optionnel)" value={email}
            onChange={e => setEmail(e.target.value)}
            style={inputStyle} autoComplete="email"
          />
        )}
        <input type="password" placeholder="Mot de passe" value={password}
          onChange={e => setPassword(e.target.value)}
          style={inputStyle} autoComplete="current-password"
        />

        {error && (
          <p style={{ color: "#ff4444", fontSize: 13, margin: 0, fontFamily: "monospace" }}>
            {error}
          </p>
        )}

        <button type="submit" disabled={loading}
          style={{
            ...btnBase, padding: 12, width: "100%",
            border: "none",
            background: isLight ? "#4db8ff" : "#ff4800",
            color: "#fff", fontWeight: "bold", fontSize: 14,
            opacity: loading ? 0.7 : 1,
          }}
        >{loading ? "..." : mode === "login" ? "Se connecter" : "Créer le compte"}</button>
      </form>
    </div>
  );
}
