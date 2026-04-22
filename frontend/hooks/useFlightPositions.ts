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
  /** true si la position vient du cache DB (OpenSky indisponible) */
  stale?: boolean;
  /** ISO date de la dernière position live fraîche */
  stale_since?: string | null;
}

export type FlightPositionMap = Record<number, FlightPosition>;
export type PositionMode = "arc" | "live";
export type PositionModeMap = Record<number, PositionMode>;

function haversineDeg(lat1: number, lng1: number, lat2: number, lng2: number): number {
  const R = 6371;
  const dLat = (lat2 - lat1) * Math.PI / 180;
  const dLng = (lng2 - lng1) * Math.PI / 180;
  const a = Math.sin(dLat/2)**2 +
    Math.cos(lat1 * Math.PI/180) * Math.cos(lat2 * Math.PI/180) * Math.sin(dLng/2)**2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
}

export function useFlightPositions(parcels: Parcel[]): {
  positions: FlightPositionMap;
  positionMode: PositionModeMap;
  setPositionMode: React.Dispatch<React.SetStateAction<PositionModeMap>>;
} {
  const { access } = useAuth();
  const [positions, setPositions] = useState<FlightPositionMap>({});
  const [modeOverrides, setModeOverrides] = useState<PositionModeMap>({});
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
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
          .then(data => data ? ({ id: p.id, data, parcel: p } as { id: number; data: FlightPosition; parcel: Parcel }) : null)
          .catch(() => null)
      )
    );

    setPositions(prev => {
      const next: FlightPositionMap = { ...prev };

      for (const r of results) {
        if (r.status !== "fulfilled" || !r.value) continue;
        const { id, data } = r.value;

        if (data.source === "live" && data.lat != null && data.lng != null) {
          if (data.stale) {
            // Backend a renvoyé un stale depuis la DB — on garde stale_since du backend
            const entry: FlightPosition = {
              ...data,
              stale: true,
              stale_since: data.stale_since ?? lastLiveRef.current[id]?.stale_since ?? new Date().toISOString(),
            };
            lastLiveRef.current[id] = entry;
            next[id] = entry;
          } else {
            // Position live fraîche
            const entry: FlightPosition = { ...data, stale: false, stale_since: null };
            lastLiveRef.current[id] = entry;
            next[id] = entry;
          }
        } else if (lastLiveRef.current[id]) {
          // API simulated mais on a un cache live — on marque stale
          const cached = lastLiveRef.current[id];
          next[id] = {
            ...cached,
            stale: true,
            stale_since: cached.stale_since ?? new Date().toISOString(),
          };
        } else {
          // Jamais eu de live — recalcul progress si nécessaire
          const origin = data.origin;
          const dest   = data.destination;
          let progress = data.progress;

          if (origin && dest && (progress == null || progress >= 0.98)) {
            const totalDist = haversineDeg(origin.lat, origin.lng, dest.lat, dest.lng);
            const doneDist  = haversineDeg(origin.lat, origin.lng, data.lat, data.lng);
            progress = totalDist > 0 ? Math.min(0.98, doneDist / totalDist) : 0.5;
          }

          next[id] = { ...data, progress: progress ?? 0.5 };
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

  const positionMode: PositionModeMap = {};
  for (const [idStr, pos] of Object.entries(positions)) {
    const id = Number(idStr);
    positionMode[id] = modeOverrides[id] ?? (pos.source === "live" ? "live" : "arc");
  }

  return { positions, positionMode, setPositionMode: setModeOverrides };
}
