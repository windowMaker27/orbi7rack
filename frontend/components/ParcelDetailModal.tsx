"use client";

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

const SOURCE_LABELS: Record<string, string> = {
  dest_country: "Position estimée (destination)",
  last_event: "Dernière position connue",
  origin_country: "Position estimée (origine)",
};

interface ParcelDetailModalProps {
  parcel: Parcel;
  onClose: () => void;
}

export default function ParcelDetailModal({ parcel, onClose }: ParcelDetailModalProps) {
  const statusColor = STATUS_COLORS[parcel.status] ?? "#fff";
  const pos = parcel.estimated_position;

  return (
    <div
      onClick={onClose}
      style={{
        position: "fixed", inset: 0, zIndex: 200,
        display: "flex", alignItems: "center", justifyContent: "center",
        pointerEvents: "auto",
      }}
    >
      <div
        onClick={e => e.stopPropagation()}
        style={{
          background: "rgba(15,3,0,0.94)",
          backdropFilter: "blur(20px)",
          WebkitBackdropFilter: "blur(20px)",
          border: "1px solid rgba(255,68,0,0.25)",
          borderRadius: 12,
          padding: 28,
          width: 400,
          maxHeight: "80vh",
          overflowY: "auto",
          display: "flex",
          flexDirection: "column",
          gap: 16,
        }}
      >
        {/* Header */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <h2 style={{
            color: "#ff6600", fontFamily: "monospace",
            fontSize: 13, letterSpacing: 3,
            textTransform: "uppercase", margin: 0,
          }}>
            Détail colis
          </h2>
          <button onClick={onClose} style={{
            background: "none", border: "none", color: "#ff440088",
            cursor: "pointer", fontSize: 18, lineHeight: 1,
          }}>✕</button>
        </div>

        {/* Tracking number */}
        <div style={{
          background: "rgba(255,68,0,0.07)",
          border: "1px solid rgba(255,68,0,0.15)",
          borderRadius: 8, padding: "12px 16px",
        }}>
          <div style={{ color: "#ff440066", fontFamily: "monospace", fontSize: 10, letterSpacing: 2, marginBottom: 4 }}>
            N° DE SUIVI
          </div>
          <div style={{ color: "#fff", fontFamily: "monospace", fontSize: 14, fontWeight: "bold", wordBreak: "break-all" }}>
            {parcel.tracking_number}
          </div>
        </div>

        {/* Infos */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
          {[
            { label: "STATUT", value: STATUS_LABELS[parcel.status] ?? parcel.status, color: statusColor },
            { label: "DESCRIPTION", value: parcel.description || "—", color: "#fff" },
            { label: "ORIGINE", value: parcel.origin_country || "—", color: "#fff" },
            { label: "DESTINATION", value: parcel.dest_country && parcel.dest_country !== "0" ? parcel.dest_country : "—", color: "#fff" },
          ].map(({ label, value, color }) => (
            <div key={label} style={{
              background: "rgba(255,255,255,0.03)",
              border: "1px solid rgba(255,68,0,0.1)",
              borderRadius: 6, padding: "10px 12px",
            }}>
              <div style={{ color: "#ff440055", fontFamily: "monospace", fontSize: 9, letterSpacing: 2, marginBottom: 4 }}>
                {label}
              </div>
              <div style={{ color, fontFamily: "monospace", fontSize: 12, fontWeight: "bold" }}>
                {value}
              </div>
            </div>
          ))}
        </div>

        {/* Position */}
        {pos && (
          <div style={{
            background: "rgba(255,68,0,0.05)",
            border: "1px solid rgba(255,68,0,0.12)",
            borderRadius: 8, padding: "10px 14px",
          }}>
            <div style={{ color: "#ff440055", fontFamily: "monospace", fontSize: 9, letterSpacing: 2, marginBottom: 6 }}>
              POSITION
            </div>
            <div style={{ color: "#ff6600", fontFamily: "monospace", fontSize: 11 }}>
              {pos.lat.toFixed(4)}, {pos.lng.toFixed(4)}
            </div>
            <div style={{ color: "#ffffff44", fontFamily: "monospace", fontSize: 10, marginTop: 4 }}>
              {SOURCE_LABELS[pos.source] ?? pos.source}
            </div>
          </div>
        )}

        {/* Historique events */}
        {parcel.events.length > 0 && (
          <div>
            <div style={{ color: "#ff440066", fontFamily: "monospace", fontSize: 10, letterSpacing: 2, marginBottom: 10 }}>
              HISTORIQUE ({parcel.events.length})
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {parcel.events.map((event, i) => (
                <div key={event.id} style={{
                  display: "flex", gap: 12, alignItems: "flex-start",
                }}>
                  <div style={{ display: "flex", flexDirection: "column", alignItems: "center", paddingTop: 4 }}>
                    <div style={{
                      width: 8, height: 8, borderRadius: "50%",
                      background: i === 0 ? statusColor : "#ff440033",
                      flexShrink: 0,
                      boxShadow: i === 0 ? `0 0 6px ${statusColor}` : "none",
                    }} />
                    {i < parcel.events.length - 1 && (
                      <div style={{ width: 1, flex: 1, minHeight: 16, background: "rgba(255,68,0,0.12)", margin: "3px 0" }} />
                    )}
                  </div>
                  <div style={{ flex: 1, paddingBottom: 8 }}>
                    <div style={{ color: "#ffffff99", fontFamily: "monospace", fontSize: 11, lineHeight: 1.4 }}>
                      {event.description || event.status}
                    </div>
                    <div style={{ display: "flex", gap: 8, marginTop: 4, flexWrap: "wrap" }}>
                      {event.location && (
                        <span style={{ color: "#ff660066", fontFamily: "monospace", fontSize: 10 }}>
                          📍 {event.location}
                        </span>
                      )}
                      <span style={{ color: "#ffffff33", fontFamily: "monospace", fontSize: 10 }}>
                        {new Date(event.timestamp).toLocaleDateString("fr-FR", {
                          day: "2-digit", month: "short", year: "numeric",
                          hour: "2-digit", minute: "2-digit",
                        })}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Sync info */}
        {parcel.last_synced_at && (
          <div style={{ color: "#ffffff22", fontFamily: "monospace", fontSize: 10, textAlign: "right" }}>
            Sync : {new Date(parcel.last_synced_at).toLocaleString("fr-FR")}
          </div>
        )}
      </div>
    </div>
  );
}
