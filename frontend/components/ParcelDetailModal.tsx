"use client";

import type { Parcel } from "@/hooks/useParcels";
import type { FlightPosition, PositionMode } from "@/hooks/useFlightPositions";

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
  flightPosition?: FlightPosition;
  positionMode?: PositionMode;
  onToggleMode?: (mode: PositionMode) => void;
}

export default function ParcelDetailModal({
  parcel,
  onClose,
  flightPosition,
  positionMode,
  onToggleMode,
}: ParcelDetailModalProps) {
  const statusColor = STATUS_COLORS[parcel.status] ?? "#fff";
  const pos = parcel.estimated_position;

  // Le switch n'est visible que si on a une position live réelle
  const showModeSwitch = flightPosition?.source === "live" && onToggleMode != null;

  return (
    <div
      onClick={onClose}
      style={{
        position: "fixed", inset: 0, zIndex: 200,
        background: "transparent",
        pointerEvents: "auto",
        display: "flex", alignItems: "center", justifyContent: "flex-end",
        paddingRight: 80,
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
          padding: 20,
          width: 320,
          maxHeight: "70vh",
          overflowY: "auto",
          scrollbarWidth: "none",
          display: "flex",
          flexDirection: "column",
          gap: 12,
        }}
      >
        <style>{`#parcel-modal::-webkit-scrollbar { display: none; }`}</style>

        {/* Header */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <h2 style={{
            color: "#ff6600", fontFamily: "monospace",
            fontSize: 11, letterSpacing: 3,
            textTransform: "uppercase", margin: 0,
          }}>
            Détail colis
          </h2>
          <button onClick={onClose} style={{
            background: "none", border: "none", color: "#ff440088",
            cursor: "pointer", fontSize: 16, lineHeight: 1,
          }}>✕</button>
        </div>

        {/* Tracking number */}
        <div style={{
          background: "rgba(255,68,0,0.07)",
          border: "1px solid rgba(255,68,0,0.15)",
          borderRadius: 8, padding: "10px 14px",
        }}>
          <div style={{ color: "#ff440066", fontFamily: "monospace", fontSize: 9, letterSpacing: 2, marginBottom: 4 }}>
            N° DE SUIVI
          </div>
          <div style={{ color: "#fff", fontFamily: "monospace", fontSize: 12, fontWeight: "bold", wordBreak: "break-all" }}>
            {parcel.tracking_number}
          </div>
        </div>

        {/* Infos */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
          {[
            { label: "STATUT", value: STATUS_LABELS[parcel.status] ?? parcel.status, color: statusColor },
            { label: "DESCRIPTION", value: parcel.description || "—", color: "#fff" },
            { label: "ORIGINE", value: parcel.origin_country || "—", color: "#fff" },
            { label: "DESTINATION", value: parcel.dest_country && parcel.dest_country !== "0" ? parcel.dest_country : "—", color: "#fff" },
          ].map(({ label, value, color }) => (
            <div key={label} style={{
              background: "rgba(255,255,255,0.03)",
              border: "1px solid rgba(255,68,0,0.1)",
              borderRadius: 6, padding: "8px 10px",
            }}>
              <div style={{ color: "#ff440055", fontFamily: "monospace", fontSize: 8, letterSpacing: 2, marginBottom: 3 }}>
                {label}
              </div>
              <div style={{ color, fontFamily: "monospace", fontSize: 11, fontWeight: "bold" }}>
                {value}
              </div>
            </div>
          ))}
        </div>

        {/* Mode switch — uniquement si source live */}
        {showModeSwitch && (
          <div style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            background: "rgba(255,68,0,0.06)",
            border: "1px solid rgba(255,68,0,0.15)",
            borderRadius: 8,
            padding: "8px 12px",
          }}>
            <span style={{ color: "#ff440088", fontFamily: "monospace", fontSize: 9, letterSpacing: 2 }}>
              MODE POSITION
            </span>
            <div style={{ display: "flex", gap: 4 }}>
              {(["arc", "live"] as PositionMode[]).map(m => (
                <button
                  key={m}
                  onClick={() => onToggleMode!(m)}
                  style={{
                    background: positionMode === m ? "rgba(255,102,0,0.25)" : "transparent",
                    border: `1px solid ${positionMode === m ? "#ff6600" : "rgba(255,68,0,0.2)"}`,
                    borderRadius: 4,
                    color: positionMode === m ? "#ff6600" : "#ff440055",
                    fontFamily: "monospace",
                    fontSize: 9,
                    letterSpacing: 1,
                    padding: "3px 8px",
                    cursor: "pointer",
                    textTransform: "uppercase",
                  }}
                >
                  {m === "arc" ? "ARC" : "LIVE"}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Position */}
        {pos && (
          <div style={{
            background: "rgba(255,68,0,0.05)",
            border: "1px solid rgba(255,68,0,0.12)",
            borderRadius: 8, padding: "8px 12px",
          }}>
            <div style={{ color: "#ff440055", fontFamily: "monospace", fontSize: 8, letterSpacing: 2, marginBottom: 4 }}>
              POSITION
            </div>
            <div style={{ color: "#ff6600", fontFamily: "monospace", fontSize: 11 }}>
              {pos.lat.toFixed(4)}, {pos.lng.toFixed(4)}
            </div>
            <div style={{ color: "#ffffff44", fontFamily: "monospace", fontSize: 9, marginTop: 3 }}>
              {SOURCE_LABELS[pos.source] ?? pos.source}
            </div>
          </div>
        )}

        {/* Historique events */}
        {parcel.events.length > 0 && (
          <div>
            <div style={{ color: "#ff440066", fontFamily: "monospace", fontSize: 9, letterSpacing: 2, marginBottom: 8 }}>
              HISTORIQUE ({parcel.events.length})
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {parcel.events.map((event, i) => (
                <div key={event.id} style={{ display: "flex", gap: 10, alignItems: "flex-start" }}>
                  <div style={{ display: "flex", flexDirection: "column", alignItems: "center", paddingTop: 3 }}>
                    <div style={{
                      width: 6, height: 6, borderRadius: "50%",
                      background: i === 0 ? statusColor : "#ff440033",
                      flexShrink: 0,
                      boxShadow: i === 0 ? `0 0 5px ${statusColor}` : "none",
                    }} />
                    {i < parcel.events.length - 1 && (
                      <div style={{ width: 1, flex: 1, minHeight: 12, background: "rgba(255,68,0,0.12)", margin: "2px 0" }} />
                    )}
                  </div>
                  <div style={{ flex: 1, paddingBottom: 6 }}>
                    <div style={{ color: "#ffffff88", fontFamily: "monospace", fontSize: 10, lineHeight: 1.4 }}>
                      {event.description || event.status}
                    </div>
                    <div style={{ display: "flex", gap: 6, marginTop: 3, flexWrap: "wrap" }}>
                      {event.location && (
                        <span style={{ color: "#ff660066", fontFamily: "monospace", fontSize: 9 }}>
                          📍 {event.location}
                        </span>
                      )}
                      <span style={{ color: "#ffffff33", fontFamily: "monospace", fontSize: 9 }}>
                        {new Date(event.timestamp).toLocaleDateString("fr-FR", {
                          day: "2-digit", month: "short", year: "numeric",
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
          <div style={{ color: "#ffffff22", fontFamily: "monospace", fontSize: 9, textAlign: "right" }}>
            Sync : {new Date(parcel.last_synced_at).toLocaleString("fr-FR")}
          </div>
        )}
      </div>
    </div>
  );
}
