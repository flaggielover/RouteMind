export const roles = ["operations", "strategy", "customer", "merchant", "courier"] as const;

export type Role = (typeof roles)[number];

export type DataSourceMode = "live" | "demo" | "replay" | "simulation";
export type DataAvailability = "loading" | "ready" | "degraded" | "unavailable";
export type ClockDomain = "WALL" | "SIMULATED" | "REPLAY";

export type OrderStatus =
  | "CREATED"
  | "CONFIRMED"
  | "PREPARING"
  | "READY_FOR_PICKUP"
  | "ASSIGNED"
  | "ACCEPTED"
  | "ARRIVED"
  | "PICKED_UP"
  | "OUT_FOR_DELIVERY"
  | "DELIVERED"
  | "ASSIGNMENT_TIMED_OUT"
  | "ASSIGNMENT_REJECTED"
  | "REASSIGNMENT_PENDING"
  | "COMPENSATING"
  | "COMPENSATED"
  | "CANCELLED";

export type ServiceStatus = "healthy" | "unavailable" | "checking";

export interface OrderEvent {
  status: OrderStatus;
  label: string;
  at: string;
  completed: boolean;
}

export interface GeoPoint {
  x: number;
  y: number;
}

export interface Order {
  id: string;
  shortId: string;
  customerName: string;
  merchantName: string;
  status: OrderStatus;
  eta: string;
  age: string;
  priority: "standard" | "priority";
  version?: number;
  destination: string;
  route: readonly GeoPoint[];
  events: readonly OrderEvent[];
}

export interface Courier {
  id: string;
  name: string;
  status: "available" | "on_route" | "offline";
  zone: string;
  eta: string;
  position: GeoPoint;
  sequence?: number;
  observedAt?: string;
  ingestedAt?: string;
  online?: boolean;
  stale?: boolean;
}

export interface Merchant {
  id: string;
  name: string;
  prepMinutes: number;
  queue: number;
  status: "open" | "busy" | "paused";
}

export interface DispatchDecision {
  strategy: string;
  version: string;
  selectedCourier: string;
  latencyMs: number;
  rationale: string;
}

export interface DispatchDecisionLedgerRecord {
  decisionId: string;
  requestId: string;
  idempotencyKey?: string;
  orderId?: string;
  courierId?: string;
  strategy: string;
  strategyVersion: string;
  referenceDataId: string;
  clockDomain: ClockDomain;
  inputDigest: string;
  outputDigest: string;
  inputSnapshotDigest: string;
  outputSnapshotDigest: string;
  inputSnapshotJson?: string;
  outputSnapshotJson?: string;
  createdAt: string;
}

export interface ServiceHealth {
  service: "business-api" | "compute-api";
  label: string;
  status: ServiceStatus;
  endpoint: string;
  checkedAt: string;
  detail: string;
}

export type SimulationStatus = "paused" | "running" | "completed";

export interface SimulationEvent {
  eventId: string;
  eventType: string;
  simulatedTimeSeconds: number;
  commandId: string;
  details: readonly (readonly [string, string])[];
}

export interface SimulationSnapshot {
  clockDomain: "SIMULATED";
  scenarioId: string;
  seed: number;
  strategy: string;
  strategyVersion: string;
  status: SimulationStatus;
  speed: number;
  simulatedTimeSeconds: number;
  tick: number;
  generation: number;
  eventCount: number;
  lastCommandId: string | null;
  replayDigest: string;
  events: readonly SimulationEvent[];
}

export type ReplayStatus = "verifying" | "ready" | "playing" | "paused" | "invalid";

export interface ReplayEvent {
  eventId: string;
  eventType: string;
  simulatedTimeSeconds: number;
  details: readonly (readonly [string, string])[];
}

export interface ReplaySnapshot {
  clockDomain: "REPLAY";
  artifactId: string;
  scenarioId: string;
  seed: number;
  status: ReplayStatus;
  verified: boolean;
  cursorSeconds: number;
  durationSeconds: number;
  speed: number;
  replayDigest: string;
  provenance: string;
  events: readonly ReplayEvent[];
  visibleEvents: readonly ReplayEvent[];
  verificationError: string | null;
}

export interface WhatIfVariantInput {
  variantId: string;
  label: string;
  demandMultiplier: number;
  supplyDelta: number;
  preparationDelayTicks: number;
  trafficMultiplier: number;
  strategy: string;
  riskMultiplier: number;
}

export interface WhatIfMetric {
  variantId: string;
  label: string;
  strategy: string;
  strategyVersion: string;
  requestCount: number;
  assignedCount: number;
  assignmentRate: number;
  simulatedEndTick: number;
  simulatedDurationSeconds: number;
  riskIndex: number;
  replayDigest: string;
  manifestDigest: string;
  outputDigest: string;
  observedRuntimeMillis: number;
}

export interface WhatIfComparison {
  source: "what-if";
  claimLabel: "scenario comparison; not a causal production claim";
  recordedRunId: string;
  comparisonDigest: string;
  scenarioId: string;
  seed: number;
  results: readonly WhatIfMetric[];
}

export interface OperationsSnapshot {
  source: DataSourceMode;
  clockDomain: ClockDomain;
  availability: DataAvailability;
  sourceDetail: string;
  generatedAt: string;
  orders: readonly Order[];
  couriers: readonly Courier[];
  merchants: readonly Merchant[];
  dispatch: DispatchDecision;
  decisionLedger?: DispatchDecisionLedgerRecord;
  health: readonly ServiceHealth[];
  simulation?: SimulationSnapshot;
  replay?: ReplaySnapshot;
}

export interface OperationsDataSource {
  getSnapshot(): OperationsSnapshot;
  loadSnapshot?: () => Promise<OperationsSnapshot>;
  controlSimulation?: (command: SimulationCommand) => Promise<OperationsSnapshot>;
  controlReplay?: (command: ReplayCommand) => Promise<OperationsSnapshot>;
}

export type SimulationAction =
  "start" | "pause" | "resume" | "step" | "reset" | "speed" | "scenario" | "seed" | "strategy";

export interface SimulationCommand {
  commandId: string;
  action: SimulationAction;
  seconds?: number;
  speed?: number;
  scenarioId?: string;
  seed?: number;
  strategy?: string;
}

export type ReplayAction = "play" | "pause" | "seek" | "step" | "speed" | "reset";

export interface ReplayCommand {
  commandId: string;
  action: ReplayAction;
  seconds?: number;
  speed?: number;
}
