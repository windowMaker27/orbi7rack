"use client";

import { useEffect, useRef } from "react";
import * as THREE from "three";
import { EffectComposer, EffectPass, RenderPass, BloomEffect } from "postprocessing";

export default function Globe() {
  const containerRef = useRef<HTMLDivElement>(null);
  const globeRef = useRef<any>(null);
  const composerRef = useRef<EffectComposer | null>(null);
  const frameRef = useRef<number>(0);

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
        .hexPolygonAltitude(0.01);

      const scene = globe.scene();
      scene.add(new THREE.AmbientLight(0xff4400, 0.4));
      const dirLight = new THREE.DirectionalLight(0xff8800, 1.2);
      dirLight.position.set(1, 1, 1);
      scene.add(dirLight);

      globe.controls().autoRotate = true;
      globe.controls().autoRotateSpeed = 0.6;

      // Glow sur les graticules
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

      // Post-processing bloom
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

      // Boucle de rendu custom
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
  }, []);

  return (
    <div
      ref={containerRef}
      style={{ width: "100%", height: "100vh", background: "#0a0000" }}
    />
  );
}