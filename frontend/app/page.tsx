"use client";

import dynamic from "next/dynamic";
import { useState, useRef } from "react";
import AuthGate from "@/components/AuthGate";
import Sidebar from "@/components/Sidebar";
import ParcelDetailModal from "@/components/ParcelDetailModal";
import TopBar from "@/components/TopBar";
import { useTheme } from "@/context/ThemeContext";
import { useAuth } from "@/context/AuthContext";
import { useParcels } from "@/hooks/useParcels";
import { useFlightPositions } from "@/hooks/useFlightPositions";
import type { Parcel } from "@/hooks/useParcels";
import type { PositionMode } from "@/hooks/useFlightPositions";

/*
  Globe chargé dynamiquement (WebGL/Three.js) — pas de SSR.
  Le composant n'est monté qu'après authentification pour éviter
  que le canvas capture les touch events pendant l'écran de login.
*/
const Globe = dynamic(() => import("@/components/Globe"), { ssr: false });

/** Durée de l'animation POV en ms */
const POV_DURATION = 1200;

/** Slerp sphérique identique à celui de Globe.tsx */
function slerpLatLng(
  lat1: number, lng1: number,
  lat2: number, lng2: number,
  t: number,
): [number, number] {
  const toRad = (d: number) => d * Math.PI / 180;
  const toDeg = (r: number) => r * 180 / Math.PI;
  const f1 = toRad(lat1), l1 = toRad(lng1), f2 = toRad(lat2), l2 = toRad(lng2);
  const x1 = Math.cos(f1) * Math.cos(l1), y1 = Math.cos(f1) * Math.sin(l1), z1 = Math.sin(f1);
  const x2 = Math.cos(f2) * Math.cos(l2), y2 = Math.cos(f2) * Math.sin(l2), z2 = Math.sin(f2);
  const dot = Math.min(1, x1 * x2 + y1 * y2 + z1 * z2);
  const omega = Math.acos(dot);
  if (omega < 1e-10) return [lat1, lng1];
  const s = Math.sin(omega);
  const a = Math.sin((1 - t) * omega) / s, b = Math.sin(t * omega) / s;
  return [
    toDeg(Math.atan2(a * z1 + b * z2, Math.sqrt((a * x1 + b * x2) ** 2 + (a * y1 + b * y2) ** 2))),
    toDeg(Math.atan2(a * y1 + b * y2, a * x1 + b * x2)),
  ];
}

function resolveCameraTarget(
  parcel: Parcel,
  live: any,
): { lat: number; lng: number } | null {
  if (!live) return parcel.estimated_position ?? null;

  if (live.source === "live" && !live.stale && live.lat != null && live.lng != null) {
    return { lat: live.lat, lng: live.lng };
  }

  if (live.origin && live.destination && live.progress != null) {
    const progress = Math.max(0.05, Math.min(0.95, live.progress));
    const [lat, lng] = slerpLatLng(
      live.origin.lat, live.origin.lng,
      live.destination.lat, live.destination.lng,
      progress,
    );
    return { lat, lng };
  }

  if (live.lat != null && live.lng != null) {
    return { lat: live.lat, lng: live.lng };
  }

  return parcel.estimated_position ?? null;
}

function GlobeWithData() {
  const { theme } = useTheme();
  const { parcels, loading, setParcels, deleteParcel } = useParcels();
  const { positions: flightPositions, positionMode, setPositionMode } = useFlightPositions(parcels);

  const flightPositionsRef = useRef(flightPositions);
  flightPositionsRef.current = flightPositions;

  const globeRef = useRef<any>(null);
  const [selectedParcel, setSelectedParcel] = useState<Parcel | null>(null);

  const handleSelectParcel = (parcel: Parcel) => {
    const live = flightPositionsRef.current[parcel.id];
    const pos  = resolveCameraTarget(parcel, live);

    if (pos && globeRef.current) {
      globeRef.current.setPOVAnimating?.(true);
      globeRef.current.pointOfView({ lat: pos.lat, lng: pos.lng, altitude: 1.5 }, POV_DURATION);
      globeRef.current.controls().autoRotate = false;
      setTimeout(() => {
        globeRef.current?.setPOVAnimating?.(false);
      }, POV_DURATION + 50);
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

  const handleDeleteParcel = async (id: number) => {
    await deleteParcel(id);
    if (selectedParcel?.id === id) handleCloseModal();
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
        theme={theme}
      />
      <Sidebar
        parcels={parcels}
        loading={loading}
        onSelectParcel={handleSelectParcel}
        onParcelAdded={handleParcelAdded}
        onDeleteParcel={handleDeleteParcel}
        flightPositions={flightPositions}
        theme={theme}
      />
      <TopBar />
      {selectedParcel && (
        <ParcelDetailModal
          parcel={selectedParcel}
          onClose={handleCloseModal}
          onDelete={handleDeleteParcel}
          flightPosition={flightPositions[selectedParcel.id]}
          positionMode={positionMode[selectedParcel.id] ?? "arc"}
          onToggleMode={handleToggleMode(selectedParcel.id)}
          theme={theme}
        />
      )}
    </>
  );
}

export default function Home() {
  const { access } = useAuth();

  return (
    <>
      {/*
        AuthGate monté UNIQUEMENT quand !access.
        Raison : le div fixed inset-0 z-9999 restait dans le DOM même
        après login (retournait un fragment vide) et continuait à
        intercepter les touch events sur mobile.
      */}
      {!access && <AuthGate>{null}</AuthGate>}

      {/*
        Globe monté UNIQUEMENT après auth.
        Raison : le canvas WebGL (globe.gl / Three.js) capture tous les
        touch events iOS Safari même avec pointer-events:none mal hérité.
        En ne le montant pas du tout pendant le login, on élimine le problème
        à la racine. Le CSS pointer-events:none sur .globe-container reste
        en place pour protéger les overlays (sidebar, modals) une fois connecté.
      */}
      {access && (
        <main style={{ margin: 0, padding: 0 }}>
          <GlobeWithData />
        </main>
      )}
    </>
  );
}
