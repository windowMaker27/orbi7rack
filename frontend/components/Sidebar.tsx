"use client";

import { useState } from "react";
import AddParcelModal from "./AddParcelModal";
import type { Parcel } from "@/hooks/useParcels";
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

interface SidebarProps {
  parcels: Parcel[];
  loading: boolean;
  onSelectParcel: (parcel: Parcel) => void;
  onParcelAdded: (parcel: Parcel) => void;
  onDeleteParcel: (id: number) => void;
  theme: Theme;
  /** Map parcelId → FlightPosition pour afficher le badge stale */
  flightPositions?: Record<number, { stale?: boolean; stale_since?: string | null }>;
}

function staleSince(isoDate?: string | null): string {
  if (!isoDate) return "";
  const diffMs = Date.now() - new Date(isoDate).getTime();
  const diffMin = Math.round(diffMs / 60_000);
  if (diffMin < 1) return "<1 min";
  if (diffMin < 60) return `${diffMin} min`;
  return `${Math.round(diffMin / 60)}h`;
}

export default function Sidebar({
  parcels, loading, onSelectParcel, onParcelAdded, onDeleteParcel, theme, flightPositions = {},
}: SidebarProps) {
  const [showAdd, setShowAdd] = useState(false);
  const isDark = theme === "dark";
  const STATUS_COLORS = isDark ? STATUS_COLORS_DARK : STATUS_COLORS_LIGHT;

  const c = {
    bg:        isDark ? "rgba(10,2,0,0.92)"    : "rgba(240,237,232,0.95)",
    border:    isDark ? "rgba(255,68,0,0.2)"   : "rgba(0,80,160,0.18)",
    accent:    isDark ? "#ff6600"              : "#0066cc",
    accentDim: isDark ? "rgba(255,68,0,0.06)" : "rgba(0,102,204,0.05)",
    accentBdr: isDark ? "rgba(255,68,0,0.12)" : "rgba(0,80,160,0.15)",
    accentLbl: isDark ? "rgba(255,68,0,0.5)"  : "rgba(0,80,180,0.65)",
    text:      isDark ? "#ffffff"              : "#0f0f1a",
    muted:     isDark ? "#ffffff88"            : "rgba(15,15,26,0.7)",
    faint:     isDark ? "#ffffff33"            : "rgba(15,15,26,0.4)",
    card:      isDark ? "rgba(255,255,255,0.02)" : "rgba(255,255,255,0.65)",
    cardBdr:   isDark ? "rgba(255,68,0,0.08)" : "rgba(0,80,160,0.15)",
    cardHov:   isDark ? "rgba(255,68,0,0.05)" : "rgba(0,80,160,0.04)",
    warning:   isDark ? "#ffaa00"              : "#b86e00",
    warnBg:    isDark ? "rgba(255,170,0,0.08)" : "rgba(184,110,0,0.06)",
    warnBdr:   isDark ? "rgba(255,170,0,0.22)" : "rgba(184,110,0,0.18)",
  };

  return (
    <>
      <div style={{
        position: "fixed", top: 0, left: 0, bottom: 0,
        width: 260, zIndex: 100,
        background: c.bg,
        backdropFilter: "blur(16px)",
        WebkitBackdropFilter: "blur(16px)",
        borderRight: `1px solid ${c.border}`,
        display: "flex", flexDirection: "column",
        overflow: "hidden",
      }}>
        {/* Logo / titre */}
        <div style={{
          padding: "18px 16px 12px",
          borderBottom: `1px solid ${c.border}`,
          display: "flex", alignItems: "center", gap: 10,
        }}>
          <div style={{
            width: 28, height: 28,
            background: c.accent,
            borderRadius: 6,
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: 14,
          }}>📦</div>
          <div>
            <div style={{ color: c.accent, fontFamily: "monospace", fontSize: 12, fontWeight: "bold", letterSpacing: 2 }}>ORBI7RACK</div>
            <div style={{ color: c.accentLbl, fontFamily: "monospace", fontSize: 8, letterSpacing: 1 }}>PARCEL TRACKER</div>
          </div>
        </div>

        {/* Liste */}
        <div style={{ flex: 1, overflowY: "auto", padding: "10px 10px", scrollbarWidth: "thin" }}>
          {loading ? (
            <div style={{ color: c.muted, fontFamily: "monospace", fontSize: 11, textAlign: "center", marginTop: 40 }}>
              Chargement...
            </div>
          ) : parcels.length === 0 ? (
            <div style={{ color: c.faint, fontFamily: "monospace", fontSize: 10, textAlign: "center", marginTop: 40, lineHeight: 1.8 }}>
              Aucun colis suivi.<br/>Ajoutez-en un ci-dessous.
            </div>
          ) : (
            parcels.map(parcel => {
              const statusColor = STATUS_COLORS[parcel.status] ?? (isDark ? "#fff" : "#1a1a2e");
              const fp = flightPositions[parcel.id];
              const isStale = fp?.stale === true;
              const staleAge = isStale ? staleSince(fp?.stale_since) : "";

              return (
                <div
                  key={parcel.id}
                  onClick={() => onSelectParcel(parcel)}
                  style={{
                    background: c.card,
                    border: `1px solid ${isStale ? c.warnBdr : c.cardBdr}`,
                    borderRadius: 8,
                    padding: "9px 12px",
                    marginBottom: 6,
                    cursor: "pointer",
                    transition: "background 150ms ease, border-color 150ms ease",
                  }}
                  onMouseEnter={e => (e.currentTarget.style.background = c.cardHov)}
                  onMouseLeave={e => (e.currentTarget.style.background = c.card)}
                >
                  {/* Ligne 1 : tracking + badge stale */}
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 4 }}>
                    <div style={{ color: c.text, fontFamily: "monospace", fontSize: 10, fontWeight: "bold", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: isStale ? 130 : "100%" }}>
                      {parcel.tracking_number}
                    </div>
                    {isStale && (
                      <span style={{
                        background: c.warnBg,
                        border: `1px solid ${c.warnBdr}`,
                        borderRadius: 20,
                        color: c.warning,
                        fontFamily: "monospace",
                        fontSize: 7,
                        padding: "2px 6px",
                        whiteSpace: "nowrap",
                        letterSpacing: 0.3,
                        flexShrink: 0,
                      }}>
                        🕐 {staleAge}
                      </span>
                    )}
                  </div>

                  {/* Ligne 2 : statut + route */}
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 5 }}>
                      <div style={{
                        width: 5, height: 5, borderRadius: "50%",
                        background: statusColor,
                        boxShadow: isDark ? `0 0 4px ${statusColor}` : "none",
                        flexShrink: 0,
                      }} />
                      <span style={{ color: statusColor, fontFamily: "monospace", fontSize: 9 }}>
                        {STATUS_LABELS[parcel.status] ?? parcel.status}
                      </span>
                    </div>
                    {(parcel.origin_country || parcel.dest_country) && (
                      <span style={{ color: c.faint, fontFamily: "monospace", fontSize: 8 }}>
                        {parcel.origin_country || "?"} → {parcel.dest_country || "?"}
                      </span>
                    )}
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Bouton ajout */}
        <div style={{ padding: "10px 10px", borderTop: `1px solid ${c.border}` }}>
          <button
            onClick={() => setShowAdd(true)}
            style={{
              width: "100%",
              background: c.accentDim,
              border: `1px solid ${c.accentBdr}`,
              borderRadius: 8,
              color: c.accent,
              fontFamily: "monospace",
              fontSize: 11,
              padding: "9px 0",
              cursor: "pointer",
              letterSpacing: 1,
              transition: "all 150ms ease",
            }}
            onMouseEnter={e => (e.currentTarget.style.background = isDark ? "rgba(255,68,0,0.12)" : "rgba(0,102,204,0.1)")}
            onMouseLeave={e => (e.currentTarget.style.background = c.accentDim)}
          >
            + AJOUTER UN COLIS
          </button>
        </div>
      </div>

      {showAdd && (
        <AddParcelModal
          onClose={() => setShowAdd(false)}
          onParcelAdded={(p) => { onParcelAdded(p); setShowAdd(false); }}
          theme={theme}
        />
      )}
    </>
  );
}
