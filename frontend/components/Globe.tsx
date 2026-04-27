"use client";

import { useEffect, useRef } from "react";
import * as THREE from "three";
import { EffectComposer, EffectPass, RenderPass, BloomEffect } from "postprocessing";
import type { Parcel } from "@/hooks/useParcels";
import type { FlightPositionMap, PositionModeMap } from "@/hooks/useFlightPositions";
import type { Theme } from "@/context/ThemeContext";

interface GlobeProps {
  parcels: Parcel[];
  globeRef: React.MutableRefObject<any>;
  flightPositions?: FlightPositionMap;
  positionMode?: PositionModeMap;
  theme?: Theme;
}

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
  in_transit: "#0055aa",
  out_for_delivery: "#007a44",
  delivered: "#2a7a00",
  exception: "#cc2200",
  expired: "#888888",
};

const ISO2_CENTROIDS: Record<string, [number, number]> = {
  AF:[33.93,67.71],AL:[41.15,20.17],DZ:[28.03,1.65],AR:[-38.41,-63.61],AT:[47.51,14.55],
  AU:[-25.27,133.77],BE:[50.50,4.46],BR:[-14.23,-51.92],CA:[56.13,-106.34],CH:[46.81,8.22],
  CL:[-35.67,-71.54],CN:[35.86,104.19],CO:[4.57,-74.29],CZ:[49.81,15.47],DE:[51.16,10.45],
  DK:[56.26,9.50],EG:[26.82,30.80],ES:[40.46,-3.74],FI:[61.92,25.74],FR:[46.22,2.21],
  GB:[55.37,-3.43],GR:[39.07,21.82],HK:[22.39,114.10],HR:[45.10,15.20],HU:[47.16,19.50],
  ID:[-0.78,113.92],IN:[20.59,78.96],IT:[41.87,12.56],JP:[36.20,138.25],KR:[35.90,127.76],
  MA:[31.79,-7.09],MX:[23.63,-102.55],MY:[4.21,101.97],NL:[52.13,5.29],NO:[60.47,8.46],
  NZ:[-40.90,174.88],PH:[12.87,121.77],PK:[30.37,69.34],PL:[51.91,19.14],PT:[39.39,-8.22],
  RO:[45.94,24.96],RU:[61.52,105.31],SA:[23.88,45.07],SE:[60.12,18.64],SG:[1.35,103.81],
  TH:[15.87,100.99],TR:[38.96,35.24],TW:[23.69,120.96],UA:[48.37,31.16],US:[37.09,-95.71],
  VN:[14.05,108.27],ZA:[-28.47,24.67],
};

const ARC_ALTITUDE = 0.25;
const LERP_POS     = 0.018;
const LERP_HDG     = 0.06;

const HEX_PALETTE_DARK = ["#ff4400","#ff6600","#ff8800","#ffaa00","#cc3300","#ff5500","#dd7700","#ee4400"];

/**
 * Couleur satellite light basée sur la latitude absolue du centroïde du feature.
 * Simule une répartition biome naturelle sans base de données externe :
 *  0–15°  → forêt tropicale dense (vert profond)
 * 15–22°  → savane verte
 * 22–30°  → savane aride / brousse (ocre chaud)
 * 30–37°  → semi-aride / méditerranéen (beige-marron)
 * 37–45°  → tempéré / prairie (vert moyen)
 * 45–55°  → bocage tempéré (vert soutenu)
 * 55–65°  → boréal / taïga (vert sombre)
 * 65–75°  → toundra (vert-gris pâle)
 * 75–90°  → polaire / glace (beige très clair)
 */
function latitudeBiomeColor(lat: number): string {
  const a = Math.abs(lat);
  if (a < 15)  return "#4a7c3f"; // forêt tropicale
  if (a < 22)  return "#7ab648"; // savane verte
  if (a < 30)  return "#c8a84b"; // savane aride / brousse
  if (a < 37)  return "#b89060"; // semi-aride / méditerranéen
  if (a < 45)  return "#8ab55a"; // tempéré / prairie
  if (a < 55)  return "#6a9e48"; // bocage tempéré
  if (a < 65)  return "#4d7a38"; // boréal / taïga
  if (a < 75)  return "#7a9e6a"; // toundra
  return "#c8d4b8";              // polaire / glace
}

