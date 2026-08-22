import type { DataAvailability, OperationsSnapshot, OrderStatus } from "../domain/model";

export const realtimeEventTypes = [
  "order.created",
  "order.status.changed",
  "dispatch.decision.recorded",
  "courier.location.updated",
  "exception.raised",
  "simulation.tick",
] as const;

export type RealtimeEventType = (typeof realtimeEventTypes)[number];
export type RealtimeStatus =
  "disabled" | "connecting" | "connected" | "reconnecting" | "stale" | "degraded";

export interface RealtimeEnvelope {
  specVersion: "1.0";
  eventId: string;
  eventType: RealtimeEventType;
  occurredAt: string;
  producer: string;
  aggregateId: string;
  aggregateVersion: number;
  correlationId: string;
  causationId: string | null;
  traceId: string;
  payload: Record<string, unknown>;
}

export interface RealtimeItem {
  schemaVersion: "v1";
  cursor: string;
  event: RealtimeEnvelope;
  replay: boolean;
  stale: boolean;
  staleReason: string | null;
}

export interface RealtimeConnectionState {
  status: RealtimeStatus;
  cursor: string;
  detail: string;
  appliedEvents: number;
  staleReason: string | null;
  recentEvents: readonly RealtimeItem[];
}

export interface RealtimeCursorState {
  cursor: string;
  seenEventIds: readonly string[];
  staleReason: string | null;
}

export type RealtimeRejectReason = "duplicate" | "out_of_order" | "stale" | "cursor_gap";

export interface RealtimeAcceptResult {
  accepted: boolean;
  reason?: RealtimeRejectReason;
  state: RealtimeCursorState;
}

const maxSeenEventIds = 256;
const maxBackoffMs = 4_000;
const initialBackoffMs = 250;

export function isCanonicalCursor(value: string): boolean {
  return /^(0|[1-9][0-9]*)$/.test(value) && value.length <= 20;
}

export function compareCursors(left: string, right: string): number {
  if (!isCanonicalCursor(left) || !isCanonicalCursor(right)) {
    throw new Error("event cursor must be canonical decimal");
  }
  const a = BigInt(left);
  const b = BigInt(right);
  return a === b ? 0 : a < b ? -1 : 1;
}

export function createRealtimeCursorState(cursor = "0"): RealtimeCursorState {
  if (!isCanonicalCursor(cursor)) throw new Error("event cursor must be canonical decimal");
  return { cursor, seenEventIds: [], staleReason: null };
}

export function parseRealtimeItem(data: string): RealtimeItem {
  const parsed: unknown = JSON.parse(data);
  if (!isRecord(parsed)) throw new Error("event stream item must be an object");
  if (parsed.schemaVersion !== "v1" || typeof parsed.cursor !== "string") {
    throw new Error("event stream item has an unsupported schema");
  }
  if (!isCanonicalCursor(parsed.cursor) || !isRecord(parsed.event)) {
    throw new Error("event stream item has an invalid cursor or event");
  }
  if (typeof parsed.event.eventId !== "string" || typeof parsed.event.eventType !== "string") {
    throw new Error("event stream item has an invalid event identity");
  }
  if (!realtimeEventTypes.includes(parsed.event.eventType as RealtimeEventType)) {
    throw new Error("event stream item has an unsupported event type");
  }
  if (typeof parsed.replay !== "boolean" || typeof parsed.stale !== "boolean") {
    throw new Error("event stream item has invalid state metadata");
  }
  if (parsed.stale && (typeof parsed.staleReason !== "string" || parsed.staleReason.length === 0)) {
    throw new Error("stale event stream item requires a reason");
  }
  if (!parsed.stale && parsed.staleReason !== null) {
    throw new Error("fresh event stream item cannot have a stale reason");
  }
  return parsed as unknown as RealtimeItem;
}

export function acceptRealtimeItem(
  state: RealtimeCursorState,
  item: RealtimeItem,
): RealtimeAcceptResult {
  if (item.stale) {
    return {
      accepted: false,
      reason: "stale",
      state: { ...state, staleReason: item.staleReason ?? "server marked stream stale" },
    };
  }
  if (
    state.seenEventIds.includes(item.event.eventId) ||
    compareCursors(item.cursor, state.cursor) <= 0
  ) {
    return { accepted: false, reason: "duplicate", state };
  }
  if (state.cursor !== "0" && compareCursors(item.cursor, incrementCursor(state.cursor)) > 0) {
    const staleReason = `cursor gap after ${state.cursor}`;
    return { accepted: false, reason: "cursor_gap", state: { ...state, staleReason } };
  }
  const seenEventIds = [...state.seenEventIds, item.event.eventId].slice(-maxSeenEventIds);
  return {
    accepted: true,
    state: { cursor: item.cursor, seenEventIds, staleReason: null },
  };
}

export function applyRealtimeItem(
  snapshot: OperationsSnapshot,
  item: RealtimeItem,
): OperationsSnapshot {
  if (
    item.stale ||
    (item.event.eventType !== "order.created" && item.event.eventType !== "order.status.changed")
  ) {
    return snapshot;
  }
  const orderId = stringValue(item.event.payload.orderId);
  const status = orderStatus(item.event.payload.status);
  if (!orderId || !status) return snapshot;
  const orders = snapshot.orders.map((order) => {
    if (
      order.id !== orderId ||
      item.event.aggregateVersion <= (order.version ?? 0) ||
      statusRank(status) < statusRank(order.status)
    )
      return order;
    return {
      ...order,
      status,
      version: item.event.aggregateVersion,
      events: [
        ...order.events,
        {
          status,
          label: status.replaceAll("_", " "),
          at: item.event.occurredAt,
          completed: true,
        },
      ],
    };
  });
  if (
    item.event.eventType === "order.created" &&
    orderId &&
    !orders.some((order) => order.id === orderId)
  ) {
    orders.push({
      id: orderId,
      shortId: orderId.slice(0, 8).toUpperCase(),
      customerName: "Customer",
      merchantName: "Pending merchant",
      status,
      eta: "Pending",
      age: "live",
      priority: "standard",
      destination: "Durable order state",
      route: [],
      version: item.event.aggregateVersion,
      events: [
        {
          status,
          label: status.replaceAll("_", " "),
          at: item.event.occurredAt,
          completed: true,
        },
      ],
    });
  }
  return {
    ...snapshot,
    orders,
    generatedAt: item.event.occurredAt,
    availability: "ready" as DataAvailability,
  };
}

