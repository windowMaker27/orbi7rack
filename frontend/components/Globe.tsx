"use client";

import { useEffect, useRef } from "react";
import * as THREE from "three";
import { EffectComposer, EffectPass, RenderPass, BloomEffect } from "postprocessing";
import type { Parcel } from "@/hooks/useParcels";
import type { FlightPositionMap, PositionModeMap } from "@/hooks/useFlightPositions";

interface GlobeProps {
  parcels: Parcel[];
  globeRef: React.MutableRefObject<any>;
  flightPositions?: FlightPositionMap;
  positionMode?: PositionModeMap;
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

const ARC_ALTITUDE = 0.25;
const LERP_POS     = 0.018;
const LERP_HDG     = 0.06;

function getCentroid(code: string): [number, number] | null {
  return ISO2_CENTROIDS[code?.toUpperCase()] ?? null;
}

function slerpLatLng(
  lat1: number, lng1: number,
  lat2: number, lng2: number,
  t: number
): [number, number] {
  const toRad = (d: number) => d * Math.PI / 180;
  const toDeg = (r: number) => r * 180 / Math.PI;
  const f1 = toRad(lat1), l1 = toRad(lng1);
  const f2 = toRad(lat2), l2 = toRad(lng2);
  const x1 = Math.cos(f1)*Math.cos(l1), y1 = Math.cos(f1)*Math.sin(l1), z1 = Math.sin(f1);
  const x2 = Math.cos(f2)*Math.cos(l2), y2 = Math.cos(f2)*Math.sin(l2), z2 = Math.sin(f2);
  const dot = Math.min(1, x1*x2 + y1*y2 + z1*z2);
  const omega = Math.acos(dot);
  if (omega < 1e-10) return [lat1, lng1];
  const s = Math.sin(omega);
  const a = Math.sin((1-t)*omega)/s, b = Math.sin(t*omega)/s;
  return [
    toDeg(Math.atan2(a*z1+b*z2, Math.sqrt((a*x1+b*x2)**2 + (a*y1+b*y2)**2))),
    toDeg(Math.atan2(a*y1+b*y2, a*x1+b*x2)),
  ];
}

function makeIconTexture(emoji: string): THREE.Texture {
  const size = 128;
  const canvas = document.createElement("canvas");
  canvas.width = size; canvas.height = size;
  const ctx = canvas.getContext("2d")!;
  ctx.font = `${size * 0.7}px serif`;
  ctx.textAlign = "center"; ctx.textBaseline = "middle";
  ctx.fillText(emoji, size/2, size/2);
  return new THREE.CanvasTexture(canvas);
}

function buildArcs(parcels: Parcel[]) {
  return parcels
    .filter(p => p.status !== "delivered" && p.status !== "expired")
    .map(p => {
      const origin = getCentroid(p.origin_country);
      const dest   = p.estimated_position;
      if (!origin || !dest) return null;
      return {
        startLat: origin[0], startLng: origin[1],
        endLat: dest.lat, endLng: dest.lng,
        color: STATUS_COLORS[p.status] ?? "#ffffff",
        label: p.tracking_number,
      };
    }).filter(Boolean);
}

function buildRings(parcels: Parcel[]) {
  return parcels
    .filter(p => p.status === "in_transit" || p.status === "out_for_delivery")
    .map(p => {
      const pos = p.estimated_position;
      if (!pos) return null;
      return { lat: pos.lat, lng: pos.lng, color: STATUS_COLORS[p.status] ?? "#fff" };
    }).filter(Boolean);
}

function buildPoints(parcels: Parcel[]) {
  return parcels
    .map(p => {
      const pos = p.estimated_position;
      if (!pos) return null;
      return {
        lat: pos.lat, lng: pos.lng,
        label: p.tracking_number, status: p.status,
        description: p.description,
        color: STATUS_COLORS[p.status] ?? "#ffffff",
        altitude: 0.02, radius: 0.4,
      };
    }).filter(Boolean);
}

function buildTransportArcs(parcels: Parcel[]) {
  return parcels
    .filter(p => p.status === "in_transit" || p.status === "out_for_delivery")
    .map(p => {
      const origin = getCentroid(p.origin_country);
      const dest   = p.estimated_position;
      if (!origin || !dest) return null;

      const emoji = p.status === "out_for_delivery" ? "🚚" : "✈️";

      return {
        id: p.id,
        startLat: origin[0], startLng: origin[1],
        endLat: dest.lat,   endLng: dest.lng,
        color: STATUS_COLORS[p.status] ?? "#fff",
        emoji,
        _curLat: null as number | null,
        _curLng: null as number | null,
        _curAlt: null as number | null,
        _curHdg: null as number | null,
      };
    }).filter(Boolean);
}

function applyData(globe: any, parcels: Parcel[]) {
  globe
    .pointsData(buildPoints(parcels))
    .pointLat((d: any) => d.lat)
    .pointLng((d: any) => d.lng)
    .pointColor((d: any) => d.color)
    .pointAltitude((d: any) => d.altitude)
    .pointRadius((d: any) => d.radius)
    .pointLabel((d: any) => `
      <div style="background:rgba(10,0,0,0.85);border:1px solid rgba(255,68,0,0.4);border-radius:8px;padding:10px 14px;font-family:monospace;font-size:12px;color:#fff;min-width:180px;">
        <div style="color:#ff6600;letter-spacing:2px;font-size:11px;margin-bottom:6px">${d.label}</div>
        <div style="color:${d.color};margin-bottom:4px">● ${d.status}</div>
        ${d.description ? `<div style="color:#ffffff88;font-size:10px">${d.description}</div>` : ""}
      </div>
    `);

  globe
    .arcsData(buildArcs(parcels))
    .arcStartLat((d: any) => d.startLat)
    .arcStartLng((d: any) => d.startLng)
    .arcEndLat((d: any) => d.endLat)
    .arcEndLng((d: any) => d.endLng)
    .arcColor((d: any) => [d.color, `${d.color}22`])
    .arcAltitude(ARC_ALTITUDE)
    .arcStroke(0.5)
    .arcDashLength(0.4)
    .arcDashGap(0.2)
    .arcDashAnimateTime(2500)
    .arcLabel((d: any) => `<div style="font-family:monospace;font-size:11px;color:${d.color};background:rgba(10,0,0,0.8);padding:6px 10px;border-radius:6px">${d.label}</div>`);

  globe
    .ringsData(buildRings(parcels))
    .ringLat((d: any) => d.lat)
    .ringLng((d: any) => d.lng)
    .ringColor((d: any) => (t: number) => `${d.color}${Math.round((1-t)*255).toString(16).padStart(2,"0")}`)
    .ringMaxRadius(3)
    .ringPropagationSpeed(2)
    .ringRepeatPeriod(800);
}

function setupTransportSprites(
  scene: THREE.Scene,
  transportArcs: any[]
): { sprite: THREE.Sprite; arc: any }[] {
  return transportArcs.map(arc => {
    const texture  = makeIconTexture(arc.emoji);
    const material = new THREE.SpriteMaterial({ map: texture, depthTest: false, rotation: 0 });
    const sprite   = new THREE.Sprite(material);
    sprite.scale.set(8, 8, 1);
    scene.add(sprite);
    return { sprite, arc };
  });
}

function lerpAngle(current: number, target: number, t: number): number {
  const diff = ((target - current) % 360 + 540) % 360 - 180;
  return current + diff * t;
}

export default function Globe({ parcels, globeRef, flightPositions = {}, positionMode = {} }: GlobeProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const composerRef  = useRef<EffectComposer | null>(null);
  const frameRef     = useRef<number>(0);
  const pendingRef   = useRef<Parcel[]>(parcels);
  const spritesRef   = useRef<{ sprite: THREE.Sprite; arc: any }[]>([]);
  const sceneRef     = useRef<THREE.Scene | null>(null);
  const flightPosRef = useRef<FlightPositionMap>(flightPositions);
  const positionModeRef = useRef<PositionModeMap>(positionMode);

  useEffect(() => {
    flightPosRef.current = flightPositions;
  }, [flightPositions]);

  useEffect(() => {
    positionModeRef.current = positionMode;
  }, [positionMode]);

  useEffect(() => {
    pendingRef.current = parcels;
    if (!globeRef.current) return;
    applyData(globeRef.current, parcels);
    if (sceneRef.current) {
      spritesRef.current.forEach(({ sprite }) => sceneRef.current!.remove(sprite));
      spritesRef.current = setupTransportSprites(
        sceneRef.current,
        buildTransportArcs(parcels) as any[]
      );
    }
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
        .globeMaterial(new THREE.MeshPhongMaterial({
          color: new THREE.Color("#0d0000"),
          emissive: new THREE.Color("#1a0000"),
          transparent: true, opacity: 0.95,
        }))
        .hexPolygonsData(countries.features)
        .hexPolygonResolution(3)
        .hexPolygonMargin(0.3)
        .hexPolygonColor(() => {
          const c = ["#ff4400","#ff6600","#ff8800","#ffaa00","#ffcc00"];
          return c[Math.floor(Math.random()*c.length)];
        })
        .hexPolygonAltitude(0.01)
        .pointsData([]).arcsData([]).ringsData([]);

      const scene = globe.scene() as THREE.Scene;
      sceneRef.current = scene;

      scene.add(new THREE.AmbientLight(0xff4400, 0.4));
      const dir = new THREE.DirectionalLight(0xff8800, 1.2);
      dir.position.set(1,1,1); scene.add(dir);

      globe.controls().autoRotate      = true;
      globe.controls().autoRotateSpeed = 0.6;

      setTimeout(() => {
        scene.traverse((obj: any) => {
          if (obj.isLine || obj.isLineSegments) {
            obj.material = new THREE.LineBasicMaterial({
              color: new THREE.Color("#ff2200"), transparent: true, opacity: 0.3,
            });
          }
        });
      }, 500);

      globeRef.current = globe;
      applyData(globe, pendingRef.current);
      spritesRef.current = setupTransportSprites(
        scene,
        buildTransportArcs(pendingRef.current) as any[]
      );

      const renderer = globe.renderer() as THREE.WebGLRenderer;
      const camera   = globe.camera() as THREE.Camera;

      const composer = new EffectComposer(renderer);
      composer.addPass(new RenderPass(scene, camera));
      composer.addPass(new EffectPass(camera, new BloomEffect({
        intensity: 1.8, luminanceThreshold: 0.1,
        luminanceSmoothing: 0.4, mipmapBlur: true,
      })));
      composerRef.current = composer;

      const animate = () => {
        frameRef.current = requestAnimationFrame(animate);
        globe.controls().update();

        spritesRef.current.forEach(({ sprite, arc }) => {
          if (!arc) return;

          const livePos = flightPosRef.current[arc.id];
          const mode    = positionModeRef.current[arc.id] ?? (livePos?.source === "live" ? "live" : "arc");

          let targetLat: number;
          let targetLng: number;
          let targetAlt: number;
          let targetHdg: number | null = null;

          if (livePos?.lat != null && livePos?.lng != null) {
            const progress = livePos.progress ?? 0.5;

            if (mode === "live") {
              // Coords directes depuis OpenSky/FR24
              targetLat = livePos.lat;
              targetLng = livePos.lng;
              targetAlt = Math.min(ARC_ALTITUDE, ((livePos.altitude ?? 10000) / 12000) * ARC_ALTITUDE);
            } else {
              // Mode arc : position interpolée sur la géodésique origin→destination
              const origin = livePos.origin ?? { lat: arc.startLat, lng: arc.startLng };
              const dest   = livePos.destination ?? { lat: arc.endLat,   lng: arc.endLng };
              [targetLat, targetLng] = slerpLatLng(
                origin.lat, origin.lng,
                dest.lat,   dest.lng,
                progress
              );
              targetAlt = Math.sin(progress * Math.PI) * ARC_ALTITUDE;
            }

            targetHdg = livePos.heading ?? null;
          } else {
            // Pas encore de réponse API : attente au milieu de l'arc
            [targetLat, targetLng] = slerpLatLng(
              arc.startLat, arc.startLng,
              arc.endLat,   arc.endLng,
              0.5
            );
            targetAlt = Math.sin(0.5 * Math.PI) * ARC_ALTITUDE;
          }

          // Initialisation au 1er frame
          if (arc._curLat === null) {
            arc._curLat = targetLat;
            arc._curLng = targetLng;
            arc._curAlt = targetAlt;
            arc._curHdg = targetHdg ?? 0;
          }

          // Lerp position
          arc._curLat += (targetLat - arc._curLat) * LERP_POS;
          arc._curLng += (targetLng - arc._curLng) * LERP_POS;
          arc._curAlt += (targetAlt - arc._curAlt) * LERP_POS;

          // Lerp heading
          if (targetHdg !== null) {
            arc._curHdg = lerpAngle(arc._curHdg!, targetHdg, LERP_HDG);
          }

          const coords = globe.getCoords(arc._curLat, arc._curLng, arc._curAlt);
          sprite.position.set(coords.x, coords.y, coords.z);
          (sprite.material as THREE.SpriteMaterial).rotation =
            -(arc._curHdg! * Math.PI) / 180;
        });

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
    <div ref={containerRef} style={{ width: "100%", height: "100vh", background: "#0a0000" }} />
  );
}
