import type { DataAvailability, OperationsSnapshot } from "../domain/model";
import { toUrbanFieldState, type UrbanFieldState } from "./urbanFieldState";

export const OPERATIONS_CHAPTER_ORDER = [
  "overview",
  "pressure",
  "risk",
  "strategy",
  "live",
  "replay",
  "research",
] as const;

export type OperationsChapterId = (typeof OPERATIONS_CHAPTER_ORDER)[number];
export type OperationsCameraMode =
  | "overview"
  | "pressure-close"
  | "risk-hotspot"
  | "strategy-pullback"
  | "live-inspection"
  | "replay-tracking"
  | "research-stable";
export type OperationsSceneRole = "hero" | "field" | "backdrop" | "inspection" | "evidence";
export type OperationsInstrumentationMode = "minimal" | "floating" | "hero" | "wall" | "dock";

export interface UrbanWorldFrame {
  chapter: OperationsChapterId;
  progress: number;
  cameraMode: OperationsCameraMode;
  sceneRole: OperationsSceneRole;
  instrumentation: OperationsInstrumentationMode;
  focusStrength: number;
  layerVisibility: {
    core: number;
    cells: number;
    flows: number;
    nodes: number;
    riskZones: number;
  };
  lighting: {
    key: number;
    ambient: number;
    risk: number;
  };
}

export interface OperationsChapterState {
  id: OperationsChapterId;
  index: number;
  label: string;
  title: string;
  description: string;
  source: OperationsSnapshot["source"];
  availability: DataAvailability;
  provenance: string;
  focusEntityId: string | null;
  activeMetric: string;
  urbanField: UrbanFieldState;
  world: UrbanWorldFrame;
}

const clamp = (value: number, min = 0, max = 1) => Math.min(max, Math.max(min, value));

const CHAPTER_META: Record<
  OperationsChapterId,
  Omit<
    OperationsChapterState,
    "index" | "source" | "availability" | "provenance" | "focusEntityId" | "urbanField" | "world"
  >
> = {
  overview: {
    id: "overview",
    label: "01 / NETWORK OVERVIEW",
    title: "Keep the city moving.",
    description: "One operational field for demand, supply, and the decisions connecting them.",
    activeMetric: "network pressure",
  },
  pressure: {
    id: "pressure",
    label: "02 / URBAN PRESSURE",
    title: "Read the pressure before it becomes a queue.",
    description: "Spatial demand and courier supply move as one field, not a stack of counters.",
    activeMetric: "pressure × supply",
  },
  risk: {
    id: "risk",
    label: "03 / SLA RISK",
    title: "Find the edge of the promise.",
    description: "Risk signals surface beside the zones and routes that can still absorb them.",
    activeMetric: "SLA risk index",
  },
  strategy: {
    id: "strategy",
    label: "04 / STRATEGY",
    title: "Make the next decision inspectable.",
    description: "Strategy state, solver latency, and alternatives share one decision surface.",
    activeMetric: "strategy response",
  },
  live: {
    id: "live",
    label: "05 / LIVE OPERATIONS",
    title: "Stay close to the handoff.",
    description:
      "Routes, queue state, lifecycle, and activity remain actionable in the same world.",
    activeMetric: "dispatch latency",
  },
  replay: {
    id: "replay",
    label: "06 / SIMULATION + REPLAY",
    title: "Move through what happened and what could happen.",
    description: "Recorded and simulated time become a navigable operational layer.",
    activeMetric: "temporal fidelity",
  },
  research: {
    id: "research",
    label: "07 / RELIABILITY + RESEARCH",
    title: "Leave an evidence trail behind every route.",
    description:
      "Reliability, lineage, and twin fidelity stay visible without breaking the spatial frame.",
    activeMetric: "twin fidelity",
  },
};

const WORLD_BY_CHAPTER: Record<
  OperationsChapterId,
  Omit<UrbanWorldFrame, "chapter" | "progress" | "focusStrength">
