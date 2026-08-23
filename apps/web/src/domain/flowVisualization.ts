import type { DataSourceMode, GeoPoint, OperationsSnapshot } from "./model";

export type FlowFreshness = "fresh" | "stale" | "empty" | "unavailable";
export type FlowDirection = "northbound" | "southbound" | "eastbound" | "westbound" | "local";

export interface FlowArc {
  flowId: string;
  sourceZone: string;
  targetZone: string;
  sourcePoint: GeoPoint;
  targetPoint: GeoPoint;
  orderCount: number;
  routeCount: number;
  direction: FlowDirection;
  recencyMinutes: number | null;
  confidence: number;
  evidenceOrderIds: readonly string[];
}

export interface FlowProjection {
  source: DataSourceMode;
  sourceLabel: string;
  freshness: FlowFreshness;
  generatedAt: string;
  derivedFrom: "order-route-records";
  flows: readonly FlowArc[];
  totalOrders: number;
  routeBearingOrders: number;
  representedOrders: number;
  projectionDigest: string;
  emptyReason: string | null;
}

const SOURCE_LABELS: Record<DataSourceMode, string> = {
  live: "LIVE source",
  demo: "DEMO source",
  replay: "REPLAY source",
  simulation: "SIMULATION source",
};

interface FlowAccumulator {
  sourceZone: string;
  targetZone: string;
  sourceX: number;
  sourceY: number;
  targetX: number;
  targetY: number;
  dx: number;
  dy: number;
  orderIds: string[];
  recencyTotal: number;
  recencySamples: number;
  confidenceTotal: number;
}

export function projectDataBackedFlows(
  snapshot: OperationsSnapshot,
  now: Date = new Date(),
): FlowProjection {
  const sourceLabel = SOURCE_LABELS[snapshot.source];
  const freshness =
    snapshot.availability === "unavailable"
      ? "unavailable"
      : freshnessOf(snapshot.generatedAt, now);
  const routeOrders = snapshot.orders.filter((order) => order.route.length >= 2);
  if (freshness === "unavailable") {
    return emptyProjection(
      snapshot,
      sourceLabel,
      "Flow records are unavailable from this source.",
      "unavailable",
    );
  }
  if (!routeOrders.length) {
    const reason = snapshot.orders.length
      ? "No order route records are available to project into flows."
      : "No order records are present in the selected source.";
    return emptyProjection(snapshot, sourceLabel, reason, freshness);
  }

  const anchors = createZoneAnchors(snapshot);
  const recencyMinutes = recencyFor(snapshot.generatedAt, now);
  const accumulators = new Map<string, FlowAccumulator>();
  for (const order of routeOrders) {
    const sourcePoint = order.route[0];
    const targetPoint = order.route[order.route.length - 1];
    if (!sourcePoint || !targetPoint) continue;
    const sourceZone = zoneForPoint(sourcePoint, anchors);
    const targetZone = zoneForPoint(targetPoint, anchors);
    const key = `${sourceZone.label}->${targetZone.label}`;
    const confidence = confidenceFor(order.route.length, sourceZone.matched, targetZone.matched);
    const current = accumulators.get(key) ?? {
      sourceZone: sourceZone.label,
      targetZone: targetZone.label,
      sourceX: 0,
      sourceY: 0,
      targetX: 0,
      targetY: 0,
      dx: 0,
      dy: 0,
      orderIds: [],
      recencyTotal: 0,
      recencySamples: 0,
      confidenceTotal: 0,
    };
    current.sourceX += sourcePoint.x;
    current.sourceY += sourcePoint.y;
    current.targetX += targetPoint.x;
    current.targetY += targetPoint.y;
    current.dx += targetPoint.x - sourcePoint.x;
    current.dy += targetPoint.y - sourcePoint.y;
    current.orderIds.push(order.id);
    if (recencyMinutes !== null) {
      current.recencyTotal += recencyMinutes;
      current.recencySamples += 1;
    }
    current.confidenceTotal += confidence;
    accumulators.set(key, current);
  }

  const flows = [...accumulators.values()]
    .map((flow) => toFlowArc(flow))
    .sort(
      (left, right) =>
        right.orderCount - left.orderCount || left.flowId.localeCompare(right.flowId),
    );
  const representedOrders = flows.reduce((sum, flow) => sum + flow.orderCount, 0);
  return {
    source: snapshot.source,
    sourceLabel,
    freshness,
    generatedAt: snapshot.generatedAt,
    derivedFrom: "order-route-records",
    flows,
    totalOrders: snapshot.orders.length,
    routeBearingOrders: routeOrders.length,
    representedOrders,
    projectionDigest: digest({
      source: snapshot.source,
      generatedAt: snapshot.generatedAt,
      flows: flows.map(({ flowId, orderCount, evidenceOrderIds }) => ({
        flowId,
        orderCount,
        evidenceOrderIds,
      })),
    }),
    emptyReason: flows.length
      ? null
      : "No order route records are available to project into flows.",
  };
}