/**
 * Calcule la latitude moyenne du centroïde d'un feature GeoJSON.
 * Utilise le plus grand anneau du polygone (ou MultiPolygon).
 */
function featureCentroidLat(feature: any): number {
  try {
    const geo = feature.geometry;
    let coords: number[][];
    if (geo.type === "Polygon") {
      coords = geo.coordinates[0];
    } else if (geo.type === "MultiPolygon") {
      coords = geo.coordinates
        .map((p: number[][][]) => p[0])
        .reduce((a: number[][], b: number[][]) => b.length > a.length ? b : a);
    } else {
      return 0;
    }
    const sum = coords.reduce((acc: number, c: number[]) => acc + c[1], 0);
    return sum / coords.length;
  } catch {
    return 0;
  }
}

function stableHexColor(feature: any, isDark: boolean): string {
  if (isDark) {
    return HEX_PALETTE_DARK[(feature.__hexIdx ?? 0) % HEX_PALETTE_DARK.length];
  }
  // Mode light : couleur basée sur la latitude du centroïde (pré-calculée à l'init)
  const lat = feature.__centroidLat ?? featureCentroidLat(feature);
  return latitudeBiomeColor(lat);
}

function getCentroid(code: string): [number, number] | null {
  return ISO2_CENTROIDS[code?.toUpperCase()] ?? null;
}

function slerpLatLng(lat1:number,lng1:number,lat2:number,lng2:number,t:number):[number,number]{
  const toRad=(d:number)=>d*Math.PI/180;
  const toDeg=(r:number)=>r*180/Math.PI;
  const f1=toRad(lat1),l1=toRad(lng1),f2=toRad(lat2),l2=toRad(lng2);
  const x1=Math.cos(f1)*Math.cos(l1),y1=Math.cos(f1)*Math.sin(l1),z1=Math.sin(f1);
  const x2=Math.cos(f2)*Math.cos(l2),y2=Math.cos(f2)*Math.sin(l2),z2=Math.sin(f2);
  const dot=Math.min(1,x1*x2+y1*y2+z1*z2);
  const omega=Math.acos(dot);
  if(omega<1e-10)return[lat1,lng1];
  const s=Math.sin(omega);
  const a=Math.sin((1-t)*omega)/s,b=Math.sin(t*omega)/s;
  return[
    toDeg(Math.atan2(a*z1+b*z2,Math.sqrt((a*x1+b*x2)**2+(a*y1+b*y2)**2))),
    toDeg(Math.atan2(a*y1+b*y2,a*x1+b*x2)),
  ];
}

function makeIconTexture(emoji:string):THREE.Texture{
  const size=128;
  const canvas=document.createElement("canvas");
  canvas.width=size;canvas.height=size;
  const ctx=canvas.getContext("2d")!;
  ctx.font=`${size*0.7}px serif`;
  ctx.textAlign="center";ctx.textBaseline="middle";
  ctx.fillText(emoji,size/2,size/2);
  return new THREE.CanvasTexture(canvas);
}

function lerpAngle(current:number,target:number,t:number):number{
  const diff=((target-current)%360+540)%360-180;
  return current+diff*t;
}

function resolveCurrentPosition(
  p: Parcel,
  flightPos: FlightPositionMap,
  isDark: boolean,
): { lat: number; lng: number } | null {
  const fp = flightPos[p.id];
  if (fp) {
    if (fp.source === "live" && !fp.stale) return { lat: fp.lat, lng: fp.lng };
    if (fp.origin && fp.destination && fp.progress != null) {
      const progress = Math.max(0.05, Math.min(0.95, fp.progress));
      const [lat, lng] = slerpLatLng(fp.origin.lat, fp.origin.lng, fp.destination.lat, fp.destination.lng, progress);
      return { lat, lng };
    }
    if (fp.lat != null && fp.lng != null) return { lat: fp.lat, lng: fp.lng };
  }
  return p.estimated_position ?? null;
}