> = {
  overview: {
    cameraMode: "overview",
    sceneRole: "hero",
    instrumentation: "minimal",
    layerVisibility: { core: 1, cells: 0.72, flows: 0.58, nodes: 0.42, riskZones: 0.28 },
    lighting: { key: 1, ambient: 0.72, risk: 0.28 },
  },
  pressure: {
    cameraMode: "pressure-close",
    sceneRole: "field",
    instrumentation: "floating",
    layerVisibility: { core: 0.78, cells: 1, flows: 0.82, nodes: 0.58, riskZones: 0.46 },
    lighting: { key: 0.88, ambient: 0.68, risk: 0.4 },
  },
  risk: {
    cameraMode: "risk-hotspot",
    sceneRole: "backdrop",
    instrumentation: "hero",
    layerVisibility: { core: 0.72, cells: 0.78, flows: 0.74, nodes: 0.92, riskZones: 1 },
    lighting: { key: 0.76, ambient: 0.58, risk: 1 },
  },
  strategy: {
    cameraMode: "strategy-pullback",
    sceneRole: "evidence",
    instrumentation: "wall",
    layerVisibility: { core: 0.9, cells: 0.56, flows: 1, nodes: 0.74, riskZones: 0.58 },
    lighting: { key: 0.92, ambient: 0.78, risk: 0.5 },
  },
  live: {
    cameraMode: "live-inspection",
    sceneRole: "inspection",
    instrumentation: "dock",
    layerVisibility: { core: 0.58, cells: 0.48, flows: 1, nodes: 1, riskZones: 0.7 },
    lighting: { key: 1, ambient: 0.64, risk: 0.56 },
  },
  replay: {
    cameraMode: "replay-tracking",
    sceneRole: "field",
    instrumentation: "dock",
    layerVisibility: { core: 0.82, cells: 0.74, flows: 0.88, nodes: 0.58, riskZones: 0.5 },
    lighting: { key: 0.88, ambient: 0.72, risk: 0.42 },
  },
  research: {
    cameraMode: "research-stable",
    sceneRole: "evidence",
    instrumentation: "wall",
    layerVisibility: { core: 0.68, cells: 0.44, flows: 0.52, nodes: 0.72, riskZones: 0.62 },
    lighting: { key: 0.8, ambient: 0.86, risk: 0.36 },
  },
};

export function toOperationsChapterState(
  snapshot: OperationsSnapshot,
  selectedOrderId: string | null = null,
): readonly OperationsChapterState[] {
  const urbanField = toUrbanFieldState(snapshot);
  const provenance = snapshot.source === "live" ? "snapshot-derived" : "deterministic demo state";
  return OPERATIONS_CHAPTER_ORDER.map((id, index) => ({
    ...CHAPTER_META[id],
    index,
    source: snapshot.source,
    availability: snapshot.availability,
    provenance,
    focusEntityId: selectedOrderId,
    urbanField,
    world: {
      chapter: id,
      progress: 0,
      focusStrength: 0.78,
      ...WORLD_BY_CHAPTER[id],
    },
  }));
}

export function interpolateUrbanWorldFrame(
  chapters: readonly OperationsChapterState[],
  progress: number,
): UrbanWorldFrame {
  const bounded = clamp(progress);
  const scaled = bounded * Math.max(chapters.length - 1, 1);
  const index = Math.min(chapters.length - 1, Math.floor(scaled));
  const nextIndex = Math.min(chapters.length - 1, index + 1);
  const local = scaled - index;
  const current = chapters[index]?.world;
  const next = chapters[nextIndex]?.world ?? current;
  if (!current || !next) {
    return {
      chapter: "overview",
      progress: bounded,
      cameraMode: "overview",
      sceneRole: "hero",
      instrumentation: "minimal",
      focusStrength: 0.78,
      layerVisibility: { core: 1, cells: 0.72, flows: 0.58, nodes: 0.42, riskZones: 0.28 },
      lighting: { key: 1, ambient: 0.72, risk: 0.28 },
    };
  }
  const blend = (a: number, b: number) => a + (b - a) * local;
  return {
    ...current,
    progress: bounded,
    focusStrength: blend(current.focusStrength, next.focusStrength),
    layerVisibility: {
      core: blend(current.layerVisibility.core, next.layerVisibility.core),
      cells: blend(current.layerVisibility.cells, next.layerVisibility.cells),
      flows: blend(current.layerVisibility.flows, next.layerVisibility.flows),
      nodes: blend(current.layerVisibility.nodes, next.layerVisibility.nodes),
      riskZones: blend(current.layerVisibility.riskZones, next.layerVisibility.riskZones),
    },
    lighting: {
      key: blend(current.lighting.key, next.lighting.key),
      ambient: blend(current.lighting.ambient, next.lighting.ambient),
      risk: blend(current.lighting.risk, next.lighting.risk),
    },
  };
}
