"use client";

import dynamic from "next/dynamic";
import AuthGate from "@/components/AuthGate";
import { useParcels } from "@/hooks/useParcels";

const Globe = dynamic(() => import("@/components/Globe"), { ssr: false });

function GlobeWithData() {
  const { parcels } = useParcels();
  return <Globe parcels={parcels} />;
}

export default function Home() {
  return (
    <AuthGate>
      <main style={{ margin: 0, padding: 0, background: "#0a0000" }}>
        <GlobeWithData />
      </main>
    </AuthGate>
  );
}
