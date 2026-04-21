import { useEffect, useRef, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import type { Parcel } from "@/hooks/useParcels";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const POLL_INTERVAL = 15_000; // 15s

export interface FlightPosition {
  lat: number;
  lng: number;
  altitude: number | null;
  speed: number | null;
  heading: number | null;
  source: "live" | "simulated";
  provider?: string;
  progress?: number;
}

// Map parcelId -> FlightPosition
export type FlightPositionMap = Record<number, FlightPosition>;

/**
 * Poll /api/parcels/{id}/flight_position/ pour tous les colis en transit.
 * Retourne une map parcelId -> FlightPosition, mise à jour toutes les 15s.
 */
export function useFlightPositions(parcels: Parcel[]): FlightPositionMap {
  const { access } = useAuth();
  const [positions, setPositions] = useState<FlightPositionMap>({});
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

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

    const next: FlightPositionMap = {};
    for (const r of results) {
      if (r.status === "fulfilled" && r.value) {
        next[r.value.id] = r.value.data;
      }
    }
    setPositions(next);
  };

  useEffect(() => {
    fetchAll();
    timerRef.current = setInterval(fetchAll, POLL_INTERVAL);
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [access, inTransitParcels.length]);

  return positions;
}
