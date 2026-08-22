export const roles = ["operations", "strategy", "customer", "merchant", "courier"] as const;

export type Role = (typeof roles)[number];

export type OrderStatus =
  | "CREATED"
  | "CONFIRMED"
  | "PREPARING"
  | "READY_FOR_PICKUP"
  | "ASSIGNED"
  | "PICKED_UP"
  | "OUT_FOR_DELIVERY"
  | "DELIVERED";

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

export interface ServiceHealth {
  service: "business-api" | "compute-api";
  label: string;
  status: ServiceStatus;
  endpoint: string;
  checkedAt: string;
  detail: string;
}

export interface OperationsSnapshot {
  source: "demo" | "api";
  generatedAt: string;
  orders: readonly Order[];
  couriers: readonly Courier[];
  merchants: readonly Merchant[];
  dispatch: DispatchDecision;
  health: readonly ServiceHealth[];
}

export interface OperationsDataSource {
  getSnapshot(): OperationsSnapshot;
}
