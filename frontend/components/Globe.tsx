"use client";

import { useEffect, useRef } from "react";
import * as THREE from "three";
import { EffectComposer, EffectPass, RenderPass, BloomEffect } from "postprocessing";
import type { Parcel } from "@/hooks/useParcels";

interface GlobeProps {
  parcels: Parcel[];
  globeRef: React.MutableRefObject<any>;
}

const STATUS_COLORS: Record<string, string> = {
  pending: "#ffaa00",
  in_transit: "#00cfff",
  out_for_delivery: "#00ff99",
  delivered: "#44ff44",
  exception: "#ff2222",
  expired: "#888888",
};

const ISO2_CENTROIDS: Record<string, [number, number]> = {
  AF: [33.93, 67.71], AL: [41.15, 20.17], DZ: [28.03, 1.65],
  AR: [-38.41, -63.61], AT: [47.51, 14.55], AU: [-25.27, 133.77],
  BE: [50.50, 4.46], BR: [-14.23, -51.92], CA: [56.13, -106.34],
  CH: [46.81, 8.22], CL: [-35.67, -71.54], CN: [35.86, 104.19],
  CO: [4.57, -74.29], CZ: [49.81, 15.47], DE: [51.16, 10.45],
  DK: [56.26, 9.50], EG: [26.82, 30.80], ES: [40.46, -3.74],
  FI: [61.92, 25.74], FR: [46.22, 2.21], GB: [55.37, -3.43],
  GR: [39.07, 21.82], HK: [22.39, 114.10], HR: [45.10, 15.20],
  HU: [47.16, 19.50], ID: [-0.78, 113.92], IN: [20.59, 78.96],
  IT: [41.87, 12.56], JP: [36.20, 138.25], KR: [35.90, 127.76],
  MA: [31.79, -7.09], MX: [23.63, -102.55], MY: [4.21, 101.97],
  NL: [52.13, 5.29], NO: [60.47, 8.46], NZ: [-40.90, 174.88],
  PH: [12.87, 121.77], PK: [30.37, 69.34], PL: [51.91, 19.14],
  PT: [39.39, -8.22], RO: [45.94, 24.96], RU: [61.52, 105.31],
  SA: [23.88, 45.07], SE: [60.12, 18.64], SG: [1.35, 103.81],
  TH: [15.87, 100.99], TR: [38.96, 35.24], TW: [23.69, 120.96],
  UA: [48.37, 31.16], US: [37.09, -95.71], VN: [14.05, 108.27],
  ZA: [-28.47, 24.67],
};

function getCentroid(code: string): [number, number] | null {
  return ISO2_CENTROIDS[code?.toUpperCase()] ?? null;
}

function buildArcs(parcels: Parcel[]) {
  return parcels
    .filter(p => p.status !== "delivered" && p.status !== "expired")
    .map(p => {
      const origin = getCentroid(p.origin_country);
      const dest = p.estimated_position;
      if (!origin || !dest) return null;
      return {
        startLat: origin[0],
        startLng: origin[1],
        endLat: dest.lat,
        endLng: dest.lng,
        color: STATUS_COLORS[p.status] ?? "#ffffff",
        label: p.tracking_number,
        status: p.status,
      };
    })
    .filter(Boolean);
}

// Rings sur la vraie estimated_position du colis
function buildRings(parcels: Parcel[]) {
  return parcels
    .filter(p => p.status === "in_transit" || p.status === "out_for_delivery")
    .map(p => {
      const pos = p.estimated_position;
      if (!pos) return null;
      return {
        lat: pos.lat,
        lng: pos.lng,
        color: STATUS_COLORS[p.status] ?? "#ffffff",
        label: p.tracking_number,
      };
    })
    .filter(Boolean);
}

function buildPoints(parcels: Parcel[]) {
  return parcels
    .map(parcel => {
      const pos = parcel.estimated_position;
      if (!pos) return null;
      return {
        lat: pos.lat,
        lng: pos.lng,
        source: pos.source,
        label: parcel.tracking_number,
        status: parcel.status,
        description: parcel.description,
        color: STATUS_COLORS[parcel.status] ?? "#ffffff",
        altitude: 0.02,
        radius: 0.4,
      };
    })
    .filter(Boolean);
}

