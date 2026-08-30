import type {
  Courier,
  DataSourceMode,
  OperationsDataSource,
  OperationsSnapshot,
  Order,
  OrderOperationalContext,
  OrderEvent,
  OrderStatus,
  ServiceHealth,
} from "../domain/model";
import { authorizedHeaders, sessionScope, type TenantSession } from "./session";
export { replayDataSource } from "./replay";

interface LiveOrder {
  id: string;
  status: string;
  version: number;
  createdAt: string;
  updatedAt: string;
  operational?: OrderOperationalContext;
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
  ingestedAt?: string;
  sequence?: number;
  online?: boolean;
}

interface LiveOperationsResponse {
  source: "live";
  generatedAt: string;
  orders: LiveOrder[];
  parties: LiveParty[];
  courierLocations: LiveCourierLocation[];
  health?: {
    status: string;
    durableState: string;
    courierProjection: string;
  };
}

const businessApi = import.meta.env.VITE_BUSINESS_API_URL ?? "http://localhost:18080";
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
      latencyMs: null,
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

function toOrder(order: LiveOrder): Order {
  const parties = order.operational?.parties;
  const partyUnavailable = !parties || parties.linkageStatus === "UNAVAILABLE";
  return {
    id: order.id,
    shortId: order.id.slice(0, 8).toUpperCase(),
    customerName: partyUnavailable ? "Unavailable" : "Customer",
    merchantName: partyUnavailable ? "Unavailable" : "Merchant",
    status: orderStatus(order.status),
    eta: order.updatedAt,
    age: "live",
    priority: "standard",
    version: order.version,
    destination: "Durable order state",
    route: [],
    events: orderEvents(order),
    operational: order.operational,
  };
}

function dispatchFromOrders(orders: readonly LiveOrder[]): OperationsSnapshot["dispatch"] {
  const decision = orders.find((order) => order.operational?.decision.status === "RECORDED")
    ?.operational?.decision;
  if (!decision) {
    return {
      strategy: "unavailable",
      version: "-",
      selectedCourier: "-",
      latencyMs: null,
      rationale: "No durable dispatch decision is recorded for the current orders",
    };
  }
  const rationale = [decision.decisionReason, decision.policySelectionMode, decision.fallbackState]
    .filter((value): value is string => Boolean(value))
    .join("; ");
  return {
    strategy: decision.strategy ?? "unavailable",
    version: decision.strategyVersion ?? "-",
    selectedCourier: decision.courierId ?? "-",
    latencyMs: null,
    rationale: rationale || "Durable dispatch decision recorded",
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
    sequence: location.sequence ?? 1,
    observedAt: location.observedAt,
    ingestedAt: location.ingestedAt ?? location.observedAt,
    online: location.online ?? !stale,
    stale,
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
  session: TenantSession,
  fetchImpl: typeof fetch = fetch,
): Promise<OperationsSnapshot> {
  try {
    const primaryRole = session.roles[0];
    if (!primaryRole) throw new Error("Verified session has no authorized surface");
    const operations = await fetchJson<LiveOperationsResponse>(
      `${businessApi}/api/v1/operations/snapshot`,
      { headers: { Accept: "application/json", ...authorizedHeaders(session, primaryRole) } },
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
    const staleOperational = operations.orders.some((order) => {
      const operational = order.operational;
      return (
        operational?.orderFreshness.status === "STALE" ||
        operational?.route.freshness.status === "STALE" ||
        operational?.courier.freshness.status === "STALE"
      );
    });
    const degradedOperational = operations.orders.some(
      (order) => order.operational?.route.status === "DEGRADED",
    );
    const orders = operations.orders.map((order) => toOrder(order));
    const health: ServiceHealth[] = operations.health
      ? [
          {
            service: "business-api",
            label: "Business API",
            status: operations.health.status === "UP" ? "healthy" : "unavailable",
            endpoint: `${businessApi}/api/v1/operations/snapshot`,
            checkedAt: operations.generatedAt,
            detail: `durable state ${operations.health.durableState}; courier projection ${operations.health.courierProjection}`,
          },
        ]
      : [];
    return {
      source: "live",
      identityScope: sessionScope(session),
      clockDomain: "WALL",
      availability: staleCourier || staleOperational || degradedOperational ? "degraded" : "ready",
      sourceDetail:
        staleCourier || staleOperational || degradedOperational
          ? "Java durable snapshot + order-scoped decision ledger; operational freshness degraded"
          : "Java durable snapshot + order-scoped decision ledger; route estimate unavailable",
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
      dispatch: dispatchFromOrders(operations.orders),
      health,
    };
  } catch (error) {
    const detail = error instanceof Error ? error.message : "Live data unavailable";
    return {
      ...emptySnapshot("live", detail),
      identityScope: sessionScope(session),
      sourceDetail: `Live unavailable: ${detail}`,
    };
  }
}

export const liveDataSource: OperationsDataSource = {
  getSnapshot: () => ({
    ...emptySnapshot("live", "Loading Java durable snapshot and Python dispatch"),
    availability: "loading",
  }),
};
