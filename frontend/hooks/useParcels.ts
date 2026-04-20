import { useEffect, useState } from "react";
import { useAuth } from "@/context/AuthContext";

export interface TrackingEvent {
  id: number;
  timestamp: string;
  location: string;
  latitude: number | null;
  longitude: number | null;
  status: string;
  description: string;
}

export interface Parcel {
  id: number;
  tracking_number: string;
  carrier: string;
  description: string;
  origin_country: string;
  dest_country: string;
  status: string;
  last_synced_at: string | null;
  created_at: string;
  updated_at: string;
  events: TrackingEvent[];
}

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export function useParcels() {
  const { access } = useAuth();
  const [parcels, setParcels] = useState<Parcel[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!access) return;

    setLoading(true);
    fetch(`${API}/api/parcels/`, {
      headers: { Authorization: `Bearer ${access}` },
    })
      .then(res => {
        if (!res.ok) throw new Error("Erreur lors du chargement des colis");
        return res.json();
      })
      .then(data => {
        // L'API DRF retourne soit un tableau soit { results: [...] } si pagination
        setParcels(Array.isArray(data) ? data : data.results ?? []);
      })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  }, [access]);

  return { parcels, setParcels, loading, error };
}