function buildData(parcels: Parcel[], isDark: boolean, flightPositions: FlightPositionMap = {}) {
  const SC = isDark ? STATUS_COLORS_DARK : STATUS_COLORS_LIGHT;

  const points = parcels.map(p => {
    const pos = resolveCurrentPosition(p, flightPositions, isDark);
    if (!pos) return null;
    return { lat: pos.lat, lng: pos.lng, label: p.tracking_number, status: p.status, description: p.description, color: SC[p.status] ?? (isDark ? "#ffffff" : "#1a1a2e"), altitude: 0.02, radius: 0.4 };
  }).filter(Boolean);

  const arcs = parcels
    .filter(p => p.status !== "delivered" && p.status !== "expired")
    .map(p => {
      const origin = getCentroid(p.origin_country);
      const dest = p.estimated_position;
      if (!origin || !dest) return null;
      return { startLat: origin[0], startLng: origin[1], endLat: dest.lat, endLng: dest.lng, color: SC[p.status] ?? "#ffffff", label: p.tracking_number };
    }).filter(Boolean);

  const rings = parcels
    .filter(p => p.status === "in_transit" || p.status === "out_for_delivery")
    .map(p => {
      const pos = resolveCurrentPosition(p, flightPositions, isDark);
      if (!pos) return null;
      return { lat: pos.lat, lng: pos.lng, color: SC[p.status] ?? "#fff" };
    }).filter(Boolean);

  const transport = parcels
    .filter(p => p.status === "in_transit" || p.status === "out_for_delivery")
    .map(p => {
      const origin = getCentroid(p.origin_country);
      const dest = p.estimated_position;
      if (!origin || !dest) return null;
      return {
        id: p.id,
        startLat: origin[0], startLng: origin[1],
        endLat: dest.lat, endLng: dest.lng,
        color: SC[p.status] ?? "#fff",
        emoji: p.status === "out_for_delivery" ? "🚚" : "✈️",
        _curLat: null as number | null, _curLng: null as number | null,
        _curAlt: null as number | null, _curHdg: null as number | null,
      };
    }).filter(Boolean);

  return { points, arcs, rings, transport };
}

function applyData(globe: any, parcels: Parcel[], isDark: boolean, flightPositions: FlightPositionMap = {}) {
  const { points, arcs, rings } = buildData(parcels, isDark, flightPositions);

  globe
    .pointsData(points)
    .pointLat((d: any) => d.lat).pointLng((d: any) => d.lng)
    .pointColor((d: any) => d.color).pointAltitude((d: any) => d.altitude).pointRadius((d: any) => d.radius)
    .pointLabel((d: any) => `
      <div style="background:rgba(10,0,0,0.85);border:1px solid rgba(255,68,0,0.4);border-radius:8px;padding:10px 14px;font-family:monospace;font-size:12px;color:#fff;min-width:180px;">
        <div style="color:#ff6600;letter-spacing:2px;font-size:11px;margin-bottom:6px">${d.label}</div>
        <div style="color:${d.color};margin-bottom:4px">● ${d.status}</div>
        ${d.description ? `<div style="color:#ffffff88;font-size:10px">${d.description}</div>` : ""}
      </div>
    `);

  globe
    .arcsData(arcs)
    .arcStartLat((d: any) => d.startLat).arcStartLng((d: any) => d.startLng)
    .arcEndLat((d: any) => d.endLat).arcEndLng((d: any) => d.endLng)
    .arcColor((d: any) => [d.color, `${d.color}22`])
    .arcAltitude(ARC_ALTITUDE).arcStroke(0.5)
    .arcDashLength(0.4).arcDashGap(0.2).arcDashAnimateTime(2500)
    .arcLabel((d: any) => `<div style="font-family:monospace;font-size:11px;color:${d.color};background:rgba(10,0,0,0.8);padding:6px 10px;border-radius:6px">${d.label}</div>`);

  globe
    .ringsData(rings)
    .ringLat((d: any) => d.lat).ringLng((d: any) => d.lng)
    .ringColor((d: any) => (t: number) => `${d.color}${Math.round((1 - t) * 255).toString(16).padStart(2, "00")}`)
    .ringMaxRadius(3).ringPropagationSpeed(2).ringRepeatPeriod(800);
}

