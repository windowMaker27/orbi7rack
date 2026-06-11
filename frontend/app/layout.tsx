import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

import { AuthProvider } from "@/context/AuthContext";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Orbi7rack",
  description: "Parcel tracker",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr" suppressHydrationWarning>
      <head>
        {/*
          Viewport mobile — NE PAS mettre maximum-scale=1 ni user-scalable=no :
          - maximum-scale=1 bloque certains touch events sur iOS Safari
          - user-scalable=no est interdit par les directives d'accessibilité WCAG
          initial-scale=1 suffit pour empêcher le zoom auto sur les inputs
          (on force font-size:16px sur les inputs à la place)
        */}
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </head>
      <body suppressHydrationWarning>
        <AuthProvider>
          {children}
        </AuthProvider>
      </body>
    </html>
  );
}
