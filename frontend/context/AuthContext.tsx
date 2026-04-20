"use client";

import { createContext, useContext, useState, useCallback, useEffect, ReactNode } from "react";

interface AuthState {
  access: string | null;
  refresh: string | null;
  username: string | null;
}

interface AuthContextType extends AuthState {
  login: (username: string, password: string) => Promise<void>;
  register: (username: string, email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const STORAGE_KEYS = {
  access: "orbi_access",
  refresh: "orbi_refresh",
  username: "orbi_username",
};

export function AuthProvider({ children }: { children: ReactNode }) {
  const [auth, setAuth] = useState<AuthState>({
    access: null,
    refresh: null,
    username: null,
  });

  // Hydrate depuis localStorage au montage
  useEffect(() => {
    const access = localStorage.getItem(STORAGE_KEYS.access);
    const refresh = localStorage.getItem(STORAGE_KEYS.refresh);
    const username = localStorage.getItem(STORAGE_KEYS.username);
    if (access) setAuth({ access, refresh, username });
  }, []);

  const persist = (access: string, refresh: string, username: string) => {
    localStorage.setItem(STORAGE_KEYS.access, access);
    localStorage.setItem(STORAGE_KEYS.refresh, refresh);
    localStorage.setItem(STORAGE_KEYS.username, username);
    setAuth({ access, refresh, username });
  };

  const login = useCallback(async (username: string, password: string) => {
    const res = await fetch(`${API}/api/auth/token/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    if (!res.ok) throw new Error("Identifiants incorrects");
    const data = await res.json();
    persist(data.access, data.refresh ?? "", username);
  }, []);

  const register = useCallback(async (username: string, email: string, password: string) => {
    const res = await fetch(`${API}/api/auth/register/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, email, password }),
    });
    if (!res.ok) throw new Error("Erreur lors de l'inscription");
    await login(username, password);
  }, [login]);

  const logout = useCallback(() => {
    localStorage.removeItem(STORAGE_KEYS.access);
    localStorage.removeItem(STORAGE_KEYS.refresh);
    localStorage.removeItem(STORAGE_KEYS.username);
    setAuth({ access: null, refresh: null, username: null });
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
