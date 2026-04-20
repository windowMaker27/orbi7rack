"use client";

import { createContext, useContext, useState, useCallback, ReactNode } from "react";

interface AuthState {
  access: string | null;
  username: string | null;
}

interface AuthContextType extends AuthState {
  login: (username: string, password: string) => Promise<void>;
  register: (username: string, email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [auth, setAuth] = useState<AuthState>({ access: null, username: null });

  const login = useCallback(async (email: string, password: string) => {
    const res = await fetch(`${API}/api/auth/token/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }), // ← email au lieu de username
    });
    if (!res.ok) throw new Error("Identifiants incorrects");
    const data = await res.json();
    setAuth({ access: data.access, username: email });
}, []);

  const register = useCallback(async (username: string, email: string, password: string) => {
    const res = await fetch(`${API}/api/auth/register/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, email, password }),
    });
    if (!res.ok) throw new Error("Erreur lors de l'inscription");
    await login(email, password); // ← login par EMAIL
}, [login]);

  const logout = useCallback(() => {
    setAuth({ access: null, username: null });
  }, []);

  return (
    <AuthContext.Provider value={{ ...auth, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}