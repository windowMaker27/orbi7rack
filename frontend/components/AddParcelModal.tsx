"use client";

import { useState } from "react";
import { useAuth } from "@/context/AuthContext";
import type { Parcel } from "@/hooks/useParcels";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface AddParcelModalProps {
  onClose: () => void;
  onAdded: (parcel: Parcel) => void;
}

export default function AddParcelModal({ onClose, onAdded }: AddParcelModalProps) {
  const { access } = useAuth();
  const [trackingNumber, setTrackingNumber] = useState("");
  const [carrier, setCarrier] = useState("");
  const [description, setDescription] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const inputStyle: React.CSSProperties = {
    padding: 10,
    borderRadius: 6,
    border: "1px solid rgba(255,68,0,0.3)",
    background: "rgba(0,0,0,0.4)",
    color: "#fff",
    fontFamily: "monospace",
    fontSize: 13,
    outline: "none",
    width: "100%",
    boxSizing: "border-box",
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!trackingNumber.trim()) return;
    setError("");
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/parcels/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${access}`,
        },
        body: JSON.stringify({
          tracking_number: trackingNumber.trim(),
          carrier: carrier.trim(),
          description: description.trim(),
        }),
      });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data?.tracking_number?.[0] ?? data?.detail ?? "Erreur lors de l'ajout");
      }
      const parcel: Parcel = await res.json();
      onAdded(parcel);
      onClose();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    // Backdrop
    <div
      onClick={onClose}
      style={{
        position: "fixed", inset: 0, zIndex: 200,
        background: "rgba(0,0,0,0.6)",
        display: "flex", alignItems: "center", justifyContent: "center",
      }}
    >
      {/* Modal */}
      <div
        onClick={e => e.stopPropagation()}
        style={{
          background: "rgba(15,3,0,0.92)",
          backdropFilter: "blur(20px)",
          WebkitBackdropFilter: "blur(20px)",
          border: "1px solid rgba(255,68,0,0.25)",
          borderRadius: 12,
          padding: 32,
          width: 380,
          display: "flex",
          flexDirection: "column",
          gap: 16,
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <h2 style={{
            color: "#ff6600", fontFamily: "monospace",
            fontSize: 13, letterSpacing: 3,
            textTransform: "uppercase", margin: 0,
          }}>
            Ajouter un colis
          </h2>
          <button onClick={onClose} style={{
            background: "none", border: "none", color: "#ff440088",
            cursor: "pointer", fontSize: 18, lineHeight: 1,
          }}>✕</button>
        </div>

        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <label style={{ color: "#ff440099", fontFamily: "monospace", fontSize: 11, letterSpacing: 1 }}>
              N° DE SUIVI *
            </label>
            <input
              placeholder="ex: JD014600006228006258"
              value={trackingNumber}
              onChange={e => setTrackingNumber(e.target.value)}
              style={inputStyle}
              autoFocus
            />
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <label style={{ color: "#ff440099", fontFamily: "monospace", fontSize: 11, letterSpacing: 1 }}>
              TRANSPORTEUR
            </label>
            <input
              placeholder="ex: DHL, Cainiao, La Poste..."
              value={carrier}
              onChange={e => setCarrier(e.target.value)}
              style={inputStyle}
            />
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <label style={{ color: "#ff440099", fontFamily: "monospace", fontSize: 11, letterSpacing: 1 }}>
              DESCRIPTION
            </label>
            <input
              placeholder="ex: Commande AliExpress"
              value={description}
              onChange={e => setDescription(e.target.value)}
              style={inputStyle}
            />
          </div>

          {error && (
            <p style={{ color: "#ff4444", fontFamily: "monospace", fontSize: 12, margin: 0 }}>
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={loading || !trackingNumber.trim()}
            style={{
              marginTop: 4,
              padding: "10px 0",
              borderRadius: 6,
              border: "none",
              background: loading || !trackingNumber.trim() ? "#ff440044" : "#ff4400",
              color: "#fff",
              cursor: loading || !trackingNumber.trim() ? "not-allowed" : "pointer",
              fontFamily: "monospace",
              fontWeight: "bold",
              fontSize: 13,
              letterSpacing: 1,
              transition: "background 0.2s",
            }}
          >
            {loading ? "Synchronisation 17TRACK..." : "Ajouter"}
          </button>
        </form>
      </div>
    </div>
  );
}
