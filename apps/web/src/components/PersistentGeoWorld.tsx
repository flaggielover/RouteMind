import { ArcLayer, PathLayer, PolygonLayer, ScatterplotLayer, TextLayer } from "@deck.gl/layers";
import { MapboxOverlay } from "@deck.gl/mapbox";
import type { PickingInfo } from "@deck.gl/core";
import * as maplibregl from "maplibre-gl";
import type { Map as MapLibreMap } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import mapLibreWorkerUrl from "maplibre-gl/dist/maplibre-gl-csp-worker.js?url";
import { useEffect, useMemo, useRef, useState, type MutableRefObject } from "react";
import type { OperationsSnapshot } from "../domain/model";
import {
  cityGeoCatalog,
  cityIds,
  createCityOperationalDataset,
  projectCityOperationalLod,
  type CityId,
  type CityOperationalDataset,
  type CourierAgent,
  type CourierTrajectory,
  type LngLat,
  type OperationalLodMode,
} from "../visuals/cityGeo";
import type { GeoWorldController } from "../visuals/geoWorldController";
import { MAP_OPTICAL_LENS_LAYER_ID, MapOpticalLensLayer } from "../visuals/mapOpticalLens";
import type { UrbanWorldFrame } from "../visuals/operationsChapterState";
import { applyRouteMindBasemapTheme, resolveBasemapProvider } from "../visuals/basemapProvider";
import { GeoWorldFallback } from "./GeoWorldFallback";
import { useLocale } from "../i18n";

const TEAL: readonly [number, number, number, number] = [88, 203, 195, 228];
const AMBER: readonly [number, number, number, number] = [222, 170, 96, 232];
const RED: readonly [number, number, number, number] = [222, 103, 99, 232];
const SLATE: readonly [number, number, number, number] = [131, 158, 163, 170];

interface PersistentGeoWorldProps {
  snapshot: OperationsSnapshot;
  worldFrame: UrbanWorldFrame;
  cityId: CityId;
  onCityChange: (cityId: CityId) => void;
  selectedTrajectoryId: string | null;
  onSelectTrajectory: (trajectoryId: string | null) => void;
  controllerRef: MutableRefObject<GeoWorldController | null>;
}

interface MovingCourier {
  id: string;
  trajectoryId?: string;
  entityType: "courier";
  label: string;
  coordinate: LngLat;
  risk: number;
  heading: number;
  state: CourierAgent["state"];
}

interface LayerObject {
  id?: string;
  label?: string;
  trajectoryId?: string;
  courierId?: string;
  entityType?: string;
  kind?: string;
  risk?: number;
}

function mixPoint(path: readonly LngLat[], progress: number): LngLat {
  if (path.length < 2) return path[0] ?? [0, 0];
  const scaled = Math.max(0, Math.min(0.999, progress)) * (path.length - 1);
  const index = Math.floor(scaled);
  const local = scaled - index;
  const from = path[index] ?? path[0]!;
  const to = path[index + 1] ?? from;
  return [from[0] + (to[0] - from[0]) * local, from[1] + (to[1] - from[1]) * local];
}

function routeHeading(path: readonly LngLat[], progress: number): number {
  if (path.length < 2) return 0;
  const scaled = Math.max(0, Math.min(0.999, progress)) * (path.length - 1);
  const index = Math.floor(scaled);
  const from = path[index] ?? path[0]!;
  const to = path[index + 1] ?? from;
  return (Math.atan2(to[0] - from[0], to[1] - from[1]) * 180) / Math.PI;
}

function routeColor(route: CourierTrajectory): readonly [number, number, number, number] {
  if (route.slaRisk > 0.62) return RED;
  if (route.slaRisk > 0.42) return AMBER;
  return route.state === "recent" ? SLATE : TEAL;
}

function movingCouriers(
  agents: readonly CourierAgent[],
  time: number,
  reducedMotion: boolean,
): MovingCourier[] {
  return agents.map((agent) => {
    const movement = reducedMotion ? 0 : (time / 1000) * agent.velocity;
    const progress = (agent.baseProgress + movement) % 1;
    return {
      id: agent.id,
      ...(agent.trajectoryId ? { trajectoryId: agent.trajectoryId } : {}),
      entityType: "courier",
      label: `Courier ${agent.id}`,
      coordinate: mixPoint(agent.path, progress),
      risk: agent.risk,
      heading: routeHeading(agent.path, progress),
      state: agent.state,
    };
  });
}

