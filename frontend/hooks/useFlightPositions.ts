import { useEffect, useRef, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import type { Parcel } from "@/hooks/useParcels";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const POLL_INTERVAL = 30_000;

export interface FlightPosition {
  lat: number;
  lng: number;
  altitude: number | null;
  speed: number | null;
  heading: number | null;
  source: "live" | "simulated";
  provider?: string;
  progress?: number;
  origin?: { lat: number; lng: number };
  destination?: { lat: number; lng: number };
  /** true si la position vient du cache local (OpenSky indisponible) */
  stale?: boolean;
}

export type FlightPositionMap = Record<number, FlightPosition>;
export type PositionMode = "arc" | "live";
export type PositionModeMap = Record<number, PositionMode>;

export function useFlightPositions(parcels: Parcel[]): {
  positions: FlightPositionMap;
  positionMode: PositionModeMap;
  setPositionMode: React.Dispatch<React.SetStateAction<PositionModeMap>>;
} {
  const { access } = useAuth();
  const [positions, setPositions] = useState<FlightPositionMap>({});
  const [modeOverrides, setModeOverrides] = useState<PositionModeMap>({});
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  // Cache de la dernière position live valide par parcelId
  const lastLiveRef = useRef<FlightPositionMap>({});

  const inTransitParcels = parcels.filter(
    p => p.status === "in_transit" || p.status === "out_for_delivery"
  );

  const fetchAll = async () => {
    if (!access || inTransitParcels.length === 0) return;

    const results = await Promise.allSettled(
      inTransitParcels.map(p =>
        fetch(`${API}/api/parcels/${p.id}/flight_position/`, {
          headers: { Authorization: `Bearer ${access}` },
        })
          .then(res => res.ok ? res.json() : null)
          .then(data => data ? ({ id: p.id, data } as { id: number; data: FlightPosition }) : null)
          .catch(() => null)
      )
    );

    setPositions(prev => {
      const next: FlightPositionMap = { ...prev };

      for (const r of results) {
        if (r.status !== "fulfilled" || !r.value) continue;
        const { id, data } = r.value;

        if (data.source === "live" && data.lat != null && data.lng != null) {
          // Nouvelle position live valide → on met à jour le cache
          lastLiveRef.current[id] = { ...data, stale: false };
          next[id] = lastLiveRef.current[id];
        } else if (lastLiveRef.current[id]) {
          // API répond mais pas de live (rate-limit, simulated…)
          // → on garde la dernière position live connue, marquée stale
          next[id] = { ...lastLiveRef.current[id], stale: true };
        } else {
          // Jamais eu de live → on prend ce que l'API donne (simulated/fallback)
          next[id] = data;
        }
      }

      return next;
    });
  };

  useEffect(() => {
    fetchAll();
    timerRef.current = setInterval(fetchAll, POLL_INTERVAL);
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [access, inTransitParcels.length]);

  // positionMode dérivé de source (ou override manuel)
  const positionMode: PositionModeMap = {};
  for (const [idStr, pos] of Object.entries(positions)) {
    const id = Number(idStr);
    positionMode[id] = modeOverrides[id] ?? (pos.source === "live" ? "live" : "arc");
  }

  return { positions, positionMode, setPositionMode: setModeOverrides };
}
