"use client";

import dynamic from "next/dynamic";

const Globe = dynamic(() => import("@/components/Globe"), { ssr: false });

export default function Home() {
  return (
    <main style={{ margin: 0, padding: 0, background: "#050d1a" }}>
      <Globe />
    </main>
  );
}