function operationalLodMode(frame: UrbanWorldFrame, selectedId: string | null): OperationalLodMode {
  if (selectedId) return "selected";
  if (
    frame.chapter === "overview" ||
    frame.chapter === "strategy" ||
    frame.chapter === "research"
  ) {
    return "city";
  }
  return "district";
}

function chapterCamera(
  dataset: CityOperationalDataset,
  frame: UrbanWorldFrame,
  selectedId: string | null,
) {
  const city = dataset.city;
  let center = city.center;
  let zoom = city.zoom;
  let pitch: number;
  let bearing = city.bearing;
  if (frame.chapter === "pressure") {
    center = dataset.hotspots[0]?.coordinate ?? center;
    zoom += 0.55;
    pitch = 48;
  } else if (frame.chapter === "risk") {
    center = [...dataset.hotspots].sort((a, b) => b.risk - a.risk)[0]?.coordinate ?? center;
    zoom += 0.82;
    pitch = 54;
    bearing -= 8;
  } else if (frame.chapter === "strategy") {
    zoom -= 0.18;
    pitch = 50;
    bearing += 14;
  } else if (frame.chapter === "live") {
    const route =
      dataset.trajectories.find((item) => item.id === selectedId) ?? dataset.trajectories[0];
    center = route ? mixPoint(route.points, route.currentProgress) : center;
    zoom += 1.2;
    pitch = 58;
  } else if (frame.chapter === "replay") {
    zoom += 0.38;
    pitch = 46;
    bearing += 5;
  } else if (frame.chapter === "research") {
    zoom -= 0.24;
    pitch = 28;
  } else {
    zoom -= 0.42;
    pitch = 26;
  }
  return { center, zoom, pitch, bearing };
}

function relatedTrajectoryId(
  dataset: CityOperationalDataset,
  object: LayerObject | null,
): string | null {
  if (!object) return null;
  if (object.entityType === "trajectory") return object.id ?? null;
  if (object.entityType === "courier") return object.trajectoryId ?? null;
  if (object.kind === "merchant" || object.kind === "customer") {
    return (
      dataset.trajectories.find(
        (route) => route.merchantId === object.id || route.customerId === object.id,
      )?.id ?? null
    );
  }
  return null;
}

function individualRouteOpacity(chapter: UrbanWorldFrame["chapter"]): number {
  if (chapter === "live") return 0.92;
  if (chapter === "replay") return 0.72;
  if (chapter === "risk") return 0.62;
  if (chapter === "pressure") return 0.24;
  if (chapter === "strategy") return 0.18;
  if (chapter === "research") return 0.2;
  return 0.1;
}

function aggregateFlowOpacity(chapter: UrbanWorldFrame["chapter"]): number {
  if (chapter === "overview") return 0.88;
  if (chapter === "strategy") return 0.66;
  if (chapter === "pressure") return 0.26;
  if (chapter === "risk") return 0.18;
  if (chapter === "replay") return 0.16;
  return 0.08;
}

function chapterAnimatesCouriers(chapter: UrbanWorldFrame["chapter"]): boolean {
  return chapter !== "research";
}

