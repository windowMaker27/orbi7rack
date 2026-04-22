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

/**
 * Distance approximative entre deux points (haversine simplifiée, en degrés)
 * utilisée uniquement pour calculer progress sur arc.
 */
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
          .then(data => data ? ({ id: p.id, data, parcel: p } as { id: number; data: FlightPosition; parcel: Parcel }) : null)
          .catch(() => null)
      )
    );

    setPositions(prev => {
      const next: FlightPositionMap = { ...prev };

      for (const r of results) {
        if (r.status !== "fulfilled" || !r.value) continue;
        const { id, data, parcel } = r.value;

        if (data.source === "live" && data.lat != null && data.lng != null) {
          // ✅ Position live fraîche — on met à jour le cache
          lastLiveRef.current[id] = { ...data, stale: false };
          next[id] = lastLiveRef.current[id];

        } else if (lastLiveRef.current[id]) {
          // ⚠️ API a répondu simulated/rate-limité mais on a un cache live
          // → on garde la dernière position live, marquée stale
          next[id] = { ...lastLiveRef.current[id], stale: true };

        } else {
          // Jamais eu de live — on garde la position simulée MAIS on s'assure
          // que progress est calculé depuis l'origine réelle, pas depuis la destination.
          // Si data.progress est absent ou === 1, on le recalcule via haversine.
          const origin = data.origin;
          const dest   = data.destination;
          let progress = data.progress;

          if (origin && dest && (progress == null || progress >= 0.98)) {
            // Le backend a renvoyé la destination comme position courante.
            // On calcule la progression réelle origin→dest→data.lat/lng.
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

  // positionMode dérivé de source (ou override manuel)
  // Si stale, on considère comme "live" car les coords sont celles de l'avion
  const positionMode: PositionModeMap = {};
  for (const [idStr, pos] of Object.entries(positions)) {
    const id = Number(idStr);
    positionMode[id] = modeOverrides[id] ?? (pos.source === "live" ? "live" : "arc");
  }

  return { positions, positionMode, setPositionMode: setModeOverrides };
}
