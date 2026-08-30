import type { GeoPoint, OperationsSnapshot } from "../domain/model";

export type UrbanFieldNodeKind = "order" | "courier" | "merchant" | "risk";

export interface UrbanFieldSpatialState {
  cells?: readonly {
    id: string;
    center: GeoPoint;
    intensity: number;
    risk?: number;
  }[];
  nodes?: readonly {
    id: string;
    kind: UrbanFieldNodeKind;
    position: GeoPoint;
    value?: number;
    risk?: number;
  }[];
  flows?: readonly {
    id: string;
    from: GeoPoint;
    to: GeoPoint;
    value: number;
    risk?: number;
  }[];
  zones?: readonly {
    id: string;
    label: string;
    center: GeoPoint;
    radius: number;
    risk: number;
    orderPressure: number;
    courierSupply: number;
    selected?: boolean;
  }[];
}

export interface UrbanFieldState {
  mode: OperationsSnapshot["source"];
  pressure: number;
  supply: number;
  risk: number;
  traffic: number;
  strategy: string;
  twinFidelity: number;
  activityRate: number;
  provenance: "snapshot-derived" | "visual-demo";
  spatial?: UrbanFieldSpatialState;
}

function clamp(value: number, min = 0, max = 1): number {
  return Math.min(max, Math.max(min, value));
}

function pointForOrder(snapshot: OperationsSnapshot, index: number): GeoPoint {
  const routePoint = snapshot.orders[index]?.route[0];
  if (routePoint) return routePoint;
  return {
    x: 15 + ((index * 29) % 70),
    y: 18 + ((index * 43) % 64),
  };
}

const CLUSTER_CELL_OFFSETS = [
  [0, 0],
  [-1, 0],
  [1, 0],
  [-0.5, -1],
  [0.5, -1],
  [-0.5, 1],
  [0.5, 1],
  [-1.5, -1],
  [1.5, -1],
  [-1.5, 1],
  [1.5, 1],
  [-1, -2],
  [0, -2],
  [1, -2],
  [-1, 2],
  [0, 2],
  [1, 2],
] as const;

function bucketForPoint(point: GeoPoint, count: number): number {
  if (count <= 1) return 0;
  return Math.min(count - 1, Math.floor((clamp(point.x, 0, 100) / 100) * count));
}