export function createOperationalLayers(
  dataset: CityOperationalDataset,
  frame: UrbanWorldFrame,
  selectedId: string | null,
  hovered: LayerObject | null,
  time: number,
  reducedMotion: boolean,
) {
  const selected = dataset.trajectories.find((route) => route.id === selectedId) ?? null;
  const camera = chapterCamera(dataset, frame, selectedId);
  const lod = projectCityOperationalLod(dataset, {
    mode: operationalLodMode(frame, selectedId),
    focusCoordinate: camera.center,
    selectedTrajectoryId: selectedId,
  });
  const relatedId = selectedId ?? relatedTrajectoryId(dataset, hovered);
  const relatedRoute = dataset.trajectories.find((route) => route.id === relatedId) ?? null;
  const routes = lod.trajectories.map((route) => ({ ...route, entityType: "trajectory" }));
  const nodes = dataset.nodes
    .filter((node) => node.kind !== "courier")
    .map((node) => ({ ...node, entityType: node.kind }));
  const hotspots = dataset.hotspots.map((hotspot) => ({ ...hotspot, entityType: "hotspot" }));
  const riskZones = dataset.riskZones.map((zone) => ({ ...zone, entityType: "risk-zone" }));
  const flows = dataset.flows.map((flow) => ({ ...flow, entityType: "aggregate-flow" }));
  const couriers = movingCouriers(
    lod.courierAgents,
    time,
    reducedMotion || !chapterAnimatesCouriers(frame.chapter),
  );
  const emphasizedCourierIds = new Set(lod.trajectories.map((route) => route.courierId));
  const emphasizedCouriers = couriers.filter((courier) => emphasizedCourierIds.has(courier.id));
  const routeOpacity = individualRouteOpacity(frame.chapter) * frame.layerVisibility.flows;
  const flowOpacity = aggregateFlowOpacity(frame.chapter) * frame.layerVisibility.flows;
  const riskExtruded = frame.chapter === "pressure" || frame.chapter === "risk";
  return [
    new PolygonLayer({
      id: `risk-cells-${dataset.city.id}`,
      data: riskZones,
      getPolygon: (item) => item.polygon,
      getFillColor: (item) => {
        const highlighted = hovered?.id === item.id;
        if (item.risk > 0.62) return [188, 70, 65, highlighted ? 118 : 68];
        return [194, 137, 72, highlighted ? 96 : 42];
      },
      getLineColor: (item) => {
        const color = item.risk > 0.62 ? RED : AMBER;
        return [color[0], color[1], color[2], hovered?.id === item.id ? 245 : 126];
      },
      getLineWidth: (item) => (hovered?.id === item.id ? 2 : 0.8),
      getElevation: (item) => 12 + (frame.chapter === "pressure" ? item.pressure : item.risk) * 96,
      lineWidthUnits: "pixels",
      extruded: riskExtruded,
      filled: true,
      stroked: true,
      opacity: frame.layerVisibility.riskZones * (frame.chapter === "overview" ? 0.42 : 0.82),
      pickable: true,
      material: { ambient: 0.42, diffuse: 0.58, shininess: 18, specularColor: [58, 68, 66] },
    }),
    new ScatterplotLayer({
      id: `demand-hotspots-${dataset.city.id}`,
      data: hotspots,
      getPosition: (item) => item.coordinate,
      getRadius: (item) => 110 + item.pressure * 280,
      getFillColor: (item) => (item.risk > 0.58 ? [222, 103, 99, 30] : [88, 203, 195, 24]),
      getLineColor: (item) => (item.risk > 0.58 ? [222, 103, 99, 112] : [88, 203, 195, 96]),
      getLineWidth: 0.75,
      radiusUnits: "meters",
      lineWidthUnits: "pixels",
      stroked: true,
      opacity: frame.layerVisibility.cells * (frame.chapter === "pressure" ? 0.86 : 0.38),
      pickable: true,
    }),
    new ArcLayer({
      id: `aggregate-flows-${dataset.city.id}`,
      data: flows,
      getSourcePosition: (item) => item.from,
      getTargetPosition: (item) => item.to,
      getSourceColor: TEAL,
      getTargetColor: (item) => (item.risk > 0.55 ? RED : AMBER),
      getWidth: (item) => 0.7 + item.courierCount / 46,
      getHeight: 0.12,
      widthUnits: "pixels",
      greatCircle: false,
      opacity: flowOpacity,
      pickable: true,
    }),
    new PathLayer({
      id: `courier-trajectory-underlay-${dataset.city.id}`,
      data: routes,
      getPath: (route) => route.points,
      getColor: (route) => {
        const color = routeColor(route);
        const focused = relatedId === route.id;
        return [color[0], color[1], color[2], focused ? 82 : route.state === "active" ? 30 : 14];
      },
      getWidth: (route) => (relatedId === route.id ? 7 : route.state === "active" ? 3.4 : 2),
      widthUnits: "pixels",
      widthMinPixels: 1,
      capRounded: true,
      jointRounded: true,
      opacity: routeOpacity,
      pickable: false,
    }),
    new PathLayer({
      id: `courier-trajectories-${dataset.city.id}`,
      data: routes,
      getPath: (route) => route.points,
      getColor: (route) => {
        const color = routeColor(route);
        const dimmed = relatedId !== null && relatedId !== route.id;
        return [
          color[0],
          color[1],
          color[2],
          dimmed ? 54 : relatedId === route.id ? 255 : color[3],
        ];
      },
      getWidth: (route) => (relatedId === route.id ? 3.8 : route.state === "active" ? 1.65 : 0.85),
      widthUnits: "pixels",
      widthMinPixels: 0.75,
      capRounded: true,
      jointRounded: true,
      opacity: routeOpacity,
      pickable: true,
    }),
    selected
      ? new PathLayer({
          id: `selected-trajectory-${selected.id}`,
          data: [{ ...selected, entityType: "trajectory" }],
          getPath: (route) => route.points,
          getColor: routeColor(selected),
          getWidth: 4.2,
          widthUnits: "pixels",
          capRounded: true,
          jointRounded: true,
          opacity: 0.96,
          pickable: true,
        })
      : null,
    new TextLayer({
      id: `operational-entity-glyphs-${dataset.city.id}`,
      data: nodes,
      getPosition: (node) => node.coordinate,
      getText: (node) => (node.kind === "merchant" ? "M" : "D"),
      getColor: (node) => (node.kind === "merchant" ? TEAL : [190, 205, 205, 220]),
      getSize: (node) =>
        relatedRoute && (node.id === relatedRoute.merchantId || node.id === relatedRoute.customerId)
          ? 17
          : 11,
      sizeUnits: "pixels",
      fontFamily: "Arial, sans-serif",
      fontWeight: 700,
      opacity: frame.layerVisibility.nodes,
      pickable: true,
    }),
    new ScatterplotLayer({
      id: `courier-population-${dataset.city.id}-${lod.mode}`,
      data: couriers,
      getPosition: (courier) => courier.coordinate,
      getRadius: (courier) =>
        lod.mode === "city" ? (courier.state === "available" ? 42 : 32) : 44,
      getFillColor: (courier) =>
        courier.state === "available"
          ? [88, 203, 195, 146]
          : courier.state === "rebalancing"
            ? [184, 153, 101, 104]
            : [151, 183, 179, 118],
      getLineColor: [7, 16, 20, 155],
      getLineWidth: 0.55,
      radiusUnits: "meters",
      radiusMinPixels: lod.mode === "city" ? 1.15 : 1.4,
      radiusMaxPixels: 3.6,
      lineWidthUnits: "pixels",
      stroked: true,
      opacity:
        frame.layerVisibility.nodes *
        (lod.mode === "city" ? 0.66 : lod.mode === "district" ? 0.8 : 0.9),
      pickable: false,
    }),
    new ScatterplotLayer({
      id: `courier-focus-rings-${dataset.city.id}`,
      data: emphasizedCouriers,
      getPosition: (courier) => courier.coordinate,
      getRadius: (courier) => (relatedId === courier.trajectoryId ? 104 : 58),
      getFillColor: [7, 16, 20, 42],
      getLineColor: (courier) => (courier.risk > 0.62 ? [222, 103, 99, 205] : [214, 162, 97, 205]),
      getLineWidth: (courier) => (relatedId === courier.trajectoryId ? 2 : 0.8),
      radiusUnits: "meters",
      lineWidthUnits: "pixels",
      stroked: true,
      opacity: frame.layerVisibility.nodes,
      pickable: false,
    }),
    new TextLayer({
      id: `moving-couriers-${dataset.city.id}`,
      data: emphasizedCouriers,
      getPosition: (courier) => courier.coordinate,
      getText: () => ">",
      getColor: (courier) => (courier.risk > 0.62 ? RED : AMBER),
      getSize: (courier) => (relatedId === courier.trajectoryId ? 17 : 12),
      getAngle: (courier) => courier.heading,
      sizeUnits: "pixels",
      fontFamily: "Arial, sans-serif",
      fontWeight: 700,
      billboard: true,
      opacity: frame.layerVisibility.nodes,
      pickable: true,
    }),
  ].filter(Boolean);
}

