"use client";

import { useState } from "react";
import type { Parcel } from "@/hooks/useParcels";
import type { Theme } from "@/context/ThemeContext";
import AddParcelModal from "@/components/AddParcelModal";

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
}

export default function Sidebar({ parcels, loading, onSelectParcel, onParcelAdded, onDeleteParcel, theme }: SidebarProps) {
  const [open, setOpen] = useState(true);
  const [selected, setSelected] = useState<number | null>(null);
  const [showModal, setShowModal] = useState(false);
  const [hoveredId, setHoveredId] = useState<number | null>(null);

  const isDark = theme === "dark";
  const STATUS_COLORS = isDark ? STATUS_COLORS_DARK : STATUS_COLORS_LIGHT;

  const c = {
    bg:        isDark ? "rgba(10,0,0,0.75)"       : "rgba(240,237,232,0.88)",
    border:    isDark ? "rgba(255,68,0,0.2)"       : "rgba(0,102,204,0.2)",
    accent:    isDark ? "#ff6600"                  : "#0066cc",
    accentBg:  isDark ? "rgba(255,68,0,0.15)"      : "rgba(0,102,204,0.1)",
    accentHov: isDark ? "rgba(255,68,0,0.3)"       : "rgba(0,102,204,0.2)",
    selBg:     isDark ? "rgba(255,68,0,0.12)"      : "rgba(0,102,204,0.08)",
    hovBg:     isDark ? "rgba(255,68,0,0.07)"      : "rgba(0,102,204,0.04)",
    text:      isDark ? "#ffffff"                  : "#1a1a2e",
    muted:     isDark ? "rgba(255,255,255,0.35)"   : "rgba(26,26,46,0.5)",
    danger:    isDark ? "#ff4444"                  : "#cc2200",
    dangerBg:  isDark ? "rgba(255,68,68,0.15)"     : "rgba(204,34,0,0.08)",
    toggle:    isDark ? "rgba(10,0,0,0.75)"        : "rgba(240,237,232,0.88)",
  };

  const handleSelect = (parcel: Parcel) => {
    setSelected(parcel.id);
    onSelectParcel(parcel);
  };

  return (
    <>
      <div style={{
        position: "fixed", top: 0, left: 0,
        height: "100vh", zIndex: 100,
        display: "flex", alignItems: "stretch",
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
            width: 300, height: "100%",
            background: c.bg,
            backdropFilter: "blur(16px)",
            WebkitBackdropFilter: "blur(16px)",
            borderRight: `1px solid ${c.border}`,
            display: "flex", flexDirection: "column",
            padding: "24px 0",
          }}>
            {/* Header */}
            <div style={{
              display: "flex", justifyContent: "space-between", alignItems: "center",
              padding: "0 20px 16px",
              borderBottom: `1px solid ${c.border}`,
            }}>
              <h2 style={{
                color: c.accent, fontFamily: "monospace",
                fontSize: 13, letterSpacing: 3,
                textTransform: "uppercase", margin: 0,
              }}>
                Colis ({parcels.length})
              </h2>
              <button
                onClick={() => setShowModal(true)}
                title="Ajouter un colis"
                style={{
                  background: c.accentBg,
                  border: `1px solid ${c.border}`,
                  borderRadius: 6, color: c.accent,
                  cursor: "pointer", width: 28, height: 28,
                  display: "flex", alignItems: "center", justifyContent: "center",
                  fontSize: 18, lineHeight: 1, transition: "background 0.2s",
                }}
                onMouseEnter={e => (e.currentTarget.style.background = c.accentHov)}
                onMouseLeave={e => (e.currentTarget.style.background = c.accentBg)}
              >+</button>
            </div>

            {/* Liste */}
            <div style={{ flex: 1, overflowY: "auto", padding: "8px 0" }}>
              {loading && (
                <p style={{ color: c.muted, fontFamily: "monospace", fontSize: 12, padding: "16px 20px" }}>
                  Chargement...
                </p>
              )}
              {!loading && parcels.length === 0 && (
                <div style={{ padding: "24px 20px", textAlign: "center" }}>
                  <p style={{ color: c.muted, fontFamily: "monospace", fontSize: 12, marginBottom: 12 }}>
                    Aucun colis suivi
                  </p>
                  <button
                    onClick={() => setShowModal(true)}
                    style={{
                      background: c.accentBg, border: `1px solid ${c.border}`,
                      borderRadius: 6, color: c.accent, cursor: "pointer",
                      padding: "8px 16px", fontFamily: "monospace", fontSize: 12,
                    }}
                  >+ Ajouter un colis</button>
                </div>
              )}

              {parcels.map(parcel => (
                <div
                  key={parcel.id}
                  style={{ position: "relative" }}
                  onMouseEnter={() => setHoveredId(parcel.id)}
                  onMouseLeave={() => setHoveredId(null)}
                >
                  <button
                    onClick={() => handleSelect(parcel)}
                    style={{
                      width: "100%",
                      background: selected === parcel.id ? c.selBg : hoveredId === parcel.id ? c.hovBg : "transparent",
                      border: "none",
                      borderLeft: `3px solid ${selected === parcel.id ? STATUS_COLORS[parcel.status] ?? c.accent : "transparent"}`,
                      padding: "12px 40px 12px 20px",
                      cursor: "pointer", textAlign: "left",
                      transition: "background 0.2s",
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                      <span style={{
                        width: 8, height: 8, borderRadius: "50%",
                        background: STATUS_COLORS[parcel.status] ?? c.accent,
                        flexShrink: 0,
                        boxShadow: isDark ? `0 0 6px ${STATUS_COLORS[parcel.status] ?? c.accent}` : "none",
                      }} />
                      <span style={{
                        color: c.text, fontFamily: "monospace",
                        fontSize: 12, fontWeight: "bold",
                        overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
                      }}>
                        {parcel.tracking_number}
                      </span>
                    </div>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <span style={{ color: STATUS_COLORS[parcel.status] ?? c.muted, fontFamily: "monospace", fontSize: 11 }}>
                        {STATUS_LABELS[parcel.status] ?? parcel.status}
                      </span>
                      {parcel.description && (
                        <span style={{ color: c.muted, fontFamily: "monospace", fontSize: 10 }}>
                          {parcel.description.slice(0, 16)}
                        </span>
                      )}
                    </div>
                  </button>

                  {/* Bouton supprimer — visible au hover */}
                  {hoveredId === parcel.id && (
                    <button
                      onClick={e => { e.stopPropagation(); onDeleteParcel(parcel.id); }}
                      title="Supprimer ce colis"
                      style={{
                        position: "absolute", right: 10, top: "50%",
                        transform: "translateY(-50%)",
                        background: c.dangerBg,
                        border: `1px solid ${isDark ? "rgba(255,68,68,0.3)" : "rgba(204,34,0,0.2)"}`,
                        borderRadius: 5,
                        color: c.danger,
                        cursor: "pointer",
                        width: 24, height: 24,
                        display: "flex", alignItems: "center", justifyContent: "center",
                        fontSize: 12, transition: "all 0.15s",
                      }}
                    >🗑</button>
                  )}
                </div>
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
            background: c.toggle,
            backdropFilter: "blur(16px)",
            border: `1px solid ${c.border}`,
            borderLeft: "none",
            borderRadius: "0 6px 6px 0",
            color: c.accent,
            cursor: "pointer",
            padding: "12px 6px",
            fontFamily: "monospace",
            fontSize: 14, lineHeight: 1,
            transition: "all 0.2s",
          }}
          title={open ? "Fermer" : "Ouvrir"}
        >{open ? "◀" : "▶"}</button>
      </div>

      {showModal && (
        <AddParcelModal
          onClose={() => setShowModal(false)}
          onAdded={parcel => { onParcelAdded(parcel); setSelected(parcel.id); }}
        />
      )}
    </>
  );
}
