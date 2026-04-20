"use client";

import dynamic from "next/dynamic";
import { useState, useRef } from "react";
import AuthGate from "@/components/AuthGate";
import Sidebar from "@/components/Sidebar";
import ParcelDetailModal from "@/components/ParcelDetailModal";
import { useParcels } from "@/hooks/useParcels";
import type { Parcel } from "@/hooks/useParcels";

const Globe = dynamic(() => import("@/components/Globe"), { ssr: false });

function GlobeWithData() {
  const { parcels, loading, setParcels } = useParcels();
  const globeRef = useRef<any>(null);
  const [selectedParcel, setSelectedParcel] = useState<Parcel | null>(null);

  const handleSelectParcel = (parcel: Parcel) => {
    const pos = parcel.estimated_position;
    if (pos && globeRef.current) {
      globeRef.current.pointOfView(
        { lat: pos.lat, lng: pos.lng, altitude: 1.5 },
        800
      );
      // Pause rotation
      globeRef.current.controls().autoRotate = false;
    }
    setSelectedParcel(parcel);
  };

  const handleCloseModal = () => {
    setSelectedParcel(null);
    // Reprend la rotation
    if (globeRef.current) {
      globeRef.current.controls().autoRotate = true;
    }
  };

  const handleParcelAdded = (parcel: Parcel) => {
    setParcels(prev => [parcel, ...prev]);
    handleSelectParcel(parcel);
  };

  return (
    <>
      <Globe parcels={parcels} globeRef={globeRef} />
      <Sidebar
        parcels={parcels}
        loading={loading}
        onSelectParcel={handleSelectParcel}
        onParcelAdded={handleParcelAdded}
      />
      {selectedParcel && (
        <ParcelDetailModal
          parcel={selectedParcel}
          onClose={handleCloseModal}
        />
      )}
    </>
  );
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
