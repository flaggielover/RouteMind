import type { DataSourceMode, OperationsSnapshot } from "./model";
import { projectCityZoneDrilldown, type DrilldownFreshness } from "./cityZoneDrilldown";
import { projectDataBackedFlows, type FlowArc } from "./flowVisualization";

export type GeoLayerId =
  | "orders"
  | "courier-supply"
  | "supply-gap"
  | "sla-risk"
  | "congestion"
  | "travel-degradation"
  | "integrity"
  | "utilization"
  | "flow";

export type GeoLayerAvailability = "available" | "unavailable";

export interface GeoLayerDefinition {
  id: GeoLayerId;
  label: string;
  unit: string;
  scale: string;
  availability: GeoLayerAvailability;
  detail: string;
}

export interface GeoLayerValue {
  key: string;
  label: string;
  value: number | null;
  displayValue: string;
  evidenceCount: number;
}

export interface GeoAnalyticalLayersProjection {
  source: DataSourceMode;
  sourceLabel: string;
  freshness: DrilldownFreshness;
  generatedAt: string;
  definitions: readonly GeoLayerDefinition[];
  values: Readonly<Record<GeoLayerId, readonly GeoLayerValue[]>>;
  flowRecords: readonly FlowArc[];
}

const SOURCE_LABELS: Record<DataSourceMode, string> = {
  live: "LIVE source",
  demo: "DEMO source",
  replay: "REPLAY source",
  simulation: "SIMULATION source",
};

const BASE_DEFINITIONS: readonly GeoLayerDefinition[] = [
  {
    id: "orders",
    label: "Order demand",
    unit: "orders / zone",
    scale: "0–N orders",
    availability: "available",
    detail: "Order records grouped by the selected city/zone projection.",
  },
  {
    id: "courier-supply",
    label: "Courier supply",
    unit: "available couriers / zone",
    scale: "0–N couriers",
    availability: "available",
    detail: "Couriers with status available in the selected snapshot.",
  },
  {
    id: "supply-gap",
    label: "Supply gap",
    unit: "uncovered orders / zone",
    scale: "0–N orders",
    availability: "available",
    detail: "Orders minus available couriers, bounded at zero.",
  },
  {
    id: "sla-risk",
    label: "SLA risk",
    unit: "% risk / zone",
    scale: "0–100%",
    availability: "available",
    detail: "Bounded priority and supply-gap risk from the zone projection.",
  },
  {
    id: "congestion",
    label: "Congestion",
    unit: "unavailable",
    scale: "No travel metric",
    availability: "unavailable",
    detail: "No congestion or segment-speed record is present in this snapshot.",
  },
  {
    id: "travel-degradation",
    label: "Travel degradation",
    unit: "unavailable",
    scale: "No travel metric",
    availability: "unavailable",
    detail: "No provider travel comparison or degradation signal is present.",
  },
  {
    id: "integrity",
    label: "Location integrity",
    unit: "stale/offline couriers / zone",
    scale: "0–N couriers",
    availability: "unavailable",
    detail: "Enabled only when courier integrity metadata is present.",
  },
  {
    id: "utilization",
    label: "Courier utilization",
    unit: "% on route / zone",
    scale: "0–100%",
    availability: "available",
    detail: "On-route couriers divided by couriers represented in the zone.",
  },
  {
    id: "flow",
    label: "Order flow",
    unit: "orders / direction",
    scale: "0–N orders",
    availability: "available",
    detail: "RM-224 route-record flow aggregates with explicit order evidence.",
  },
];

export function projectGeoAnalyticalLayers(
  snapshot: OperationsSnapshot,
  now: Date = new Date(),
): GeoAnalyticalLayersProjection {
  const drilldown = projectCityZoneDrilldown(snapshot, 11, now);
  const flowProjection = projectDataBackedFlows(snapshot, now);
  const integrityAvailable = snapshot.couriers.some(
    (courier) =>
      courier.stale !== undefined ||
      courier.sequence !== undefined ||
      courier.observedAt !== undefined ||
      courier.online !== undefined,
  );
  const definitions: readonly GeoLayerDefinition[] = BASE_DEFINITIONS.map((definition) =>
    definition.id === "integrity"
      ? {
          ...definition,
          availability: integrityAvailable ? ("available" as const) : ("unavailable" as const),
        }
      : definition,
  );
  const values = {
    orders: drilldown.zones.map((zone) =>
      numberValue(zone.zoneId, zone.zoneLabel, zone.orderCount, zone.orderCount),
    ),
    "courier-supply": drilldown.zones.map((zone) =>
      numberValue(zone.zoneId, zone.zoneLabel, zone.availableCourierCount, zone.courierCount),
    ),
    "supply-gap": drilldown.zones.map((zone) =>
      numberValue(zone.zoneId, zone.zoneLabel, zone.supplyGap, zone.orderCount),
    ),
    "sla-risk": drilldown.zones.map((zone) =>
      numberValue(zone.zoneId, zone.zoneLabel, Math.round(zone.riskIndex * 100), zone.orderCount),
    ),
    congestion: [],
    "travel-degradation": [],
    integrity: integrityAvailable
      ? drilldown.zones.map((zone) => {
          const couriers = snapshot.couriers.filter((courier) => courier.zone === zone.zoneLabel);
          const incidents = couriers.filter(
            (courier) =>
              courier.stale === true || courier.online === false || courier.status === "offline",
          ).length;
          return numberValue(zone.zoneId, zone.zoneLabel, incidents, couriers.length);
        })
      : [],
    utilization: drilldown.zones.map((zone) => {
      const utilized = Math.max(0, zone.courierCount - zone.availableCourierCount);
      const value = zone.courierCount ? Math.round((utilized / zone.courierCount) * 100) : 0;
      return numberValue(zone.zoneId, zone.zoneLabel, value, zone.courierCount);
    }),
    flow: flowProjection.flows.map((flow) =>
      numberValue(
        `${flow.flowId}-flow`,
        `${flow.sourceZone} → ${flow.targetZone}`,
        flow.orderCount,
        flow.orderCount,
      ),
    ),
  } satisfies Record<GeoLayerId, readonly GeoLayerValue[]>;
  return {
    source: snapshot.source,
    sourceLabel: SOURCE_LABELS[snapshot.source],
    freshness: drilldown.freshness,
    generatedAt: snapshot.generatedAt,
    definitions,
    values,
    flowRecords: flowProjection.flows,
  };
}

function numberValue(
  key: string,
  label: string,
  value: number,
  evidenceCount: number,
): GeoLayerValue {
  return {
    key,
    label,
    value,
    displayValue: `${value}`,
    evidenceCount,
  };
}
