"use client";

import { useState } from "react";
import { useAuth } from "@/context/AuthContext";
import type { Parcel } from "@/hooks/useParcels";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface AddParcelModalProps {
  onClose: () => void;
  onParcelAdded: (parcel: Parcel) => void;
}

export default function AddParcelModal({ onClose, onParcelAdded }: AddParcelModalProps) {
  const { access } = useAuth();

  const [trackingNumber, setTrackingNumber] = useState("");
  const [carrier, setCarrier] = useState("");
  const [description, setDescription] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  /* font-size: 16px obligatoire sur iOS pour éviter le zoom auto sur focus input */
  const inputStyle: React.CSSProperties = {
    padding: 12,
    borderRadius: 6,
    border: "1px solid var(--border)",
    background: "var(--accent-dim)",
    color: "var(--text)",
    fontFamily: "inherit",
    fontSize: 16,
    outline: "none",
    width: "100%",
    boxSizing: "border-box",
    minHeight: 44,
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
      onParcelAdded(parcel);
      onClose();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="add-modal-overlay" onClick={onClose}>
      <div
        className="add-modal-panel"
        onClick={e => e.stopPropagation()}
        style={{
          background: "var(--surface)",
          backdropFilter: "blur(20px)",
          WebkitBackdropFilter: "blur(20px)",
          border: "1px solid var(--border)",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <h2 style={{
            color: "var(--accent)",
            fontFamily: "inherit",
            fontSize: 13,
            letterSpacing: 3,
            textTransform: "uppercase",
            margin: 0,
          }}>
            Ajouter un colis
          </h2>
          <button onClick={onClose} style={{
            background: "none",
            border: "none",
            color: "var(--text-muted)",
            cursor: "pointer",
            fontSize: 18,
            lineHeight: 1,
            minHeight: 44,
            minWidth: 44,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}>✕</button>
        </div>

        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <label style={{
              color: "var(--text-muted)",
              fontFamily: "inherit",
              fontSize: 11,
              letterSpacing: 1,
            }}>
              N° DE SUIVI *
            </label>
            <input
              placeholder="ex: JD014600006228006258"
              value={trackingNumber}
              onChange={e => setTrackingNumber(e.target.value)}
              style={inputStyle}
              autoComplete="off"
              autoCorrect="off"
              autoCapitalize="none"
            />
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <label style={{
              color: "var(--text-muted)",
              fontFamily: "inherit",
              fontSize: 11,
              letterSpacing: 1,
            }}>
              TRANSPORTEUR (optionnel)
            </label>
            <input
              placeholder="ex: DHL, Cainiao, La Poste..."
              value={carrier}
              onChange={e => setCarrier(e.target.value)}
              style={inputStyle}
              autoComplete="off"
            />
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <label style={{
              color: "var(--text-muted)",
              fontFamily: "inherit",
              fontSize: 11,
              letterSpacing: 1,
            }}>
              DESCRIPTION
            </label>
            <input
              placeholder="ex: Commande AliExpress"
              value={description}
              onChange={e => setDescription(e.target.value)}
              style={inputStyle}
              autoComplete="off"
            />
          </div>

          {error && (
            <p style={{ color: "var(--danger)", fontFamily: "inherit", fontSize: 12, margin: 0 }}>
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={loading || !trackingNumber.trim()}
            style={{
              marginTop: 4,
              padding: "12px 0",
              borderRadius: 6,
              border: "none",
              background: loading || !trackingNumber.trim() ? "var(--accent-mid)" : "var(--accent)",
              color: "var(--text)",
              cursor: loading || !trackingNumber.trim() ? "not-allowed" : "pointer",
              fontFamily: "inherit",
              fontWeight: "bold",
              fontSize: 14,
              letterSpacing: 1,
              transition: "background 0.2s",
              minHeight: 44,
              opacity: loading || !trackingNumber.trim() ? 0.5 : 1,
            }}
          >
            {loading ? "Synchronisation 17TRACK..." : "Ajouter"}
          </button>
        </form>
      </div>
    </div>
  );
}