function createSpatialState(snapshot: OperationsSnapshot, risk: number): UrbanFieldSpatialState {
  const zoneLabels = [...new Set(snapshot.couriers.map((courier) => courier.zone).filter(Boolean))];
  const normalizedZoneLabels = zoneLabels.length ? zoneLabels : ["City core"];
  const zoneSignals = normalizedZoneLabels.map((label, zoneIndex) => {
    const couriers = snapshot.couriers.filter((courier) => courier.zone === label);
    const orders = snapshot.orders.filter(
      (order) =>
        bucketForPoint(
          order.route[0] ?? pointForOrder(snapshot, zoneIndex),
          normalizedZoneLabels.length,
        ) === zoneIndex,
    );
    const merchants = snapshot.merchants.filter(
      (_, merchantIndex) => merchantIndex % normalizedZoneLabels.length === zoneIndex,
    );
    const availableCouriers = couriers.filter((courier) => courier.status === "available").length;
    const center = couriers.length
      ? {
          x: couriers.reduce((sum, courier) => sum + courier.position.x, 0) / couriers.length,
          y: couriers.reduce((sum, courier) => sum + courier.position.y, 0) / couriers.length,
        }
      : { x: 24 + (zoneIndex % 3) * 26, y: 31 + ((zoneIndex * 29) % 42) };
    const orderPressure = clamp(orders.length / Math.max(2, merchants.length * 2));
    const courierSupply = couriers.length ? clamp(availableCouriers / couriers.length) : 0;
    const supplyGap = Math.max(0, orders.length - availableCouriers);
    const priorityShare =
      orders.filter((order) => order.priority === "priority" && order.status !== "DELIVERED")
        .length / Math.max(1, orders.length);
    const zoneRisk = clamp(priorityShare * 0.62 + (supplyGap / Math.max(1, orders.length)) * 0.38);
    return {
      id: label.toLowerCase().replaceAll(" ", "-"),
      label,
      center,
      radius: 14 + orderPressure * 5,
      risk: zoneRisk,
      orderPressure,
      courierSupply,
    };
  });
  const selectedZoneId = zoneSignals.reduce(
    (selected, zone) => (zone.risk > selected.risk ? zone : selected),
    zoneSignals[0],
  )?.id;

  const nodes = [
    ...snapshot.orders.map((order, index) => ({
      id: order.id,
      kind:
        order.priority === "priority" && order.status !== "DELIVERED"
          ? ("risk" as const)
          : ("order" as const),
      position: pointForOrder(snapshot, index),
      value: order.priority === "priority" ? 0.85 : 0.55,
      risk: order.priority === "priority" && order.status !== "DELIVERED" ? 0.8 : 0.2,
    })),
    ...snapshot.couriers.map((courier) => ({
      id: courier.id,
      kind: "courier" as const,
      position: courier.position,
      value: courier.status === "available" ? 0.78 : 0.52,
      risk: courier.status === "offline" || courier.stale ? 0.72 : 0.08,
    })),
    ...snapshot.merchants.map((merchant, index) => {
      const zone = zoneSignals[index % zoneSignals.length];
      return {
        id: merchant.id,
        kind: "merchant" as const,
        position: {
          x: clamp((zone?.center.x ?? 50) + ((index % 2) * 2 - 1) * 3.8, 4, 96),
          y: clamp((zone?.center.y ?? 50) + ((index % 3) - 1) * 3.2, 4, 96),
        },
        value: clamp(merchant.queue / 5),
        risk: clamp(merchant.prepMinutes / 24),
      };
    }),
  ];

  const flows = snapshot.orders.flatMap((order, index) => {
    const from = order.route[0] ?? pointForOrder(snapshot, index);
    const to = order.route.at(-1) ?? { x: 80 - (index % 3) * 8, y: 28 + (index % 4) * 14 };
    return [
      {
        id: `${order.id}-flow`,
        from,
        to,
        value: order.priority === "priority" ? 0.85 : 0.45,
        risk: order.priority === "priority" && order.status !== "DELIVERED" ? risk : 0.14,
      },
    ];
  });

  const cells = zoneSignals.flatMap((zone, zoneIndex) =>
    CLUSTER_CELL_OFFSETS.map(([column, row], cellIndex) => {
      const localVariation = ((cellIndex * 17 + zoneIndex * 11) % 23) / 100;
      return {
        id: `${zone.id}-cell-${cellIndex}`,
        center: {
          x: clamp(zone.center.x + column * 3.5, 3, 97),
          y: clamp(zone.center.y + row * 4.1, 3, 97),
        },
        intensity: clamp(0.16 + zone.orderPressure * 0.68 + localVariation),
        risk: clamp(zone.risk * 0.82 + localVariation * 0.55),
      };
    }),
  );

  return {
    cells,
    nodes,
    flows,
    zones: zoneSignals.map((zone) => ({
      ...zone,
      risk: clamp(Math.max(zone.risk, risk * 0.22)),
      selected: zone.id === selectedZoneId,
    })),
  };
}

export function toUrbanFieldState(snapshot: OperationsSnapshot): UrbanFieldState {
  const orderCount = snapshot.orders.length;
  const courierCount = snapshot.couriers.length;
  const availableCouriers = snapshot.couriers.filter(
    (courier) => courier.status === "available",
  ).length;
  const priorityOrders = snapshot.orders.filter(
    (order) => order.priority === "priority" && order.status !== "DELIVERED",
  ).length;
  const offlineCouriers = snapshot.couriers.filter(
    (courier) => courier.status === "offline" || courier.stale,
  ).length;
  const pressure = clamp(orderCount / Math.max(6, courierCount * 1.75));
  const supply = courierCount ? clamp(availableCouriers / courierCount) : 0;
  const risk = clamp(
    (priorityOrders / Math.max(1, orderCount)) * 0.7 +
      (offlineCouriers / Math.max(1, courierCount)) * 0.3,
  );
  const dispatchLatency = snapshot.dispatch.latencyMs ?? 0;
  const traffic = clamp(0.22 + pressure * 0.36 + (dispatchLatency > 80 ? 0.18 : 0));
  const activityRate = clamp(0.28 + orderCount * 0.06 + dispatchLatency / 280);
  const provenance = snapshot.source === "live" ? "snapshot-derived" : "visual-demo";

  return {
    mode: snapshot.source,
    pressure,
    supply,
    risk,
    traffic,
    strategy: snapshot.dispatch.strategy,
    twinFidelity: snapshot.source === "replay" || snapshot.source === "simulation" ? 0.93 : 0.86,
    activityRate,
    provenance,
    spatial: createSpatialState(snapshot, risk),
  };
}
