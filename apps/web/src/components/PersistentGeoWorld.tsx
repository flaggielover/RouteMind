import { ArcLayer, PathLayer, PolygonLayer, ScatterplotLayer } from "@deck.gl/layers";
import { MapboxOverlay } from "@deck.gl/mapbox";
import type { PickingInfo } from "@deck.gl/core";
import * as maplibregl from "maplibre-gl";
import type { Map as MapLibreMap, StyleSpecification } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import mapLibreWorkerUrl from "maplibre-gl/dist/maplibre-gl-csp-worker.js?url";
import { useEffect, useMemo, useRef, useState, type MutableRefObject } from "react";
import type { OperationsSnapshot } from "../domain/model";
import {
  cityGeoCatalog,
  cityIds,
  createCityOperationalDataset,
  type CityId,
  type CityOperationalDataset,
  type CourierTrajectory,
  type LngLat,
} from "../visuals/cityGeo";
import type { GeoWorldController } from "../visuals/geoWorldController";
import type { UrbanWorldFrame } from "../visuals/operationsChapterState";
import { GeoWorldFallback } from "./GeoWorldFallback";

const DEFAULT_MAP_STYLE: StyleSpecification = {
  version: 8,
  sources: {
    openmaptiles: {
      type: "vector",
      url: "https://tiles.openfreemap.org/planet",
    },
  },
  layers: [
    {
      id: "background",
      type: "background",
      paint: { "background-color": "#081116" },
    },
    {
      id: "landuse",
      type: "fill",
      source: "openmaptiles",
      "source-layer": "landuse",
      paint: { "fill-color": "#111d21", "fill-opacity": 0.68 },
    },
    {
      id: "park",
      type: "fill",
      source: "openmaptiles",
      "source-layer": "park",
      paint: { "fill-color": "#142723", "fill-opacity": 0.8 },
    },
    {
      id: "water",
      type: "fill",
      source: "openmaptiles",
      "source-layer": "water",
      paint: { "fill-color": "#0b2730", "fill-opacity": 0.96 },
    },
    {
      id: "waterway",
      type: "line",
      source: "openmaptiles",
      "source-layer": "waterway",
      paint: { "line-color": "#28606b", "line-opacity": 0.62, "line-width": 1 },
    },
    {
      id: "administrative-boundary",
      type: "line",
      source: "openmaptiles",
      "source-layer": "boundary",
      paint: { "line-color": "#26383d", "line-opacity": 0.38, "line-width": 1 },
    },
    {
      id: "transportation",
      type: "line",
      source: "openmaptiles",
      "source-layer": "transportation",
      paint: {
        "line-color": "#34484d",
        "line-opacity": 0.72,
        "line-width": ["interpolate", ["linear"], ["zoom"], 8, 0.25, 13, 0.7, 17, 2.2],
      },
    },
    {
      id: "building",
      type: "fill-extrusion",
      source: "openmaptiles",
      "source-layer": "building",
      minzoom: 12,
      paint: {
        "fill-extrusion-color": "#1b292d",
        "fill-extrusion-height": ["coalesce", ["get", "render_height"], 7],
        "fill-extrusion-base": ["coalesce", ["get", "render_min_height"], 0],
        "fill-extrusion-opacity": 0.52,
      },
    },
  ],
};
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
  trajectoryId: string;
  entityType: "courier";
  label: string;
  coordinate: LngLat;
  risk: number;
}