function applyHexColors(globe: any, isDark: boolean) {
  globe.hexPolygonColor((feat: any) => stableHexColor(feat, isDark));
}

const OCEAN_LIGHT = { color: "#1a6fa8", emissive: "#0d4f7a" };
const OCEAN_DARK  = { color: "#0d0000", emissive: "#0a0000" };

function applyTheme(globe: any, scene: THREE.Scene, isDark: boolean) {
  const ocean = isDark ? OCEAN_DARK : OCEAN_LIGHT;
  globe
    .atmosphereColor(isDark ? "#ff6600" : "#4db8ff")
    .globeMaterial(new THREE.MeshPhongMaterial({
      color:    new THREE.Color(ocean.color),
      emissive: new THREE.Color(ocean.emissive),
      transparent: true, opacity: 0.95,
    }));

  const toRemove: THREE.Object3D[] = [];
  scene.traverse((obj: any) => { if (obj.isAmbientLight || obj.isDirectionalLight) toRemove.push(obj); });
  toRemove.forEach(l => scene.remove(l));

  if (isDark) {
    scene.add(new THREE.AmbientLight(0xffffff, 1.0));
    const dir = new THREE.DirectionalLight(0xff9944, 0.8);
    dir.position.set(1, 1, 1); scene.add(dir);
  } else {
    scene.add(new THREE.AmbientLight(0xffffff, 0.8));
    const dir = new THREE.DirectionalLight(0xd4eeff, 1.1);
    dir.position.set(1, 1, 1); scene.add(dir);
  }

  applyHexColors(globe, isDark);
}

function setupSprites(scene: THREE.Scene, transport: any[]): { sprite: THREE.Sprite; arc: any }[] {
  return transport.map(arc => {
    const tex = makeIconTexture(arc.emoji);
    const mat = new THREE.SpriteMaterial({ map: tex, depthTest: false, rotation: 0 });
    const sprite = new THREE.Sprite(mat);
    sprite.scale.set(8, 8, 1);
    scene.add(sprite);
    return { sprite, arc };
  });
}

