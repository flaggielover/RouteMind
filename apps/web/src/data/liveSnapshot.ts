import type {
  Courier,
  DataSourceMode,
  OperationsDataSource,
  OperationsSnapshot,
  Order,
  OrderEvent,
  OrderStatus,
} from "../domain/model";
export { replayDataSource } from "./replay";

interface LiveOrder {
  id: string;
  status: string;
  version: number;
  createdAt: string;
  updatedAt: string;
}

interface LiveParty {
  id: string;
  type: string;
  displayName: string;
  status: string;
}

interface LiveCourierLocation {
  courierId: string;
  latitude: number;
  longitude: number;
  observedAt: string;
}

interface LiveOperationsResponse {
  source: "live";
  generatedAt: string;
  orders: LiveOrder[];
  parties: LiveParty[];
  courierLocations: LiveCourierLocation[];
}

interface LiveDispatchResponse {
  source: "live";
  strategy: string;
  strategy_version: string;
  selected_courier: string | null;
  score: number | null;
  rationale: string[];
  latency_millis: number;
  trace_id: string;
}

const businessApi = import.meta.env.VITE_BUSINESS_API_URL ?? "http://localhost:18080";
const computeApi = import.meta.env.VITE_COMPUTE_API_URL ?? "http://localhost:18081";
const timeoutMs = 2_000;

function emptySnapshot(mode: DataSourceMode, detail: string): OperationsSnapshot {
  return {
    source: mode,
    clockDomain: "WALL",
    availability: "unavailable",
    sourceDetail: detail,
    generatedAt: "",
    orders: [],
    couriers: [],
    merchants: [],
    dispatch: {
      strategy: "unavailable",
      version: "-",
      selectedCourier: "-",
      latencyMs: 0,
      rationale: detail,
    },
    health: [],
  };
}

function orderStatus(status: string): OrderStatus {
  const map: Record<string, OrderStatus> = {
    CREATED: "CREATED",
    CONFIRMED: "CONFIRMED",
    PREPARING: "PREPARING",
    READY_FOR_PICKUP: "READY_FOR_PICKUP",
    ASSIGNED: "ASSIGNED",
    ACCEPTED: "ACCEPTED",
    ARRIVED: "ARRIVED",
    PICKED_UP: "PICKED_UP",
    DELIVERED: "DELIVERED",
    ASSIGNMENT_TIMED_OUT: "ASSIGNMENT_TIMED_OUT",
    ASSIGNMENT_REJECTED: "ASSIGNMENT_REJECTED",
    REASSIGNMENT_PENDING: "REASSIGNMENT_PENDING",
    COMPENSATING: "COMPENSATING",
    COMPENSATED: "COMPENSATED",
    CANCELLED: "CANCELLED",
  };
  return map[status] ?? "CREATED";
}

function orderEvents(order: LiveOrder): readonly OrderEvent[] {
  return [
    {
      status: orderStatus(order.status),
      label: order.status.replaceAll("_", " "),
      at: order.updatedAt,
      completed: true,
    },
  ];
}

function toOrder(order: LiveOrder, parties: readonly LiveParty[]): Order {
  const customer = parties.find((party) => party.type === "CUSTOMER")?.displayName ?? "Customer";
  const merchant = parties.find((party) => party.type === "MERCHANT")?.displayName ?? "Merchant";
  return {
    id: order.id,
    shortId: order.id.slice(0, 8).toUpperCase(),
    customerName: customer,
    merchantName: merchant,
    status: orderStatus(order.status),
    eta: order.updatedAt,
    age: "live",
    priority: "standard",
    version: order.version,
    destination: "Durable order state",
    route: [],
    events: orderEvents(order),
  };
}

function toCourier(location: LiveCourierLocation, reference: Date): Courier {
  const observedAt = new Date(location.observedAt);
  const stale =
    !Number.isNaN(observedAt.getTime()) && reference.getTime() - observedAt.getTime() > 120_000;
  return {
    id: location.courierId,
    name: location.courierId,
    status: stale ? "offline" : "available",
    zone: "live",
    eta: stale ? "stale" : "unknown",
    position: { x: location.longitude, y: location.latitude },
  };
}

async function fetchJson<T>(
  url: string,
  init: RequestInit = {},
  fetchImpl: typeof fetch = fetch,
): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetchImpl(url, { ...init, signal: controller.signal });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    return (await response.json()) as T;
  } finally {
    clearTimeout(timeout);
  }
}

export async function loadLiveSnapshot(
  fetchImpl: typeof fetch = fetch,
): Promise<OperationsSnapshot> {
  try {
    const operations = await fetchJson<LiveOperationsResponse>(
      `${businessApi}/api/v1/operations/snapshot`,
      { headers: { Accept: "application/json" } },
      fetchImpl,
    );
    const candidates = operations.courierLocations.map((location) => ({
      courier_id: location.courierId,
      location: { latitude: location.latitude, longitude: location.longitude },
    }));
    const dispatch = await fetchJson<LiveDispatchResponse>(
      `${computeApi}/api/v1/dispatch/snapshot`,
      {
        method: "POST",
        headers: { Accept: "application/json", "Content-Type": "application/json" },
        body: JSON.stringify({
          request_id: "operations-live-snapshot",
          strategy: "weighted-greedy",
          pickup: { latitude: 0, longitude: 0 },
          candidates,
        }),
      },
      fetchImpl,
    );
    const reference = new Date(operations.generatedAt);
    const staleCourier = operations.courierLocations.some((location) => {
      const observedAt = new Date(location.observedAt);
      return (
        !Number.isNaN(reference.getTime()) &&
        !Number.isNaN(observedAt.getTime()) &&
        reference.getTime() - observedAt.getTime() > 120_000
      );
    });
    const orders = operations.orders.map((order) => toOrder(order, operations.parties));
    return {
      source: "live",
      clockDomain: "WALL",
      availability: staleCourier ? "degraded" : "ready",
      sourceDetail: staleCourier
        ? "Java durable snapshot + Python dispatch decision; courier location stale"
        : "Java durable snapshot + Python dispatch decision",
      generatedAt: operations.generatedAt,
      orders,
      couriers: operations.courierLocations.map((location) => toCourier(location, reference)),
      merchants: operations.parties
        .filter((party) => party.type === "MERCHANT")
        .map((party) => ({
          id: party.id,
          name: party.displayName,
          prepMinutes: 0,
          queue: 0,
          status: "open" as const,
        })),
      dispatch: {
        strategy: dispatch.strategy,
        version: dispatch.strategy_version,
        selectedCourier: dispatch.selected_courier ?? "-",
        latencyMs: dispatch.latency_millis,
        rationale: dispatch.rationale.join("; "),
      },
      health: [],
    };
  } catch (error) {
    const detail = error instanceof Error ? error.message : "Live data unavailable";
    return { ...emptySnapshot("live", detail), sourceDetail: `Live unavailable: ${detail}` };
  }
}

export const liveDataSource: OperationsDataSource = {
  getSnapshot: () => ({
    ...emptySnapshot("live", "Loading Java durable snapshot and Python dispatch"),
    availability: "loading",
  }),
  loadSnapshot: () => loadLiveSnapshot(),
};
