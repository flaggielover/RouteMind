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
  zones?: readonly { id: string; center: GeoPoint; radius: number; risk: number }[];
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

function pointForMerchant(index: number): GeoPoint {
  return {
    x: 18 + ((index * 37) % 68),
    y: 20 + ((index * 23) % 58),
  };
}

function createSpatialState(snapshot: OperationsSnapshot, risk: number): UrbanFieldSpatialState {
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
    ...snapshot.merchants.map((merchant, index) => ({
      id: merchant.id,
      kind: "merchant" as const,
      position: pointForMerchant(index),
      value: clamp(merchant.queue / 5),
      risk: clamp(merchant.prepMinutes / 24),
    })),
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

  const cells = Array.from({ length: 72 }, (_, index) => {
    const column = index % 12;
    const row = Math.floor(index / 12);
    const wave = (Math.sin(column * 0.82 + row * 0.37) + 1) / 2;
    const intensity = clamp(0.18 + wave * 0.48 + snapshot.orders.length * 0.025);
    return {
      id: `cell-${column}-${row}`,
      center: { x: 8 + column * 7.6, y: 14 + row * 14.2 },
      intensity,
      risk: clamp(risk * 0.5 + wave * 0.24),
    };
  });

  return {
    cells,
    nodes,
    flows,
    zones: [
      { id: "north-loop", center: { x: 68, y: 28 }, radius: 17, risk: clamp(risk * 1.05) },
      { id: "market-east", center: { x: 33, y: 65 }, radius: 14, risk: clamp(risk * 0.72) },
    ],
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
  const traffic = clamp(0.22 + pressure * 0.36 + (snapshot.dispatch.latencyMs > 80 ? 0.18 : 0));
  const activityRate = clamp(0.28 + orderCount * 0.06 + snapshot.dispatch.latencyMs / 280);
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