function applyData(globe: any, parcels: Parcel[]) {
  const points = buildPoints(parcels);
  const arcs   = buildArcs(parcels);
  const rings  = buildRings(parcels);

  globe
    .pointsData(points)
    .pointLat((d: any) => d.lat)
    .pointLng((d: any) => d.lng)
    .pointColor((d: any) => d.color)
    .pointAltitude((d: any) => d.altitude)
    .pointRadius((d: any) => d.radius)
    .pointLabel((d: any) => `
      <div style="
        background:rgba(10,0,0,0.85);
        border:1px solid rgba(255,68,0,0.4);
        border-radius:8px;
        padding:10px 14px;
        font-family:monospace;
        font-size:12px;
        color:#fff;
        min-width:180px;
      ">
        <div style="color:#ff6600;letter-spacing:2px;font-size:11px;margin-bottom:6px">${d.label}</div>
        <div style="color:${d.color};margin-bottom:4px">● ${d.status}</div>
        ${d.description ? `<div style="color:#ffffff88;font-size:10px">${d.description}</div>` : ""}
      </div>
    `);

  globe
    .arcsData(arcs)
    .arcStartLat((d: any) => d.startLat)
    .arcStartLng((d: any) => d.startLng)
    .arcEndLat((d: any) => d.endLat)
    .arcEndLng((d: any) => d.endLng)
    .arcColor((d: any) => [d.color, `${d.color}22`])
    .arcAltitude(0.25)
    .arcStroke(0.5)
    .arcDashLength(0.4)
    .arcDashGap(0.2)
    .arcDashAnimateTime(2500)
    .arcLabel((d: any) => `<div style="font-family:monospace;font-size:11px;color:${d.color};background:rgba(10,0,0,0.8);padding:6px 10px;border-radius:6px">${d.label}</div>`);

  globe
    .ringsData(rings)
    .ringLat((d: any) => d.lat)
    .ringLng((d: any) => d.lng)
    .ringColor((d: any) => (t: number) => `${d.color}${Math.round((1 - t) * 255).toString(16).padStart(2, "0")}`)
    .ringMaxRadius(3)
    .ringPropagationSpeed(2)
    .ringRepeatPeriod(800);
}

export default function Globe({ parcels, globeRef }: GlobeProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const composerRef  = useRef<EffectComposer | null>(null);
  const frameRef     = useRef<number>(0);
  const pendingRef   = useRef<Parcel[]>(parcels);

  useEffect(() => {
    pendingRef.current = parcels;
    if (!globeRef.current) return;
    applyData(globeRef.current, parcels);
  }, [parcels, globeRef]);

  useEffect(() => {
    if (!containerRef.current) return;

    const init = async () => {
      const [{ default: GlobeGL }, countries] = await Promise.all([
        import("globe.gl"),
        fetch("https://raw.githubusercontent.com/holtzy/D3-graph-gallery/master/DATA/world.geojson").then(r => r.json()),
      ]);

      const globe = (GlobeGL as any)(
        { animateIn: true, rendererConfig: { antialias: true, alpha: true } }
      )(containerRef.current)
        .width(containerRef.current!.clientWidth)
        .height(containerRef.current!.clientHeight)
        .backgroundColor("rgba(0,0,0,0)")
        .showGraticules(true)
        .atmosphereColor("#ff4400")
        .atmosphereAltitude(0.12)
        .globeMaterial(
          new THREE.MeshPhongMaterial({
            color: new THREE.Color("#0d0000"),
            emissive: new THREE.Color("#1a0000"),
            transparent: true,
            opacity: 0.95,
          })
        )
        .hexPolygonsData(countries.features)
        .hexPolygonResolution(3)
        .hexPolygonMargin(0.3)
        .hexPolygonColor(() => {
          const colors = ["#ff4400", "#ff6600", "#ff8800", "#ffaa00", "#ffcc00"];
          return colors[Math.floor(Math.random() * colors.length)];
        })
        .hexPolygonAltitude(0.01)
        .pointsData([])
        .arcsData([])
        .ringsData([]);

      const scene = globe.scene();
      scene.add(new THREE.AmbientLight(0xff4400, 0.4));
      const dirLight = new THREE.DirectionalLight(0xff8800, 1.2);
      dirLight.position.set(1, 1, 1);
      scene.add(dirLight);

      globe.controls().autoRotate      = true;
      globe.controls().autoRotateSpeed = 0.6;

      setTimeout(() => {
        scene.traverse((obj: any) => {
          if (obj.isLine || obj.isLineSegments) {
            obj.material = new THREE.LineBasicMaterial({
              color: new THREE.Color("#ff2200"),
              transparent: true,
              opacity: 0.3,
            });
          }
        });
      }, 500);

      globeRef.current = globe;
      applyData(globe, pendingRef.current);

      const renderer = globe.renderer() as THREE.WebGLRenderer;
      const camera   = globe.camera() as THREE.Camera;

      const composer = new EffectComposer(renderer);
      composer.addPass(new RenderPass(scene, camera));
      composer.addPass(
        new EffectPass(
          camera,
          new BloomEffect({
            intensity: 1.8,
            luminanceThreshold: 0.1,
            luminanceSmoothing: 0.4,
            mipmapBlur: true,
          })
        )
      );
      composerRef.current = composer;

      const animate = () => {
        frameRef.current = requestAnimationFrame(animate);
        globe.controls().update();
        composer.render();
      };
      animate();
    };

    init();

    const handleResize = () => {
      if (globeRef.current && containerRef.current) {
        globeRef.current
          .width(containerRef.current.clientWidth)
          .height(containerRef.current.clientHeight);
        composerRef.current?.setSize(
          containerRef.current.clientWidth,
          containerRef.current.clientHeight
        );
      }
    };
    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      cancelAnimationFrame(frameRef.current);
    };
  }, [globeRef]);

  return (
    <div
      ref={containerRef}
      style={{ width: "100%", height: "100vh", background: "#0a0000" }}
    />
  );
}
