"use client";

import dynamic from "next/dynamic";
import { useState, useRef } from "react";
import AuthGate from "@/components/AuthGate";
import Sidebar from "@/components/Sidebar";
import ParcelDetailModal from "@/components/ParcelDetailModal";
import { useParcels } from "@/hooks/useParcels";
import { useFlightPositions } from "@/hooks/useFlightPositions";
import type { Parcel } from "@/hooks/useParcels";
import type { PositionMode } from "@/hooks/useFlightPositions";

const Globe = dynamic(() => import("@/components/Globe"), { ssr: false });

function GlobeWithData() {
  const { parcels, loading, setParcels } = useParcels();
  const { positions: flightPositions, positionMode, setPositionMode } = useFlightPositions(parcels);

  // Ref vers les positions live — mis à jour à chaque render
  const flightPositionsRef = useRef(flightPositions);
  flightPositionsRef.current = flightPositions;

  const globeRef = useRef<any>(null);
  const [selectedParcel, setSelectedParcel] = useState<Parcel | null>(null);

  const handleSelectParcel = (parcel: Parcel) => {
    // Utilise flightPositionsRef.current (positions, pas l'objet hook entier)
    const live = flightPositionsRef.current[parcel.id];
    const pos = (live?.source === "live" && live.lat != null && live.lng != null)
      ? { lat: live.lat, lng: live.lng }
      : parcel.estimated_position;

    if (pos && globeRef.current) {
      globeRef.current.pointOfView(
        { lat: pos.lat, lng: pos.lng, altitude: 1.5 },
        800
      );
      globeRef.current.controls().autoRotate = false;
    }
    setSelectedParcel(parcel);
  };

  const handleCloseModal = () => {
    setSelectedParcel(null);
    if (globeRef.current) globeRef.current.controls().autoRotate = true;
  };

  const handleParcelAdded = (parcel: Parcel) => {
    setParcels(prev => [parcel, ...prev]);
    handleSelectParcel(parcel);
  };

  const handleToggleMode = (parcelId: number) => (mode: PositionMode) => {
    setPositionMode(prev => ({ ...prev, [parcelId]: mode }));
  };

  return (
    <>
      <Globe
        parcels={parcels}
        globeRef={globeRef}
        flightPositions={flightPositions}
        positionMode={positionMode}
      />
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
          flightPosition={flightPositions[selectedParcel.id]}
          positionMode={positionMode[selectedParcel.id] ?? "arc"}
          onToggleMode={handleToggleMode(selectedParcel.id)}
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