interface LayerObject {
  id?: string;
  label?: string;
  trajectoryId?: string;
  courierId?: string;
  entityType?: string;
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

function routeColor(route: CourierTrajectory): readonly [number, number, number, number] {
  if (route.slaRisk > 0.62) return RED;
  if (route.slaRisk > 0.42) return AMBER;
  return route.state === "recent" ? SLATE : TEAL;
}

function movingCouriers(
  dataset: CityOperationalDataset,
  time: number,
  reducedMotion: boolean,
): MovingCourier[] {
  return dataset.trajectories
    .filter((route) => route.state === "active")
    .map((route, index) => {
      const movement = reducedMotion ? 0 : (time / 18000 + index * 0.11) % 0.28;
      return {
        id: route.courierId,
        trajectoryId: route.id,
        entityType: "courier",
        label: `Courier ${route.courierId}`,
        coordinate: mixPoint(route.points, Math.min(0.96, route.currentProgress + movement)),
        risk: route.slaRisk,
      };
    });
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

function applyOperationalStyle(map: MapLibreMap): void {
  for (const layer of map.getStyle().layers ?? []) {
    const id = layer.id.toLowerCase();
    try {
      if (layer.type === "background")
        map.setPaintProperty(layer.id, "background-color", "#081116");
      if (layer.type === "fill") {
        map.setPaintProperty(
          layer.id,
          "fill-color",
          id.includes("water") ? "#0b2730" : id.includes("building") ? "#1b292d" : "#111d21",
        );
        map.setPaintProperty(layer.id, "fill-opacity", id.includes("building") ? 0.62 : 0.9);
      }
      if (layer.type === "line") {
        map.setPaintProperty(
          layer.id,
          "line-color",
          id.includes("water")
            ? "#28606b"
            : id.includes("road") || id.includes("transport")
              ? "#34484d"
              : "#26383d",
        );
        map.setPaintProperty(layer.id, "line-opacity", id.includes("road") ? 0.72 : 0.52);
      }
      if (layer.type === "symbol") {
        map.setPaintProperty(layer.id, "text-color", "#8ea4a5");
        map.setPaintProperty(layer.id, "text-halo-color", "#081116");
        map.setPaintProperty(layer.id, "text-halo-width", 1.2);
        map.setPaintProperty(layer.id, "icon-opacity", 0.42);
      }
    } catch {
      // Style schemas differ; unsupported paint properties keep their source value.
    }
  }
}

function createOperationalLayers(
  dataset: CityOperationalDataset,
  frame: UrbanWorldFrame,
  selectedId: string | null,
  time: number,
  reducedMotion: boolean,
) {
  const selected = dataset.trajectories.find((route) => route.id === selectedId) ?? null;
  const routes = dataset.trajectories.map((route) => ({ ...route, entityType: "trajectory" }));
  const nodes = dataset.nodes.map((node) => ({ ...node, entityType: node.kind }));
  const hotspots = dataset.hotspots.map((hotspot) => ({ ...hotspot, entityType: "hotspot" }));
  const riskZones = dataset.riskZones.map((zone) => ({ ...zone, entityType: "risk-zone" }));
  const flows = dataset.flows.map((flow) => ({ ...flow, entityType: "aggregate-flow" }));
  const routeOpacity = 0.52 + frame.layerVisibility.flows * 0.38;
  const detailRoutes =
    frame.chapter === "live" || frame.chapter === "risk" || frame.chapter === "replay";
  return [
    new PolygonLayer({
      id: `risk-zones-${dataset.city.id}`,
      data: riskZones,
      getPolygon: (item) => item.polygon,
      getFillColor: (item) => (item.risk > 0.62 ? [185, 62, 62, 66] : [194, 129, 61, 40]),
      getLineColor: (item) => (item.risk > 0.62 ? RED : AMBER),
      getLineWidth: 1.5,
      lineWidthUnits: "pixels",
      filled: true,
      stroked: true,
      opacity: frame.layerVisibility.riskZones,
      pickable: true,
    }),
    new ScatterplotLayer({
      id: `demand-hotspots-${dataset.city.id}`,
      data: hotspots,
      getPosition: (item) => item.coordinate,
      getRadius: (item) => 180 + item.pressure * 520,
      getFillColor: (item) => (item.risk > 0.58 ? [222, 103, 99, 58] : [88, 203, 195, 46]),
      getLineColor: (item) => (item.risk > 0.58 ? RED : TEAL),
      getLineWidth: 1,
      radiusUnits: "meters",
      lineWidthUnits: "pixels",
      stroked: true,
      opacity: frame.layerVisibility.cells,
      pickable: true,
    }),
    new ArcLayer({
      id: `aggregate-flows-${dataset.city.id}`,
      data: flows,
      getSourcePosition: (item) => item.from,
      getTargetPosition: (item) => item.to,
      getSourceColor: TEAL,
      getTargetColor: (item) => (item.risk > 0.55 ? RED : AMBER),
      getWidth: (item) => 1.2 + item.courierCount / 24,
      widthUnits: "pixels",
      greatCircle: false,
      opacity: detailRoutes
        ? frame.layerVisibility.flows * 0.22
        : frame.layerVisibility.flows * 0.72,
      pickable: true,
    }),
    new PathLayer({
      id: `courier-trajectory-glow-${dataset.city.id}`,
      data: routes,
      getPath: (route) => route.points,
      getColor: (route) => {
        const color = routeColor(route);
        return [color[0], color[1], color[2], route.state === "active" ? 54 : 24];
      },
      getWidth: (route) => (selectedId === route.id ? 13 : route.state === "active" ? 7 : 3.5),
      widthUnits: "pixels",
      widthMinPixels: 2,
      capRounded: true,
      jointRounded: true,
      opacity: routeOpacity,
      pickable: false,
    }),
    new PathLayer({
      id: `courier-trajectories-${dataset.city.id}`,
      data: routes,
      getPath: (route) => route.points,
      getColor: (route) => routeColor(route),
      getWidth: (route) => (selectedId === route.id ? 5.4 : route.state === "active" ? 3.1 : 1.4),
      widthUnits: "pixels",
      widthMinPixels: 1,
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
          getWidth: 6.5,
          widthUnits: "pixels",
          capRounded: true,
          jointRounded: true,
          opacity: 0.96,
          pickable: true,
        })
      : null,
    new ScatterplotLayer({
      id: `operational-nodes-${dataset.city.id}`,
      data: nodes,
      getPosition: (node) => node.coordinate,
      getRadius: (node) => (node.kind === "courier" ? 78 : node.kind === "merchant" ? 62 : 54),
      getFillColor: (node) =>
        node.kind === "courier" ? AMBER : node.kind === "merchant" ? TEAL : SLATE,
      getLineColor: [232, 244, 241, 210],
      getLineWidth: 1,
      radiusUnits: "meters",
      lineWidthUnits: "pixels",
      stroked: true,
      opacity: frame.layerVisibility.nodes,
      pickable: true,
    }),
    new ScatterplotLayer({
      id: `moving-couriers-${dataset.city.id}`,
      data: movingCouriers(dataset, time, reducedMotion),
      getPosition: (courier) => courier.coordinate,
      getRadius: 118,
      getFillColor: (courier) => (courier.risk > 0.62 ? RED : AMBER),
      getLineColor: [247, 247, 235, 245],
      getLineWidth: 2,
      radiusUnits: "meters",
      lineWidthUnits: "pixels",
      stroked: true,
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
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const overlayRef = useRef<MapboxOverlay | null>(null);
  const dataset = useMemo(() => createCityOperationalDataset(cityId), [cityId]);
  const datasetRef = useRef(dataset);
  const frameRef = useRef(worldFrame);
  const selectedRef = useRef(selectedTrajectoryId);
  const reducedRef = useRef(false);
  const visibleRef = useRef(true);
  const animationRef = useRef(0);
  const lastLayerFrameRef = useRef(0);
  const [mapStatus, setMapStatus] = useState<"loading" | "ready" | "fallback">("loading");
  const [fallbackReason, setFallbackReason] = useState("Map initialization pending");
  const [hovered, setHovered] = useState<LayerObject | null>(null);

  const updateLayers = (time = 0) => {
    overlayRef.current?.setProps({
      layers: createOperationalLayers(
        datasetRef.current,
        frameRef.current,
        selectedRef.current,
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
        style: import.meta.env.VITE_MAP_STYLE_URL || DEFAULT_MAP_STYLE,
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
      });
      mapRef.current = map;
      map.addControl(
        new maplibregl.AttributionControl({
          compact: true,
          customAttribution: "RouteMind DEMO operations · © OpenStreetMap · © OpenMapTiles",
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
        applyOperationalStyle(map);
        const overlay = new MapboxOverlay({
          interleaved: true,
          layers: createOperationalLayers(
            datasetRef.current,
            frameRef.current,
            selectedRef.current,
            performance.now(),
            reducedRef.current,
          ),
          pickingRadius: 7,
          getCursor: ({ isHovering }) => (isHovering ? "pointer" : "grab"),
          onHover: (info: PickingInfo) => setHovered((info.object as LayerObject | null) ?? null),
          onClick: (info: PickingInfo) => {
            const object = info.object as LayerObject | null;
            const trajectoryId =
              object?.entityType === "trajectory" ? object.id : object?.trajectoryId;
            if (trajectoryId) onSelectTrajectory(trajectoryId);
          },
        });
        map.addControl(overlay);
        overlayRef.current = overlay;
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
        time - lastLayerFrameRef.current > 66
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
      setPointerFrame() {},
      clearFocus() {
        setHovered(null);
      },
    };
    return () => {
      destroyed = true;
      window.clearTimeout(loadTimeout);
      if (animationRef.current) window.cancelAnimationFrame(animationRef.current);
      document.removeEventListener("visibilitychange", onVisibility);
      reducedQuery?.removeEventListener?.("change", onReduced);
      overlayRef.current?.finalize();
      overlayRef.current = null;
      mapRef.current?.remove();
      mapRef.current = null;
      controllerRef.current = null;
    };
  }, [controllerRef, onSelectTrajectory]);

  const selected = dataset.trajectories.find((route) => route.id === selectedTrajectoryId) ?? null;
  return (
    <aside
      className="persistent-urban-world persistent-geo-world"
      data-world-chapter={worldFrame.chapter}
      data-world-role={worldFrame.sceneRole}
      data-map-status={mapStatus}
      data-city={cityId}
      data-pointer-target="scene"
      data-pointer-id="persistent-geo-world"
      aria-label={`Persistent ${dataset.city.name} courier operations map`}
    >
      <div className="geo-map-container" ref={containerRef} />
      {mapStatus === "fallback" && <GeoWorldFallback dataset={dataset} reason={fallbackReason} />}
      {mapStatus === "loading" && (
        <div className="geo-map-loading" role="status">
          Loading {dataset.city.name} real geography
        </div>
      )}
      <div className="persistent-world-chrome">
        <span className="persistent-world-kicker">ROUTEMIND / REAL CITY COURIER NETWORK</span>
        <span className="persistent-world-chapter">{worldFrame.chapter.replace("-", " ")}</span>
      </div>
      <div className="geo-city-selector" role="group" aria-label="Select operations city">
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
      <div className="geo-source-badge">
        <strong>DEMO / SIMULATED</strong>
        <span>real geography · synthetic operations · {snapshot.source} page context</span>
      </div>
      <div className="geo-map-summary" aria-live="polite">
        <span>
          <small>City</small>
          <strong>{dataset.city.name}</strong>
        </span>
        <span>
          <small>Active riders</small>
          <strong>{dataset.trajectories.filter((route) => route.state === "active").length}</strong>
        </span>
        <span>
          <small>Risk zones</small>
          <strong>{dataset.riskZones.length}</strong>
        </span>
      </div>
      <div className="geo-inspection" data-pointer-target="hud">
        <span>local inspection</span>
        <strong>{inspectionText(hovered, dataset)}</strong>
      </div>
      {selected && (
        <div className="geo-selected-route" aria-live="polite">
          <button
            type="button"
            aria-label="Clear selected courier"
            title="Clear selected courier"
            onClick={() => onSelectTrajectory(null)}
          >
            ×
          </button>
          <span>SELECTED COURIER</span>
          <strong>{selected.courierId}</strong>
          <dl>
            <div>
              <dt>Order</dt>
              <dd>{selected.orderId}</dd>
            </div>
            <div>
              <dt>ETA</dt>
              <dd>{selected.etaMinutes} min</dd>
            </div>
            <div>
              <dt>Distance</dt>
              <dd>{selected.distanceKilometres} km</dd>
            </div>
            <div>
              <dt>SLA risk</dt>
              <dd>{Math.round(selected.slaRisk * 100)}%</dd>
            </div>
            <div>
              <dt>Strategy</dt>
              <dd>{selected.strategy}</dd>
            </div>
          </dl>
        </div>
      )}
      <div className="geo-map-legend" aria-label="Operational map legend">
        <span>
          <i className="geo-legend-line active" /> active courier
        </span>
        <span>
          <i className="geo-legend-line recent" /> recent route
        </span>
        <span>
          <i className="geo-legend-dot merchant" /> pickup
        </span>
        <span>
          <i className="geo-legend-dot risk" /> SLA risk
        </span>
      </div>
      <div className="persistent-world-rule" aria-hidden="true" />
    </aside>
  );
}
