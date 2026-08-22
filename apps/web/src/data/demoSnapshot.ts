import type { OperationsDataSource, OperationsSnapshot } from "../domain/model";

const lifecycle = [
  ["CREATED", "Order received", "12:14", true],
  ["CONFIRMED", "Merchant confirmed", "12:15", true],
  ["PREPARING", "Kitchen started", "12:17", true],
  ["READY_FOR_PICKUP", "Ready for pickup", "12:27", true],
  ["ASSIGNED", "Courier assigned", "12:29", true],
  ["PICKED_UP", "Picked up", "12:34", true],
  ["OUT_FOR_DELIVERY", "Out for delivery", "12:36", true],
  ["DELIVERED", "Delivered", "12:48", true],
] as const;

const primaryOrder = {
  id: "order-2041",
  shortId: "RM-2041",
  customerName: "Maya Chen",
  merchantName: "Northstar Kitchen",
  status: "DELIVERED",
  eta: "Delivered 12:48",
  age: "34 min",
  priority: "standard",
  destination: "18 Willow Lane",
  route: [
    { x: 18, y: 78 },
    { x: 36, y: 64 },
    { x: 54, y: 61 },
    { x: 75, y: 37 },
  ],
  events: lifecycle.map(([status, label, at, completed]) => ({
    status,
    label,
    at,
    completed,
  })),
} as const;

const demoSnapshot: OperationsSnapshot = {
  source: "demo",
  availability: "ready",
  sourceDetail: "Deterministic fixture for offline demonstration",
  generatedAt: "2026-08-22T09:48:00Z",
  orders: [
    primaryOrder,
    {
      ...primaryOrder,
      id: "order-2042",
      shortId: "RM-2042",
      customerName: "Jon Bell",
      merchantName: "Greenline Market",
      status: "OUT_FOR_DELIVERY",
      eta: "12:56",
      age: "12 min",
      priority: "priority",
      destination: "4 Orchard Street",
      route: [
        { x: 24, y: 31 },
        { x: 42, y: 44 },
        { x: 65, y: 56 },
        { x: 82, y: 69 },
      ],
      events: lifecycle.map(([status, label, at], index) => ({
        status,
        label,
        at,
        completed: index < 7,
      })),
    },
    {
      ...primaryOrder,
      id: "order-2043",
      shortId: "RM-2043",
      customerName: "Inez Park",
      merchantName: "Cedar & Salt",
      status: "PREPARING",
      eta: "13:08",
      age: "7 min",
      priority: "standard",
      destination: "72 Market Row",
      route: [
        { x: 70, y: 23 },
        { x: 59, y: 39 },
        { x: 49, y: 58 },
        { x: 28, y: 70 },
      ],
      events: lifecycle.map(([status, label, at], index) => ({
        status,
        label,
        at,
        completed: index < 3,
      })),
    },
  ],
  couriers: [
    {
      id: "courier-17",
      name: "Ari Singh",
      status: "on_route",
      zone: "North Loop",
      eta: "8 min",
      position: { x: 64, y: 43 },
    },
    {
      id: "courier-22",
      name: "Theo Martin",
      status: "available",
      zone: "Market East",
      eta: "2 min",
      position: { x: 28, y: 69 },
    },
    {
      id: "courier-31",
      name: "Samira Okafor",
      status: "available",
      zone: "Riverside",
      eta: "4 min",
      position: { x: 72, y: 24 },
    },
  ],
  merchants: [
    {
      id: "merchant-northstar",
      name: "Northstar Kitchen",
      prepMinutes: 11,
      queue: 2,
      status: "busy",
    },
    {
      id: "merchant-greenline",
      name: "Greenline Market",
      prepMinutes: 6,
      queue: 1,
      status: "open",
    },
    { id: "merchant-cedar", name: "Cedar & Salt", prepMinutes: 14, queue: 3, status: "busy" },
  ],
  dispatch: {
    strategy: "weighted-greedy",
    version: "1.0.0",
    selectedCourier: "courier-17",
    latencyMs: 42,
    rationale: "Priority order balanced with courier proximity and zone load.",
  },
  health: [
    {
      service: "business-api",
      label: "Business API",
      status: "checking",
      endpoint: "http://localhost:18080/actuator/health",
      checkedAt: "12:48:00",
      detail: "Awaiting probe",
    },
    {
      service: "compute-api",
      label: "Compute API",
      status: "checking",
      endpoint: "http://localhost:18081/healthz",
      checkedAt: "12:48:00",
      detail: "Awaiting probe",
    },
  ],
};

export const demoDataSource: OperationsDataSource = {
  getSnapshot: () => demoSnapshot,
};