export interface EventSourceLike {
  onopen: ((event: Event) => void) | null;
  onerror: ((event: Event) => void) | null;
  onmessage: ((event: MessageEvent<string>) => void) | null;
  addEventListener(type: string, listener: (event: MessageEvent<string>) => void): void;
  close(): void;
}

export interface RealtimeStreamOptions {
  endpoint: string;
  initialCursor?: string;
  onEvent: (item: RealtimeItem) => void;
  onStateChange: (state: RealtimeConnectionState) => void;
  eventSourceFactory?: (url: string) => EventSourceLike;
  setTimeout?: (handler: () => void, timeout: number) => unknown;
  clearTimeout?: (handle: unknown) => void;
}

export interface RealtimeStream {
  start(): void;
  stop(): void;
}

export function createRealtimeStream(options: RealtimeStreamOptions): RealtimeStream {
  const eventSourceFactory = options.eventSourceFactory ?? ((url) => new EventSource(url));
  const schedule =
    options.setTimeout ?? ((handler, timeout) => window.setTimeout(handler, timeout));
  const cancel = options.clearTimeout ?? ((handle) => window.clearTimeout(handle as number));
  let cursorState = createRealtimeCursorState(options.initialCursor ?? "0");
  let source: EventSourceLike | null = null;
  let retryTimer: unknown = null;
  let retryAttempt = 0;
  let stopped = false;
  let appliedEvents = 0;
  let recentEvents: RealtimeItem[] = [];

  const publish = (
    status: RealtimeStatus,
    detail: string,
    staleReason = cursorState.staleReason,
  ) => {
    options.onStateChange({
      status,
      cursor: cursorState.cursor,
      detail,
      appliedEvents,
      staleReason,
      recentEvents,
    });
  };

  const closeSource = () => {
    source?.close();
    source = null;
  };

  const scheduleReconnect = () => {
    if (stopped || cursorState.staleReason) return;
    closeSource();
    const delay = Math.min(initialBackoffMs * 2 ** retryAttempt, maxBackoffMs);
    retryAttempt += 1;
    publish("reconnecting", `Reconnecting in ${delay} ms`);
    retryTimer = schedule(connect, delay);
  };

  const handleData = (data: string) => {
    try {
      const item = parseRealtimeItem(data);
      const result = acceptRealtimeItem(cursorState, item);
      cursorState = result.state;
      if (!result.accepted) {
        if (result.reason === "stale" || result.reason === "cursor_gap") {
          closeSource();
          publish("stale", cursorState.staleReason ?? "Stream cursor is stale");
        }
        return;
      }
      appliedEvents += 1;
      recentEvents = [item, ...recentEvents].slice(0, 20);
      options.onEvent(item);
      publish("connected", item.replay ? "Replayed event received" : "Live event received");
    } catch (error) {
      const detail = error instanceof Error ? error.message : "Invalid event stream item";
      publish("degraded", `Realtime event rejected: ${detail}`);
    }
  };

  function connect() {
    if (stopped) return;
    retryTimer = null;
    publish(retryAttempt === 0 ? "connecting" : "reconnecting", "Connecting to live event stream");
    const separator = options.endpoint.includes("?") ? "&" : "?";
    const url = `${options.endpoint}${separator}after=${encodeURIComponent(cursorState.cursor)}`;
    const nextSource = eventSourceFactory(url);
    source = nextSource;
    nextSource.onopen = () => {
      retryAttempt = 0;
      publish("connected", "Live event stream connected");
    };
    nextSource.onerror = () => {
      if (source === nextSource) scheduleReconnect();
    };
    nextSource.onmessage = (event: MessageEvent<string>) => handleData(event.data);
    for (const eventType of realtimeEventTypes) {
      nextSource.addEventListener(eventType, (event: MessageEvent<string>) =>
        handleData(event.data),
      );
    }
  }

  return {
    start: () => {
      stopped = false;
      connect();
    },
    stop: () => {
      stopped = true;
      if (retryTimer !== null) cancel(retryTimer);
      retryTimer = null;
      closeSource();
    },
  };
}

function incrementCursor(cursor: string): string {
  return (BigInt(cursor) + 1n).toString();
}

function stringValue(value: unknown): string | null {
  return typeof value === "string" && value.length > 0 ? value : null;
}

function orderStatus(value: unknown): OrderStatus | null {
  const statuses: readonly OrderStatus[] = [
    "CREATED",
    "CONFIRMED",
    "PREPARING",
    "READY_FOR_PICKUP",
    "ASSIGNED",
    "PICKED_UP",
    "OUT_FOR_DELIVERY",
    "DELIVERED",
  ];
  return typeof value === "string" && statuses.includes(value as OrderStatus)
    ? (value as OrderStatus)
    : null;
}

function statusRank(status: OrderStatus): number {
  return [
    "CREATED",
    "CONFIRMED",
    "PREPARING",
    "READY_FOR_PICKUP",
    "ASSIGNED",
    "PICKED_UP",
    "OUT_FOR_DELIVERY",
    "DELIVERED",
  ].indexOf(status);
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}
