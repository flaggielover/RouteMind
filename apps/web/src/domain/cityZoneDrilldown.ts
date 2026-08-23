import type { DataSourceMode, OperationsSnapshot } from "./model";

export type DrilldownFreshness = "fresh" | "stale" | "empty" | "unavailable";
export type DrilldownAggregation = "city" | "zone";

export interface CityZoneSignal {
  zoneId: string;
  zoneLabel: string;
  orderCount: number;
  merchantCount: number;
  courierCount: number;
  availableCourierCount: number;
  densityPer100: number;
  supplyGap: number;
  riskIndex: number;
  routeCount: number;
}

export interface CityZoneProjection {
  source: DataSourceMode;
  sourceLabel: string;
  freshness: DrilldownFreshness;
  generatedAt: string;
  zoom: number;
  aggregation: DrilldownAggregation;
  derivedFromSnapshot: true;
  zones: readonly CityZoneSignal[];
  totalOrders: number;
  totalMerchants: number;
  totalCouriers: number;
  totalRoutes: number;
}

const SOURCE_LABELS: Record<DataSourceMode, string> = {
  live: "LIVE source",
  demo: "DEMO source",
  replay: "REPLAY source",
  simulation: "SIMULATION source",
};

export function projectCityZoneDrilldown(
  snapshot: OperationsSnapshot,
  zoom: number,
  now: Date = new Date(),
): CityZoneProjection {
  const sourceLabel = SOURCE_LABELS[snapshot.source];
  const freshness =
    snapshot.availability === "unavailable" ? "unavailable" : freshnessOf(snapshot, now);
  const zoneLabels = [...new Set(snapshot.couriers.map((courier) => courier.zone).filter(Boolean))];
  const empty = !snapshot.orders.length && !snapshot.couriers.length && !snapshot.merchants.length;
  if (empty || freshness === "unavailable") {
    return {
      source: snapshot.source,
      sourceLabel,
      freshness: empty ? "empty" : freshness,
      generatedAt: snapshot.generatedAt,
      zoom,
      aggregation: zoom <= 8 ? "city" : "zone",
      derivedFromSnapshot: true,
      zones: [],
      totalOrders: 0,
      totalMerchants: 0,
      totalCouriers: 0,
      totalRoutes: 0,
    };
  }
  const zones = zoneLabels.map((zone, index) => buildZone(snapshot, zone, index, zoneLabels));
  const normalizedZones = zoom <= 8 ? [mergeCity(zones)] : zones;
  return {
    source: snapshot.source,
    sourceLabel,
    freshness,
    generatedAt: snapshot.generatedAt,
    zoom,
    aggregation: zoom <= 8 ? "city" : "zone",
    derivedFromSnapshot: true,
    zones: normalizedZones,
    totalOrders: snapshot.orders.length,
    totalMerchants: snapshot.merchants.length,
    totalCouriers: snapshot.couriers.length,
    totalRoutes: snapshot.orders.filter((order) => order.route.length > 1).length,
  };
}

function buildZone(
  snapshot: OperationsSnapshot,
  zone: string,
  zoneIndex: number,
  zones: readonly string[],
): CityZoneSignal {
  const orders = snapshot.orders.filter(
    (order) => bucketForOrder(order.route[0]?.x ?? 50, zones.length) === zoneIndex,
  );
  const couriers = snapshot.couriers.filter((courier) => courier.zone === zone);
  const merchants = snapshot.merchants.filter((_, index) => index % zones.length === zoneIndex);
  const availableCourierCount = couriers.filter((courier) => courier.status === "available").length;
  const densityPer100 = (orders.length / Math.max(1, merchants.length)) * 100;
  const supplyGap = Math.max(0, orders.length - availableCourierCount);
  const riskIndex = Math.min(
    1,
    (orders.filter((order) => order.priority === "priority").length / Math.max(1, orders.length)) *
      0.6 +
      (supplyGap / Math.max(1, orders.length)) * 0.4,
  );
  return {
    zoneId: zone.toLowerCase().replaceAll(" ", "-"),
    zoneLabel: zone,
    orderCount: orders.length,
    merchantCount: merchants.length,
    courierCount: couriers.length,
    availableCourierCount,
    densityPer100,
    supplyGap,
    riskIndex,
    routeCount: orders.filter((order) => order.route.length > 1).length,
  };
}

function mergeCity(zones: readonly CityZoneSignal[]): CityZoneSignal {
  const orderCount = zones.reduce((sum, zone) => sum + zone.orderCount, 0);
  const merchantCount = zones.reduce((sum, zone) => sum + zone.merchantCount, 0);
  const courierCount = zones.reduce((sum, zone) => sum + zone.courierCount, 0);
  const availableCourierCount = zones.reduce((sum, zone) => sum + zone.availableCourierCount, 0);
  return {
    zoneId: "city-total",
    zoneLabel: "City total",
    orderCount,
    merchantCount,
    courierCount,
    availableCourierCount,
    densityPer100: (orderCount / Math.max(1, merchantCount)) * 100,
    supplyGap: Math.max(0, orderCount - availableCourierCount),
    riskIndex: Math.min(
      1,
      zones.reduce((sum, zone) => sum + zone.riskIndex, 0) / Math.max(1, zones.length),
    ),
    routeCount: zones.reduce((sum, zone) => sum + zone.routeCount, 0),
  };
}

function bucketForOrder(x: number, count: number): number {
  if (count <= 1) return 0;
  return Math.min(count - 1, Math.floor((Math.max(0, Math.min(100, x)) / 100) * count));
}

function freshnessOf(snapshot: OperationsSnapshot, now: Date): DrilldownFreshness {
  const generated = Date.parse(snapshot.generatedAt);
  if (!Number.isFinite(generated)) return "empty";
  return now.getTime() - generated <= 15 * 60 * 1000 ? "fresh" : "stale";
}
