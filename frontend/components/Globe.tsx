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

function applyPoints(globe: any, points: any[]) {
  globe
    .pointsData(points)
    .pointLat((d: any) => d.lat)
    .pointLng((d: any) => d.lng)
    .pointColor((d: any) => d.color)
    .pointAltitude((d: any) => d.altitude)
    .pointRadius((d: any) => d.radius)
    .pointLabel((d: any) => `
      <div style="
        background: rgba(10,0,0,0.85);
        border: 1px solid rgba(255,68,0,0.4);
        border-radius: 8px;
        padding: 10px 14px;
        font-family: monospace;
        font-size: 12px;
        color: #fff;
        min-width: 180px;
      ">
        <div style="color:#ff6600;letter-spacing:2px;font-size:11px;margin-bottom:6px">${d.label}</div>
        <div style="color:${d.color};margin-bottom:4px">● ${d.status}</div>
        ${d.description ? `<div style="color:#ffffff88;font-size:10px">${d.description}</div>` : ""}
        <div style="color:#ffffff44;font-size:10px;margin-top:4px">pos: ${d.source}</div>
      </div>
    `);
}

export default function Globe({ parcels, globeRef }: GlobeProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const composerRef = useRef<EffectComposer | null>(null);
  const frameRef = useRef<number>(0);
  const pendingParcelsRef = useRef<Parcel[]>(parcels);

  useEffect(() => {
    pendingParcelsRef.current = parcels;
    if (!globeRef.current) return;
    applyPoints(globeRef.current, buildPoints(parcels));
  }, [parcels, globeRef]);

  useEffect(() => {
    if (!containerRef.current) return;

    const init = async () => {
      const [{ default: GlobeGL }, countries] = await Promise.all([
        import("globe.gl"),
        fetch("https://raw.githubusercontent.com/holtzy/D3-graph-gallery/master/DATA/world.geojson").then(r => r.json()),
      ]);

      const GlobeConstructor = GlobeGL as any;
      const globe = GlobeConstructor({ animateIn: true, rendererConfig: { antialias: true, alpha: true } })(containerRef.current)
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
        .pointLat((d: any) => d.lat)
        .pointLng((d: any) => d.lng)
        .pointColor((d: any) => d.color)
        .pointAltitude((d: any) => d.altitude)
        .pointRadius((d: any) => d.radius)
        .pointLabel(() => "");

      const scene = globe.scene();
      scene.add(new THREE.AmbientLight(0xff4400, 0.4));
      const dirLight = new THREE.DirectionalLight(0xff8800, 1.2);
      dirLight.position.set(1, 1, 1);
      scene.add(dirLight);

      globe.controls().autoRotate = true;
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

      // Applique les colis déjà chargés pendant l'init
      applyPoints(globe, buildPoints(pendingParcelsRef.current));

      const renderer = globe.renderer() as THREE.WebGLRenderer;
      const camera = globe.camera() as THREE.Camera;

      const composer = new EffectComposer(renderer);
      composer.addPass(new RenderPass(scene, camera));
      composer.addPass(
        new EffectPass(
          camera as THREE.Camera,
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