function inspectionText(object: LayerObject | null, dataset: CityOperationalDataset): string {
  if (!object) return `${dataset.city.name} courier network ready for inspection`;
  if (object.entityType === "trajectory") {
    const route = dataset.trajectories.find((item) => item.id === object.id);
    return route
      ? `${route.courierId} · ${route.etaMinutes} min ETA · ${Math.round(route.slaRisk * 100)}% SLA risk`
      : "Courier trajectory";
  }
  if (object.entityType === "courier") return `${object.label ?? object.id} · on route`;
  if (object.entityType === "merchant") return `${object.label ?? object.id} · pickup origin`;
  if (object.entityType === "customer")
    return `${object.label ?? object.id} · delivery destination`;
  if (object.entityType === "risk-zone") return `${object.label ?? object.id} · SLA risk region`;
  if (object.entityType === "hotspot") return "Demand pressure hotspot";
  return object.label ?? "Operational map signal";
}

export default function PersistentGeoWorld({
  snapshot,
  worldFrame,
  cityId,
  onCityChange,
  selectedTrajectoryId,
  onSelectTrajectory,
  controllerRef,
}: PersistentGeoWorldProps) {
  const { t, formatNumber } = useLocale();
  const basemapProvider = useMemo(
    () =>
      resolveBasemapProvider({
        styleUrl: import.meta.env.VITE_MAP_STYLE_URL,
        attribution: import.meta.env.VITE_MAP_ATTRIBUTION,
        label: import.meta.env.VITE_MAP_PROVIDER_LABEL,
      }),
    [],
  );
  const worldRef = useRef<HTMLElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const overlayRef = useRef<MapboxOverlay | null>(null);
  const opticalLensRef = useRef<MapOpticalLensLayer | null>(null);
  const dataset = useMemo(() => createCityOperationalDataset(cityId), [cityId]);
  const datasetRef = useRef(dataset);
  const frameRef = useRef(worldFrame);
  const selectedRef = useRef(selectedTrajectoryId);
  const reducedRef = useRef(false);
  const visibleRef = useRef(true);
  const animationRef = useRef(0);
  const lastLayerFrameRef = useRef(0);
  const hoveredRef = useRef<LayerObject | null>(null);
  const [mapStatus, setMapStatus] = useState<"loading" | "ready" | "fallback">("loading");
  const [lensMode, setLensMode] = useState<"pending" | "webgl-cc-lens" | "unavailable">("pending");
  const [fallbackReason, setFallbackReason] = useState("Map initialization pending");
  const [hovered, setHovered] = useState<LayerObject | null>(null);

  const updateLayers = (time = 0) => {
    overlayRef.current?.setProps({
      layers: createOperationalLayers(
        datasetRef.current,
        frameRef.current,
        selectedRef.current,
        hoveredRef.current,
        time,
        reducedRef.current,
      ),
    });
  };

  const applyCamera = (animate: boolean) => {
    const map = mapRef.current;
    if (!map) return;
    const camera = chapterCamera(datasetRef.current, frameRef.current, selectedRef.current);
    const options = {
      center: camera.center as [number, number],
      zoom: camera.zoom,
      pitch: camera.pitch,
      bearing: camera.bearing,
    };
    if (animate && !reducedRef.current) map.easeTo({ ...options, duration: 900, essential: false });
    else map.jumpTo(options);
  };

  useEffect(() => {
    datasetRef.current = dataset;
    selectedRef.current = selectedTrajectoryId;
    updateLayers(performance.now());
    applyCamera(true);
  }, [dataset, selectedTrajectoryId]);

  useEffect(() => {
    frameRef.current = worldFrame;
    updateLayers(performance.now());
    applyCamera(true);
  }, [worldFrame]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container || typeof window === "undefined") return;
    if (typeof WebGL2RenderingContext === "undefined") {
      setFallbackReason("WebGL2 unavailable");
      setMapStatus("fallback");
      controllerRef.current = {
        setWorldFrame: () => undefined,
        setScrollFrame: () => undefined,
        setPointerFrame: () => undefined,
        clearFocus: () => undefined,
      };
      return () => {
        controllerRef.current = null;
      };
    }
    const reducedQuery = window.matchMedia?.("(prefers-reduced-motion: reduce)") ?? null;
    reducedRef.current = reducedQuery?.matches ?? false;
    let destroyed = false;
    let loadTimeout = 0;
    try {
      maplibregl.setWorkerUrl(mapLibreWorkerUrl);
      const map = new maplibregl.Map({
        container,
        style: basemapProvider.styleUrl,
        center: datasetRef.current.city.center as [number, number],
        zoom: datasetRef.current.city.zoom - 0.42,
        pitch: 26,
        bearing: datasetRef.current.city.bearing,
        attributionControl: false,
        canvasContextAttributes: {
          antialias: true,
          powerPreference: "high-performance",
        },
        pixelRatio: Math.min(window.devicePixelRatio || 1, 1.5),
        maxPitch: 65,
        // Plain wheel scrolling continues the page; hold Ctrl/Cmd for map zoom.
        cooperativeGestures: true,
      });
      mapRef.current = map;
      const updateMapZoom = () => {
        const world = worldRef.current;
        if (world) world.dataset.mapZoom = map.getZoom().toFixed(2);
      };
      map.on("zoom", updateMapZoom);
      map.on("move", updateMapZoom);
      map.on("zoomend", updateMapZoom);
      updateMapZoom();
      map.addControl(
        new maplibregl.AttributionControl({
          compact: true,
          customAttribution: [...basemapProvider.customAttribution],
        }),
        "bottom-right",
      );
      map.addControl(
        new maplibregl.NavigationControl({ showCompass: false, visualizePitch: true }),
        "bottom-left",
      );
      map.on("load", () => {
        if (destroyed) return;
        window.clearTimeout(loadTimeout);
        const themeMutationCount =
          basemapProvider.themePolicy === "routemind-graphite"
            ? applyRouteMindBasemapTheme(map)
            : 0;
        if (worldRef.current) {
          worldRef.current.dataset.basemapLayers = String(map.getStyle().layers?.length ?? 0);
          worldRef.current.dataset.basemapThemeMutations = String(themeMutationCount);
        }
        const overlay = new MapboxOverlay({
          interleaved: true,
          layers: createOperationalLayers(
            datasetRef.current,
            frameRef.current,
            selectedRef.current,
            hoveredRef.current,
            performance.now(),
            reducedRef.current,
          ),
          pickingRadius: 7,
          getCursor: ({ isHovering }) => (isHovering ? "pointer" : "crosshair"),
          onHover: (info: PickingInfo) => {
            const next = (info.object as LayerObject | null) ?? null;
            if (
              next?.id === hoveredRef.current?.id &&
              next?.entityType === hoveredRef.current?.entityType
            ) {
              return;
            }
            hoveredRef.current = next;
            setHovered(next);
            updateLayers(performance.now());
          },
          onClick: (info: PickingInfo) => {
            const object = info.object as LayerObject | null;
            const trajectoryId =
              object?.entityType === "trajectory" ? object.id : object?.trajectoryId;
            if (trajectoryId) onSelectTrajectory(trajectoryId);
          },
        });
        map.addControl(overlay);
        overlayRef.current = overlay;
        try {
          const opticalLens = new MapOpticalLensLayer();
          map.addLayer(opticalLens);
          opticalLensRef.current = opticalLens;
          setLensMode("webgl-cc-lens");
        } catch {
          opticalLensRef.current = null;
          setLensMode("unavailable");
        }
        setMapStatus("ready");
        applyCamera(false);
      });
      map.on("error", () => {
        if (!map.loaded() && !destroyed) setFallbackReason("Real basemap unavailable");
      });
      loadTimeout = window.setTimeout(() => {
        if (!map.loaded() && !destroyed) setMapStatus("fallback");
      }, 12000);
    } catch (error) {
      setFallbackReason(error instanceof Error ? error.message : "WebGL map initialization failed");
      setMapStatus("fallback");
    }

    const onVisibility = () => {
      visibleRef.current = document.visibilityState === "visible";
    };
    const onReduced = (event: MediaQueryListEvent) => {
      reducedRef.current = event.matches;
      updateLayers(performance.now());
      applyCamera(false);
    };
    document.addEventListener("visibilitychange", onVisibility);
    reducedQuery?.addEventListener?.("change", onReduced);
    const animate = (time: number) => {
      if (
        !destroyed &&
        visibleRef.current &&
        !reducedRef.current &&
        chapterAnimatesCouriers(frameRef.current.chapter) &&
        time - lastLayerFrameRef.current > 180
      ) {
        lastLayerFrameRef.current = time;
        updateLayers(time);
      }
      if (!destroyed) animationRef.current = window.requestAnimationFrame(animate);
    };
    animationRef.current = window.requestAnimationFrame(animate);

    controllerRef.current = {
      setWorldFrame(frame) {
        frameRef.current = frame;
        updateLayers(performance.now());
        applyCamera(true);
      },
      setScrollFrame() {},
      setPointerFrame(pointer) {
        const world = worldRef.current;
        if (!world) return;
        const rect = world.getBoundingClientRect();
        const x = pointer.x - rect.left;
        const y = pointer.y - rect.top;
        const inside = x >= 0 && x <= rect.width && y >= 0 && y <= rect.height;
        const active = inside && pointer.targetType === "scene";
        opticalLensRef.current?.setPointerFrame({
          x,
          y,
          vx: pointer.vx,
          vy: pointer.vy,
          viewportWidth: rect.width,
          viewportHeight: rect.height,
          active,
          reducedMotion: reducedRef.current,
        });
        const lensDebug = opticalLensRef.current?.getDebugState();
        world.dataset.lensActive = String(active);
        world.dataset.lensDistortion = lensDebug?.distortion.toFixed(2) ?? "0";
        world.dataset.lensRgbShift = lensDebug?.rgbShift.toFixed(5) ?? "0";
      },
      clearFocus() {
        hoveredRef.current = null;
        setHovered(null);
        const world = worldRef.current;
        const rect = world?.getBoundingClientRect();
        opticalLensRef.current?.setPointerFrame({
          x: 0,
          y: 0,
          vx: 0,
          vy: 0,
          viewportWidth: rect?.width ?? 1,
          viewportHeight: rect?.height ?? 1,
          active: false,
          reducedMotion: reducedRef.current,
        });
        if (world) {
          world.dataset.lensActive = "false";
          world.dataset.lensRgbShift = "0";
        }
      },
    };
    return () => {
      destroyed = true;
      window.clearTimeout(loadTimeout);
      if (animationRef.current) window.cancelAnimationFrame(animationRef.current);
      document.removeEventListener("visibilitychange", onVisibility);
      reducedQuery?.removeEventListener?.("change", onReduced);
      if (mapRef.current?.getLayer(MAP_OPTICAL_LENS_LAYER_ID)) {
        mapRef.current.removeLayer(MAP_OPTICAL_LENS_LAYER_ID);
      }
      opticalLensRef.current = null;
      overlayRef.current?.finalize();
      overlayRef.current = null;
      mapRef.current?.remove();
      mapRef.current = null;
      controllerRef.current = null;
    };
  }, [basemapProvider, controllerRef, onSelectTrajectory]);

  const selected = dataset.trajectories.find((route) => route.id === selectedTrajectoryId) ?? null;
  const lodMode = operationalLodMode(worldFrame, selectedTrajectoryId);
  const lod = projectCityOperationalLod(dataset, {
    mode: lodMode,
    focusCoordinate: chapterCamera(dataset, worldFrame, selectedTrajectoryId).center,
    selectedTrajectoryId,
  });
  const selectedMerchant = selected
    ? (dataset.nodes.find((node) => node.id === selected.merchantId) ?? null)
    : null;
  const selectedCustomer = selected
    ? (dataset.nodes.find((node) => node.id === selected.customerId) ?? null)
    : null;
  return (
    <aside
      ref={worldRef}
      className="persistent-urban-world persistent-geo-world"
      data-world-chapter={worldFrame.chapter}
      data-world-role={worldFrame.sceneRole}
      data-map-status={mapStatus}
      data-basemap-provider={basemapProvider.id}
      data-basemap-quality={basemapProvider.qualityTier}
      data-basemap-theme={basemapProvider.themePolicy}
      data-city={cityId}
      data-courier-population={dataset.courierAgents.length}
      data-emphasized-trajectories={dataset.trajectories.length}
      data-visible-couriers={lod.courierAgents.length}
      data-visible-trajectories={lod.trajectories.length}
      data-map-lod={lodMode}
      data-lens-mode={lensMode}
      data-pointer-target="scene"
      data-pointer-id="persistent-geo-world"
      aria-label={`Persistent ${dataset.city.name} courier operations map`}
      aria-roledescription={t("chapter.live")}
    >
      <div className="geo-map-container" ref={containerRef} />
      {mapStatus === "fallback" && <GeoWorldFallback dataset={dataset} reason={fallbackReason} />}
      {mapStatus === "loading" && (
        <div className="geo-map-loading" role="status">
          {dataset.city.name} {t("ops.loadingProjections")}
        </div>
      )}
      <div
        className="persistent-world-chrome"
        data-pointer-target="hud"
        data-pointer-id="geo-world-chrome"
      >
        <span className="persistent-world-kicker">
          ROUTEMIND / {t("ops.syntheticCourierField")}
        </span>
        <span className="persistent-world-chapter">{worldFrame.chapter.replace("-", " ")}</span>
      </div>
      <div className="geo-city-selector" role="group" aria-label={t("ops.selectCity")}>
        {cityIds.map((id) => (
          <button
            key={id}
            type="button"
            className={id === cityId ? "active" : ""}
            aria-pressed={id === cityId}
            onClick={() => onCityChange(id)}
          >
            <span>{cityGeoCatalog[id].name}</span>
            <small>{cityGeoCatalog[id].nameZh}</small>
          </button>
        ))}
      </div>
      <div
        className="geo-source-badge"
        data-pointer-target="hud"
        data-pointer-id="geo-source-badge"
      >
        <strong>{t("ops.demoSynthetic")}</strong>
        <span>
          {basemapProvider.label} · {t("ops.syntheticOperations")} · {snapshot.source} page context
        </span>
      </div>
      <div
        className="geo-map-summary"
        data-pointer-target="hud"
        data-pointer-id="geo-map-summary"
        aria-live="polite"
      >
        <span>
          <small>{t("ops.city")}</small>
          <strong>{dataset.city.name}</strong>
        </span>
        <span>
          <small>{t("ops.couriers")}</small>
          <strong>{formatNumber(dataset.courierAgents.length)}</strong>
        </span>
        <span>
          <small>{t("ops.focusRoutes")}</small>
          <strong>{formatNumber(dataset.trajectories.length)}</strong>
        </span>
        <span>
          <small>{t("ops.lod")}</small>
          <strong>{lodMode.toUpperCase()}</strong>
        </span>
        <span>
          <small>{t("ops.riskZones")}</small>
          <strong>{formatNumber(dataset.riskZones.length)}</strong>
        </span>
      </div>
      <div className="geo-inspection" data-pointer-target="hud" data-pointer-id="geo-inspection">
        <span>{t("ops.localInspection")}</span>
        <strong>{inspectionText(hovered, dataset)}</strong>
      </div>
      {selected && (
        <div
          className="geo-selected-route"
          data-pointer-target="hud"
          data-pointer-id="geo-selected-route"
          aria-live="polite"
        >
          <button
            type="button"
            aria-label={t("ops.clearSelectedCourier")}
            title={t("ops.clearSelectedCourier")}
            onClick={() => onSelectTrajectory(null)}
          >
            ×
          </button>
          <span>{t("ops.selectedCourier")}</span>
          <strong>{selected.courierId}</strong>
          <dl>
            <div>
              <dt>{t("ops.order")}</dt>
              <dd>{selected.orderId}</dd>
            </div>
            <div>
              <dt>{t("ops.eta")}</dt>
              <dd>{selected.etaMinutes} min</dd>
            </div>
            <div>
              <dt>{t("ops.distance")}</dt>
              <dd>{selected.distanceKilometres} km</dd>
            </div>
            <div>
              <dt>{t("ops.slaRisk")}</dt>
              <dd>{Math.round(selected.slaRisk * 100)}%</dd>
            </div>
            <div>
              <dt>{t("chapter.strategy")}</dt>
              <dd>{selected.strategy}</dd>
            </div>
            <div>
              <dt>{t("ops.handoff")}</dt>
              <dd>
                {selectedMerchant?.label ?? selected.merchantId} →{" "}
                {selectedCustomer?.label ?? selected.customerId}
              </dd>
            </div>
          </dl>
        </div>
      )}
      <div
        className="geo-map-legend"
        data-pointer-target="hud"
        data-pointer-id="geo-map-legend"
        aria-label={t("ops.mapLegend")}
      >
        <span>
          <i className="geo-legend-line active" /> {t("ops.emphasizedRoute")}
        </span>
        <span>
          <i className="geo-legend-line recent" /> {t("ops.recentRoute")}
        </span>
        <span>
          <i className="geo-legend-dot courier" /> {t("ops.syntheticCourier")}
        </span>
        <span>
          <i className="geo-legend-dot merchant" /> {t("ops.pickup")}
        </span>
        <span>
          <i className="geo-legend-dot risk" /> {t("ops.slaRisk")}
        </span>
      </div>
      <div className="persistent-world-rule" aria-hidden="true" />
    </aside>
  );
}