function toFlowArc(flow: FlowAccumulator): FlowArc {
  const orderCount = flow.orderIds.length;
  const sourcePoint = { x: flow.sourceX / orderCount, y: flow.sourceY / orderCount };
  const targetPoint = { x: flow.targetX / orderCount, y: flow.targetY / orderCount };
  return {
    flowId: `${slug(flow.sourceZone)}-to-${slug(flow.targetZone)}`,
    sourceZone: flow.sourceZone,
    targetZone: flow.targetZone,
    sourcePoint,
    targetPoint,
    orderCount,
    routeCount: orderCount,
    direction: directionFor(flow.dx, flow.dy),
    recencyMinutes:
      flow.recencySamples > 0
        ? Math.max(0, Math.round(flow.recencyTotal / flow.recencySamples))
        : null,
    confidence: Math.min(1, Math.max(0, flow.confidenceTotal / orderCount)),
    evidenceOrderIds: [...flow.orderIds].sort(),
  };
}

interface ZoneAnchor {
  label: string;
  point: GeoPoint;
  matched: boolean;
}

function createZoneAnchors(snapshot: OperationsSnapshot): ZoneAnchor[] {
  const byZone = new Map<string, GeoPoint>();
  for (const courier of snapshot.couriers) {
    if (!byZone.has(courier.zone)) byZone.set(courier.zone, courier.position);
  }
  if (byZone.size) {
    return [...byZone.entries()].map(([label, point]) => ({ label, point, matched: true }));
  }
  return [
    { label: "West area", point: { x: 20, y: 50 }, matched: false },
    { label: "Central area", point: { x: 50, y: 50 }, matched: false },
    { label: "East area", point: { x: 80, y: 50 }, matched: false },
  ];
}

function zoneForPoint(point: GeoPoint, anchors: readonly ZoneAnchor[]): ZoneAnchor {
  return anchors.reduce((closest, anchor) =>
    distance(point, anchor.point) < distance(point, closest.point) ? anchor : closest,
  );
}

function confidenceFor(
  routeLength: number,
  sourceMatched: boolean,
  targetMatched: boolean,
): number {
  const geometry = routeLength >= 3 ? 0.95 : 0.88;
  const lineage = sourceMatched && targetMatched ? 0.05 : 0;
  return Math.min(1, geometry + lineage);
}

function directionFor(dx: number, dy: number): FlowDirection {
  if (Math.abs(dx) < 8 && Math.abs(dy) < 8) return "local";
  if (Math.abs(dx) >= Math.abs(dy)) return dx >= 0 ? "eastbound" : "westbound";
  return dy <= 0 ? "northbound" : "southbound";
}

function distance(left: GeoPoint, right: GeoPoint): number {
  return (left.x - right.x) ** 2 + (left.y - right.y) ** 2;
}

function freshnessOf(generatedAt: string, now: Date): FlowFreshness {
  const generated = Date.parse(generatedAt);
  if (!Number.isFinite(generated)) return "empty";
  return now.getTime() - generated <= 15 * 60 * 1000 ? "fresh" : "stale";
}

function recencyFor(generatedAt: string, now: Date): number | null {
  const generated = Date.parse(generatedAt);
  if (!Number.isFinite(generated)) return null;
  return Math.max(0, Math.round((now.getTime() - generated) / 60_000));
}

function emptyProjection(
  snapshot: OperationsSnapshot,
  sourceLabel: string,
  emptyReason: string,
  freshness: FlowFreshness = "empty",
): FlowProjection {
  return {
    source: snapshot.source,
    sourceLabel,
    freshness,
    generatedAt: snapshot.generatedAt,
    derivedFrom: "order-route-records",
    flows: [],
    totalOrders: snapshot.orders.length,
    routeBearingOrders: 0,
    representedOrders: 0,
    projectionDigest: digest({
      source: snapshot.source,
      generatedAt: snapshot.generatedAt,
      emptyReason,
    }),
    emptyReason,
  };
}

function slug(value: string): string {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
}

function digest(value: unknown): string {
  const encoded = JSON.stringify(value);
  let hash = 2166136261;
  for (const character of encoded) hash = Math.imul(hash ^ character.charCodeAt(0), 16777619);
  return (hash >>> 0).toString(16).padStart(8, "0").repeat(8);
}
