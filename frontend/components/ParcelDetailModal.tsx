"use client";

import { useState } from "react";
import type { Parcel } from "@/hooks/useParcels";
import type { FlightPosition, PositionMode } from "@/hooks/useFlightPositions";
import type { Theme } from "@/context/ThemeContext";

const STATUS_LABELS: Record<string, string> = {
  pending: "En attente",
  in_transit: "En transit",
  out_for_delivery: "En livraison",
  delivered: "Livré",
  exception: "Incident",
  expired: "Expiré",
};

const STATUS_COLORS_DARK: Record<string, string> = {
  pending: "#ffaa00",
  in_transit: "#00cfff",
  out_for_delivery: "#00ff99",
  delivered: "#44ff44",
  exception: "#ff2222",
  expired: "#888888",
};

const STATUS_COLORS_LIGHT: Record<string, string> = {
  pending: "#b86e00",
  in_transit: "#0066cc",
  out_for_delivery: "#007a44",
  delivered: "#2a7a00",
  exception: "#cc2200",
  expired: "#666666",
};

const SOURCE_LABELS: Record<string, string> = {
  dest_country: "Position estimée (destination)",
  last_event: "Dernière position connue",
  origin_country: "Position estimée (origine)",
};

interface ParcelDetailModalProps {
  parcel: Parcel;
  onClose: () => void;
  onDelete: (id: number) => void;
  flightPosition?: FlightPosition;
  positionMode?: PositionMode;
  onToggleMode?: (mode: PositionMode) => void;
  theme: Theme;
}

