"use client";

import { createContext, useContext, useEffect, useState, ReactNode } from "react";

export type Theme = "dark" | "light";

interface ThemeContextType {
  theme: Theme;
  toggleTheme: () => void;
}

const ThemeContext = createContext<ThemeContextType | null>(null);

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<Theme>("dark");

  useEffect(() => {
    const stored = localStorage.getItem("orbi_theme") as Theme | null;
    const initial = (stored === "light" || stored === "dark") ? stored : "dark";
    setTheme(initial);
    // Applique data-theme sur <html> — pas de div wrapper qui cause
    // un hydration mismatch SSR/client sur Safari iOS
    document.documentElement.setAttribute("data-theme", initial);
  }, []);

  const toggleTheme = () => {
    setTheme(prev => {
      const next = prev === "dark" ? "light" : "dark";
      localStorage.setItem("orbi_theme", next);
      document.documentElement.setAttribute("data-theme", next);
      return next;
    });
  };

  // Pas de div wrapper — on rend les children directement
  // pour eviter tout mismatch SSR/client
  return (
    <ThemeContext.Provider value={{ theme, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error("useTheme must be used within ThemeProvider");
  return ctx;
}
