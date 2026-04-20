"use client";

import { useState } from "react";
import type { Parcel } from "@/hooks/useParcels";

const STATUS_LABELS: Record<string, string> = {
  pending: "En attente",
  in_transit: "En transit",
  out_for_delivery: "En livraison",
  delivered: "Livré",
  exception: "Incident",
  expired: "Expiré",
};

const STATUS_COLORS: Record<string, string> = {
  pending: "#ffaa00",
  in_transit: "#00cfff",
  out_for_delivery: "#00ff99",
  delivered: "#44ff44",
  exception: "#ff2222",
  expired: "#888888",
};

interface SidebarProps {
  parcels: Parcel[];
  loading: boolean;
  onSelectParcel: (parcel: Parcel) => void;
}

export default function Sidebar({ parcels, loading, onSelectParcel }: SidebarProps) {
  const [open, setOpen] = useState(true);
  const [selected, setSelected] = useState<number | null>(null);

  const handleSelect = (parcel: Parcel) => {
    setSelected(parcel.id);
    onSelectParcel(parcel);
  };

  return (
    <div style={{
      position: "fixed",
      top: 0, left: 0,
      height: "100vh",
      zIndex: 100,
      display: "flex",
      alignItems: "stretch",
      pointerEvents: "none",
    }}>
      {/* Panel */}
      <div style={{
        width: open ? 300 : 0,
        overflow: "hidden",
        transition: "width 0.35s cubic-bezier(0.16,1,0.3,1)",
        pointerEvents: "auto",
      }}>
        <div style={{
          width: 300,
          height: "100%",
          background: "rgba(10, 0, 0, 0.75)",
          backdropFilter: "blur(16px)",
          WebkitBackdropFilter: "blur(16px)",
          borderRight: "1px solid rgba(255,68,0,0.2)",
          display: "flex",
          flexDirection: "column",
          padding: "24px 0",
        }}>
          <h2 style={{
            color: "#ff6600",
            fontFamily: "monospace",
            fontSize: 13,
            letterSpacing: 3,
            textTransform: "uppercase",
            padding: "0 20px 16px",
            borderBottom: "1px solid rgba(255,68,0,0.15)",
            margin: 0,
          }}>
            Colis ({parcels.length})
          </h2>

          <div style={{ flex: 1, overflowY: "auto", padding: "8px 0" }}>
            {loading && (
              <p style={{ color: "#ff440088", fontFamily: "monospace", fontSize: 12, padding: "16px 20px" }}>
                Chargement...
              </p>
            )}
            {!loading && parcels.length === 0 && (
              <p style={{ color: "#ff440055", fontFamily: "monospace", fontSize: 12, padding: "16px 20px" }}>
                Aucun colis suivi
              </p>
            )}
            {parcels.map(parcel => (
              <button
                key={parcel.id}
                onClick={() => handleSelect(parcel)}
                style={{
                  width: "100%",
                  background: selected === parcel.id ? "rgba(255,68,0,0.12)" : "transparent",
                  border: "none",
                  borderLeft: `3px solid ${
                    selected === parcel.id ? STATUS_COLORS[parcel.status] ?? "#ff4400" : "transparent"
                  }`,
                  padding: "12px 20px",
                  cursor: "pointer",
                  textAlign: "left",
                  transition: "background 0.2s",
                }}
                onMouseEnter={e => {
                  if (selected !== parcel.id)
                    (e.currentTarget as HTMLElement).style.background = "rgba(255,68,0,0.07)";
                }}
                onMouseLeave={e => {
                  if (selected !== parcel.id)
                    (e.currentTarget as HTMLElement).style.background = "transparent";
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                  <span style={{
                    width: 8, height: 8, borderRadius: "50%",
                    background: STATUS_COLORS[parcel.status] ?? "#fff",
                    flexShrink: 0,
                    boxShadow: `0 0 6px ${STATUS_COLORS[parcel.status] ?? "#fff"}`,
                  }} />
                  <span style={{
                    color: "#fff",
                    fontFamily: "monospace",
                    fontSize: 12,
                    fontWeight: "bold",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                  }}>
                    {parcel.tracking_number}
                  </span>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span style={{
                    color: STATUS_COLORS[parcel.status] ?? "#aaa",
                    fontFamily: "monospace",
                    fontSize: 11,
                  }}>
                    {STATUS_LABELS[parcel.status] ?? parcel.status}
                  </span>
                  {parcel.description && (
                    <span style={{ color: "#ffffff55", fontFamily: "monospace", fontSize: 10 }}>
                      {parcel.description.slice(0, 16)}
                    </span>
                  )}
                </div>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Toggle tab */}
      <button
        onClick={() => setOpen(o => !o)}
        style={{
          alignSelf: "center",
          pointerEvents: "auto",
          background: "rgba(10,0,0,0.75)",
          backdropFilter: "blur(16px)",
          border: "1px solid rgba(255,68,0,0.2)",
          borderLeft: "none",
          borderRadius: "0 6px 6px 0",
          color: "#ff6600",
          cursor: "pointer",
          padding: "12px 6px",
          fontFamily: "monospace",
          fontSize: 14,
          lineHeight: 1,
          transition: "all 0.2s",
        }}
        title={open ? "Fermer" : "Ouvrir"}
      >
        {open ? "◀" : "▶"}
      </button>
    </div>
  );
}