export default function ParcelDetailModal({
  parcel, onClose, onDelete,
  flightPosition, positionMode, onToggleMode,
  theme,
}: ParcelDetailModalProps) {
  const [confirmDelete, setConfirmDelete] = useState(false);
  const isDark = theme === "dark";
  const STATUS_COLORS = isDark ? STATUS_COLORS_DARK : STATUS_COLORS_LIGHT;
  const statusColor = STATUS_COLORS[parcel.status] ?? (isDark ? "#fff" : "#1a1a2e");
  const pos = parcel.estimated_position;
  const showModeSwitch = flightPosition?.source === "live" && onToggleMode != null;
  const activeMode: PositionMode = positionMode ?? "arc";
  const isStale = flightPosition?.stale === true;

  const c = {
    bg:        isDark ? "rgba(15,3,0,0.94)"        : "rgba(240,237,232,0.97)",
    border:    isDark ? "rgba(255,68,0,0.25)"       : "rgba(0,102,204,0.2)",
    accent:    isDark ? "#ff6600"                   : "#0066cc",
    accentDim: isDark ? "rgba(255,68,0,0.07)"       : "rgba(0,102,204,0.06)",
    accentBdr: isDark ? "rgba(255,68,0,0.15)"       : "rgba(0,102,204,0.2)",
    accentLbl: isDark ? "#ff440066"                 : "rgba(0,80,180,0.7)",
    accentMid: isDark ? "rgba(255,102,0,0.3)"       : "rgba(0,102,204,0.18)",
    text:      isDark ? "#ffffff"                   : "#0f0f1a",
    muted:     isDark ? "#ffffff88"                 : "rgba(15,15,26,0.75)",
    faint:     isDark ? "#ffffff44"                 : "rgba(15,15,26,0.5)",
    card:      isDark ? "rgba(255,255,255,0.03)"    : "rgba(255,255,255,0.7)",
    cardBdr:   isDark ? "rgba(255,68,0,0.1)"        : "rgba(0,80,160,0.2)",
    timelineDot: isDark ? "rgba(255,68,0,0.25)"     : "rgba(0,80,160,0.3)",
    timelineLine: isDark ? "rgba(255,68,0,0.15)"    : "rgba(0,80,160,0.2)",
    danger:    isDark ? "#ff4444"                   : "#cc2200",
    dangerBg:  isDark ? "rgba(255,68,68,0.1)"       : "rgba(204,34,0,0.06)",
    dangerBdr: isDark ? "rgba(255,68,68,0.3)"       : "rgba(204,34,0,0.2)",
    dangerHov: isDark ? "rgba(255,68,68,0.2)"       : "rgba(204,34,0,0.12)",
    warning:   isDark ? "#ffaa00"                   : "#b86e00",
    warnBg:    isDark ? "rgba(255,170,0,0.08)"      : "rgba(184,110,0,0.06)",
    warnBdr:   isDark ? "rgba(255,170,0,0.25)"      : "rgba(184,110,0,0.2)",
    liveGreen: isDark ? "#00ff99"                   : "#007a44",
    eventDesc: isDark ? "rgba(255,255,255,0.8)"     : "rgba(10,10,30,0.85)",
    eventLoc:  isDark ? "rgba(255,102,0,0.7)"       : "rgba(0,80,160,0.65)",
    eventDate: isDark ? "rgba(255,255,255,0.4)"     : "rgba(10,10,30,0.5)",
  };

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
          background: c.bg,
          backdropFilter: "blur(20px)",
          WebkitBackdropFilter: "blur(20px)",
          border: `1px solid ${c.border}`,
          borderRadius: 12,
          padding: 20,
          width: 320,
          maxHeight: "75vh",
          overflowY: "auto",
          scrollbarWidth: "thin",
          display: "flex", flexDirection: "column", gap: 12,
        }}
      >
        {/* Header */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <h2 style={{ color: c.accent, fontFamily: "monospace", fontSize: 11, letterSpacing: 3, textTransform: "uppercase", margin: 0 }}>
            Détail colis
          </h2>
          <button onClick={onClose} style={{ background: "none", border: "none", color: c.accentLbl, cursor: "pointer", fontSize: 16, lineHeight: 1 }}>✕</button>
        </div>

        {/* Tracking number */}
        <div style={{ background: c.accentDim, border: `1px solid ${c.accentBdr}`, borderRadius: 8, padding: "10px 14px" }}>
          <div style={{ color: c.accentLbl, fontFamily: "monospace", fontSize: 9, letterSpacing: 2, marginBottom: 4 }}>N° DE SUIVI</div>
          <div style={{ color: c.text, fontFamily: "monospace", fontSize: 12, fontWeight: "bold", wordBreak: "break-all" }}>
            {parcel.tracking_number}
          </div>
        </div>

        {/* Infos grid */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
          {[
            { label: "STATUT",      value: STATUS_LABELS[parcel.status] ?? parcel.status, color: statusColor },
            { label: "DESCRIPTION", value: parcel.description || "—",                    color: c.text },
            { label: "ORIGINE",     value: parcel.origin_country || "—",                  color: c.text },
            { label: "DESTINATION", value: parcel.dest_country && parcel.dest_country !== "0" ? parcel.dest_country : "—", color: c.text },
          ].map(({ label, value, color }) => (
            <div key={label} style={{ background: c.card, border: `1px solid ${c.cardBdr}`, borderRadius: 6, padding: "8px 10px" }}>
              <div style={{ color: c.accentLbl, fontFamily: "monospace", fontSize: 8, letterSpacing: 2, marginBottom: 3 }}>{label}</div>
              <div style={{ color, fontFamily: "monospace", fontSize: 11, fontWeight: "bold" }}>{value}</div>
            </div>
          ))}
        </div>

        {/* Bannière stale */}
        {isStale && (
          <div style={{ display: "flex", alignItems: "center", gap: 8, background: c.warnBg, border: `1px solid ${c.warnBdr}`, borderRadius: 8, padding: "7px 12px" }}>
            <span style={{ fontSize: 13 }}>⚠️</span>
            <div>
              <div style={{ color: c.warning, fontFamily: "monospace", fontSize: 9, letterSpacing: 1, fontWeight: "bold" }}>SIGNAL PERDU</div>
              <div style={{ color: c.warning + "99", fontFamily: "monospace", fontSize: 9, marginTop: 2 }}>Dernière position connue — OpenSky indisponible</div>
            </div>
          </div>
        )}

        {/* Switch ARC / LIVE */}
        {showModeSwitch && (
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", background: c.accentDim, border: `1px solid ${c.accentBdr}`, borderRadius: 8, padding: "8px 12px" }}>
            <span style={{ color: c.accentLbl, fontFamily: "monospace", fontSize: 9, letterSpacing: 2 }}>MODE POSITION</span>
            <div style={{ display: "flex", gap: 4 }}>
              {(["arc", "live"] as PositionMode[]).map(m => {
                const isActive = activeMode === m;
                return (
                  <button
                    key={m}
                    onClick={() => onToggleMode!(m)}
                    style={{
                      background: isActive ? c.accentMid : "transparent",
                      border: `1px solid ${isActive ? c.accent : c.accentBdr}`,
                      borderRadius: 4, color: isActive ? c.accent : c.accentLbl,
                      fontFamily: "monospace", fontSize: 9, letterSpacing: 1,
                      padding: "4px 10px", cursor: "pointer",
                      textTransform: "uppercase", transition: "all 150ms ease",
                    }}
                  >{m === "arc" ? "🛤 ARC" : "📡 LIVE"}</button>
                );
              })}
            </div>
          </div>
        )}

        {/* Position live */}
        {flightPosition && (
          <div style={{ background: c.accentDim, border: `1px solid ${isStale ? c.warnBdr : c.accentBdr}`, borderRadius: 8, padding: "8px 12px" }}>
            <div style={{ color: c.accentLbl, fontFamily: "monospace", fontSize: 8, letterSpacing: 2, marginBottom: 4 }}>
              POSITION{isStale ? " 🟡 CACHE" : flightPosition.source === "live" ? " 🟢 LIVE" : " ⏳ SIMULÉE"}
            </div>
            <div style={{ color: isStale ? c.warning : c.accent, fontFamily: "monospace", fontSize: 11 }}>
              {flightPosition.lat.toFixed(4)}, {flightPosition.lng.toFixed(4)}
            </div>
            {flightPosition.altitude != null && (
              <div style={{ color: c.faint, fontFamily: "monospace", fontSize: 9, marginTop: 2 }}>
                Alt: {Math.round(flightPosition.altitude)}m
                {flightPosition.speed != null ? ` · ${Math.round(flightPosition.speed)} kt` : ""}
              </div>
            )}
          </div>
        )}

        {/* Position estimée DB */}
        {pos && !flightPosition && (
          <div style={{ background: c.accentDim, border: `1px solid ${c.accentBdr}`, borderRadius: 8, padding: "8px 12px" }}>
            <div style={{ color: c.accentLbl, fontFamily: "monospace", fontSize: 8, letterSpacing: 2, marginBottom: 4 }}>POSITION</div>
            <div style={{ color: c.accent, fontFamily: "monospace", fontSize: 11 }}>{pos.lat.toFixed(4)}, {pos.lng.toFixed(4)}</div>
            <div style={{ color: c.faint, fontFamily: "monospace", fontSize: 9, marginTop: 3 }}>{SOURCE_LABELS[pos.source] ?? pos.source}</div>
          </div>
        )}

        {/* Historique events */}
        {parcel.events.length > 0 && (
          <div>
            <div style={{ color: c.accentLbl, fontFamily: "monospace", fontSize: 9, letterSpacing: 2, marginBottom: 8, fontWeight: "bold" }}>
              HISTORIQUE ({parcel.events.length})
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {parcel.events.map((event, i) => (
                <div key={event.id} style={{ display: "flex", gap: 10, alignItems: "flex-start" }}>
                  <div style={{ display: "flex", flexDirection: "column", alignItems: "center", paddingTop: 3 }}>
                    <div style={{
                      width: 6, height: 6, borderRadius: "50%",
                      background: i === 0 ? statusColor : c.timelineDot,
                      flexShrink: 0,
                      boxShadow: i === 0 && isDark ? `0 0 5px ${statusColor}` : "none",
                    }} />
                    {i < parcel.events.length - 1 && (
                      <div style={{ width: 1, flex: 1, minHeight: 12, background: c.timelineLine, margin: "2px 0" }} />
                    )}
                  </div>
                  <div style={{ flex: 1, paddingBottom: 6 }}>
                    <div style={{ color: c.eventDesc, fontFamily: "monospace", fontSize: 10, lineHeight: 1.4 }}>
                      {event.description || event.status}
                    </div>
                    <div style={{ display: "flex", gap: 6, marginTop: 3, flexWrap: "wrap" }}>
                      {event.location && (
                        <span style={{ color: c.eventLoc, fontFamily: "monospace", fontSize: 9 }}>📍 {event.location}</span>
                      )}
                      <span style={{ color: c.eventDate, fontFamily: "monospace", fontSize: 9 }}>
                        {new Date(event.timestamp).toLocaleDateString("fr-FR", { day: "2-digit", month: "short", year: "numeric" })}
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
          <div style={{ color: c.faint, fontFamily: "monospace", fontSize: 9, textAlign: "right" }}>
            Sync : {new Date(parcel.last_synced_at).toLocaleString("fr-FR")}
          </div>
        )}

        {/* Supprimer */}
        <div style={{ borderTop: `1px solid ${c.border}`, paddingTop: 12, marginTop: 4 }}>
          {!confirmDelete ? (
            <button
              onClick={() => setConfirmDelete(true)}
              style={{
                width: "100%",
                background: c.dangerBg,
                border: `1px solid ${c.dangerBdr}`,
                borderRadius: 8, color: c.danger,
                fontFamily: "monospace", fontSize: 11,
                padding: "9px 0", cursor: "pointer",
                transition: "all 0.15s",
                display: "flex", alignItems: "center", justifyContent: "center", gap: 6,
              }}
              onMouseEnter={e => (e.currentTarget.style.background = c.dangerHov)}
              onMouseLeave={e => (e.currentTarget.style.background = c.dangerBg)}
            >
              🗑 Supprimer ce colis
            </button>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              <p style={{ color: c.danger, fontFamily: "monospace", fontSize: 10, margin: 0, textAlign: "center" }}>
                Confirmer la suppression ?
              </p>
              <div style={{ display: "flex", gap: 8 }}>
                <button
                  onClick={() => { onDelete(parcel.id); onClose(); }}
                  style={{
                    flex: 1, background: c.dangerBg,
                    border: `1px solid ${c.dangerBdr}`,
                    borderRadius: 6, color: c.danger,
                    fontFamily: "monospace", fontSize: 11,
                    padding: "8px 0", cursor: "pointer",
                  }}
                >Oui, supprimer</button>
                <button
                  onClick={() => setConfirmDelete(false)}
                  style={{
                    flex: 1, background: c.card,
                    border: `1px solid ${c.cardBdr}`,
                    borderRadius: 6, color: c.muted,
                    fontFamily: "monospace", fontSize: 11,
                    padding: "8px 0", cursor: "pointer",
                  }}
                >Annuler</button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
