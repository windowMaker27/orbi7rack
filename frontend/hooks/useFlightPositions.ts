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
  // overrides manuels : seulement les parcelIds où l'user a cliqué
  const [modeOverrides, setModeOverrides] = useState<PositionModeMap>({});
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

    const nextPos: FlightPositionMap = {};
    for (const r of results) {
      if (r.status === "fulfilled" && r.value) {
        nextPos[r.value.id] = r.value.data;
      }
    }
    setPositions(nextPos);
  };

  useEffect(() => {
    fetchAll();
    timerRef.current = setInterval(fetchAll, POLL_INTERVAL);
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [access, inTransitParcels.length]);

  // positionMode = override manuel si présent, sinon dérivé de source API
  const positionMode: PositionModeMap = {};
  for (const [idStr, pos] of Object.entries(positions)) {
    const id = Number(idStr);
    positionMode[id] = modeOverrides[id] ?? (pos.source === "live" ? "live" : "arc");
  }

  return { positions, positionMode, setPositionMode: setModeOverrides };
}
