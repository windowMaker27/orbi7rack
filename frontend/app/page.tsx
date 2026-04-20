"use client";

import dynamic from "next/dynamic";
import AuthGate from "@/components/AuthGate";

const Globe = dynamic(() => import("@/components/Globe"), { ssr: false });

export default function Home() {
  return (
    <AuthGate>
      <main style={{ margin: 0, padding: 0, background: "#0a0000" }}>
        <Globe />
      </main>
    </AuthGate>
  );
}