export default function Globe({ parcels, globeRef, flightPositions = {}, positionMode = {}, theme = "dark" }: GlobeProps) {
  const containerRef    = useRef<HTMLDivElement>(null);
  const composerRef     = useRef<EffectComposer | null>(null);
  const frameRef        = useRef<number>(0);
  const pendingRef      = useRef<Parcel[]>(parcels);
  const spritesRef      = useRef<{ sprite: THREE.Sprite; arc: any }[]>([]);
  const sceneRef        = useRef<THREE.Scene | null>(null);
  const flightPosRef    = useRef<FlightPositionMap>(flightPositions);
  const positionModeRef = useRef<PositionModeMap>(positionMode);
  const themeRef        = useRef<Theme>(theme);
  const spriteStateRef  = useRef<Map<number, { lat: number; lng: number; alt: number; hdg: number }>>(new Map());

  flightPosRef.current    = flightPositions;
  positionModeRef.current = positionMode;
  themeRef.current        = theme;

  useEffect(() => {
    pendingRef.current = parcels;
    if (!globeRef.current) return;
    const isDark = theme === "dark";
    applyData(globeRef.current, parcels, isDark, flightPositions);
    if (sceneRef.current) {
      applyTheme(globeRef.current, sceneRef.current, isDark);
      const prevState = spriteStateRef.current;
      spritesRef.current.forEach(({ sprite }) => sceneRef.current!.remove(sprite));
      const newTransport = buildData(parcels, isDark, flightPositions).transport as any[];
      newTransport.forEach((arc: any) => {
        const saved = prevState.get(arc.id);
        if (saved) { arc._curLat = saved.lat; arc._curLng = saved.lng; arc._curAlt = saved.alt; arc._curHdg = saved.hdg; }
      });
      spritesRef.current = setupSprites(sceneRef.current, newTransport);
    }
    if (composerRef.current) {
      const passes = (composerRef.current as any).passes as any[];
      const effectPass = passes.find((p: any) => p instanceof EffectPass);
      if (effectPass) {
        const bloom = (effectPass as any).effects?.find((e: any) => e instanceof BloomEffect);
        if (bloom) {
          bloom.intensity = isDark ? 1.6 : 0.2;
          bloom.luminancePass.fullscreenMaterial.uniforms.threshold.value = isDark ? 0.3 : 0.5;
        }
      }
    }
  }, [parcels, theme, globeRef, flightPositions]);

  useEffect(() => {
    if (!containerRef.current) return;
    const init = async () => {
      const isDark = themeRef.current === "dark";
      const [{ default: GlobeGL }, countries] = await Promise.all([
        import("globe.gl"),
        fetch("https://raw.githubusercontent.com/holtzy/D3-graph-gallery/master/DATA/world.geojson").then(r => r.json()),
      ]);

      // Pré-calcul du centroïde latitude pour chaque feature (fait une seule fois au chargement)
      countries.features.forEach((f: any, i: number) => {
        f.__hexIdx = i;
        f.__centroidLat = featureCentroidLat(f);
      });

      const ocean = isDark ? OCEAN_DARK : OCEAN_LIGHT;

      const globe = (GlobeGL as any)(
        { animateIn: true, rendererConfig: { antialias: true, alpha: true } }
      )(containerRef.current)
        .width(containerRef.current!.clientWidth)
        .height(containerRef.current!.clientHeight)
        .backgroundColor("rgba(0,0,0,0)")
        .showGraticules(true)
        .atmosphereColor(isDark ? "#ff6600" : "#4db8ff")
        .atmosphereAltitude(0.12)
        .globeMaterial(new THREE.MeshPhongMaterial({
          color:    new THREE.Color(ocean.color),
          emissive: new THREE.Color(ocean.emissive),
          transparent: true, opacity: 0.95,
        }))
        .hexPolygonsData(countries.features)
        .hexPolygonResolution(3)
        .hexPolygonMargin(0.3)
        .hexPolygonColor((feat: any) => stableHexColor(feat, isDark))
        .hexPolygonAltitude(0.01)
        .pointsData([]).arcsData([]).ringsData([]);

      const scene = globe.scene() as THREE.Scene;
      sceneRef.current = scene;

      if (isDark) {
        scene.add(new THREE.AmbientLight(0xffffff, 0.25));
        const dir = new THREE.DirectionalLight(0xff9944, 0.8);
        dir.position.set(1, 1, 1); scene.add(dir);
      } else {
        scene.add(new THREE.AmbientLight(0xffffff, 0.8));
        const dir = new THREE.DirectionalLight(0xd4eeff, 1.1);
        dir.position.set(1, 1, 1); scene.add(dir);
      }

      globe.controls().autoRotate = true;
      globe.controls().autoRotateSpeed = 0.6;

      setTimeout(() => {
        scene.traverse((obj: any) => {
          if (obj.isLine || obj.isLineSegments) {
            if (obj.material) obj.material = new THREE.LineBasicMaterial({
              color: new THREE.Color(isDark ? "#993300" : "#0066bb"),
              transparent: true, opacity: 0.25,
            });
          }
        });
      }, 500);

      globeRef.current = globe;
      applyData(globe, pendingRef.current, isDark, flightPosRef.current);

      const transport = buildData(pendingRef.current, isDark, flightPosRef.current).transport as any[];
      transport.forEach((arc: any) => {
        const [midLat, midLng] = slerpLatLng(arc.startLat, arc.startLng, arc.endLat, arc.endLng, 0.5);
        arc._curLat = midLat; arc._curLng = midLng;
        arc._curAlt = Math.sin(0.5 * Math.PI) * ARC_ALTITUDE;
        arc._curHdg = 0;
      });
      spritesRef.current = setupSprites(scene, transport);

      const renderer = globe.renderer() as THREE.WebGLRenderer;
      const camera = globe.camera() as THREE.Camera;

      const composer = new EffectComposer(renderer);
      composer.addPass(new RenderPass(scene, camera));
      composer.addPass(new EffectPass(camera, new BloomEffect({
        intensity: isDark ? 1.6 : 0.5,
        luminanceThreshold: isDark ? 0.15 : 0.35,
        luminanceSmoothing: 0.4, mipmapBlur: true,
      })));
      composerRef.current = composer;

      const animate = () => {
        frameRef.current = requestAnimationFrame(animate);
        globe.controls().update();

        spritesRef.current.forEach(({ sprite, arc }) => {
          if (!arc) return;
          const livePos = flightPosRef.current[arc.id];
          const mode = positionModeRef.current[arc.id] ?? (livePos?.source === "live" ? "live" : "arc");

          let targetLat: number, targetLng: number, targetAlt: number;
          let targetHdg: number | null = null;

          if (livePos?.lat != null && livePos?.lng != null) {
            const rawProgress = livePos.progress;
            const progress = (rawProgress != null && rawProgress > 0 && rawProgress < 1)
              ? Math.max(0.05, Math.min(0.95, rawProgress)) : 0.5;

            if (mode === "live") {
              targetLat = livePos.lat; targetLng = livePos.lng;
              targetAlt = Math.min(ARC_ALTITUDE, ((livePos.altitude ?? 10000) / 12000) * ARC_ALTITUDE);
            } else {
              const origin = livePos.origin ?? { lat: arc.startLat, lng: arc.startLng };
              const dest = livePos.destination ?? { lat: arc.endLat, lng: arc.endLng };
              [targetLat, targetLng] = slerpLatLng(origin.lat, origin.lng, dest.lat, dest.lng, progress);
              targetAlt = Math.sin(progress * Math.PI) * ARC_ALTITUDE;
            }
            targetHdg = livePos.heading ?? null;
          } else {
            [targetLat, targetLng] = slerpLatLng(arc.startLat, arc.startLng, arc.endLat, arc.endLng, 0.5);
            targetAlt = Math.sin(0.5 * Math.PI) * ARC_ALTITUDE;
          }

          arc._curLat! += (targetLat - arc._curLat!) * LERP_POS;
          arc._curLng! += (targetLng - arc._curLng!) * LERP_POS;
          arc._curAlt! += (targetAlt - arc._curAlt!) * LERP_POS;
          if (targetHdg !== null) arc._curHdg = lerpAngle(arc._curHdg!, targetHdg, LERP_HDG);

          spriteStateRef.current.set(arc.id, { lat: arc._curLat!, lng: arc._curLng!, alt: arc._curAlt!, hdg: arc._curHdg! });

          const coords = globe.getCoords(arc._curLat, arc._curLng, arc._curAlt);
          sprite.position.set(coords.x, coords.y, coords.z);
          (sprite.material as THREE.SpriteMaterial).rotation = -(arc._curHdg! * Math.PI) / 180;
        });

        composer.render();
      };
      animate();
    };

    init();

    const handleResize = () => {
      if (globeRef.current && containerRef.current) {
        globeRef.current.width(containerRef.current.clientWidth).height(containerRef.current.clientHeight);
        composerRef.current?.setSize(containerRef.current.clientWidth, containerRef.current.clientHeight);
      }
    };
    window.addEventListener("resize", handleResize);
    return () => {
      window.removeEventListener("resize", handleResize);
      cancelAnimationFrame(frameRef.current);
    };
  }, [globeRef]);

  const bgColor = theme === "dark" ? "#0a0000" : "#0d4f7a";
  return (
    <div ref={containerRef} style={{ width: "100%", height: "100vh", background: bgColor }} />
  );
}
