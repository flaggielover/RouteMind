import { beforeEach, describe, expect, it, vi } from "vitest";
import { demoDataSource } from "./demoSnapshot";
import {
  acceptRealtimeItem,
  applyRealtimeItem,
  createRealtimeCursorState,
  createRealtimeStream,
  parseRealtimeItem,
  type EventSourceLike,
  type RealtimeConnectionState,
  type RealtimeItem,
} from "./realtime";

function item(cursor: string, eventId = `event-${cursor}`, status = "CONFIRMED"): RealtimeItem {
  return {
    schemaVersion: "v1",
    cursor,
    replay: cursor !== "1",
    stale: false,
    staleReason: null,
    event: {
      specVersion: "1.0",
      eventId,
      eventType: "order.status.changed",
      occurredAt: "2026-08-22T10:00:00Z",
      producer: "business-api",
      aggregateId: "order-2042",
      aggregateVersion: Number(cursor),
      correlationId: "correlation-1",
      causationId: null,
      traceId: "0123456789abcdef0123456789abcdef",
      payload: { orderId: "order-2042", status },
    },
  };
}

class FakeEventSource implements EventSourceLike {
  onopen: ((event: Event) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
  onmessage: ((event: MessageEvent<string>) => void) | null = null;
  closed = false;
  private listeners = new Map<string, (event: MessageEvent<string>) => void>();

  addEventListener(type: string, listener: (event: MessageEvent<string>) => void): void {
    this.listeners.set(type, listener);
  }

  close(): void {
    this.closed = true;
  }

  emit(itemValue: RealtimeItem): void {
    this.listeners.get(itemValue.event.eventType)?.({
      data: JSON.stringify(itemValue),
    } as MessageEvent<string>);
  }

  fail(): void {
    this.onerror?.(new Event("error"));
  }
}

describe("browser realtime cursor and reconnect boundary", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("accepts strictly newer events, suppresses duplicates, and marks cursor gaps stale", () => {
    let state = createRealtimeCursorState();
    const first = acceptRealtimeItem(state, item("1"));
    expect(first.accepted).toBe(true);
    state = first.state;
    const duplicate = acceptRealtimeItem(state, item("1", "event-1"));
    expect(duplicate.accepted).toBe(false);
    expect(duplicate.reason).toBe("duplicate");
    const gap = acceptRealtimeItem(state, item("3"));
    expect(gap.accepted).toBe(false);
    expect(gap.reason).toBe("cursor_gap");
    expect(gap.state.staleReason).toContain("cursor gap");
  });

  it("rejects stale items and malformed contract payloads", () => {
    const stale = { ...item("2"), stale: true, staleReason: "retention boundary" };
    const result = acceptRealtimeItem(createRealtimeCursorState("1"), stale);
    expect(result.accepted).toBe(false);
    expect(result.reason).toBe("stale");
    expect(() =>
      parseRealtimeItem(JSON.stringify({ schemaVersion: "v1", cursor: "004" })),
    ).toThrow();
  });

  it("updates only forward order lifecycle states", () => {
    const snapshot = demoDataSource.getSnapshot();
    const forward = applyRealtimeItem(snapshot, {
      ...item("1", "event-forward", "DELIVERED"),
      event: {
        ...item("1").event,
        aggregateId: "order-2042",
        payload: { orderId: "order-2042", status: "DELIVERED" },
      },
    });
    expect(forward.orders.find((order) => order.id === "order-2042")?.status).toBe("DELIVERED");
    const regression = applyRealtimeItem(forward, {
      ...item("2", "event-regression", "PREPARING"),
      event: {
        ...item("2").event,
        aggregateVersion: 99,
        payload: { orderId: "order-2042", status: "PREPARING" },
      },
    });
    expect(regression.orders.find((order) => order.id === "order-2042")?.status).toBe("DELIVERED");
  });

  it("reconnects with the last cursor using bounded backoff", () => {
    const sources: FakeEventSource[] = [];
    const urls: string[] = [];
    const pending: Array<() => void> = [];
    const states: RealtimeConnectionState[] = [];
    const stream = createRealtimeStream({
      endpoint: "http://business.test/api/v1/events/stream",
      eventSourceFactory: (url) => {
        urls.push(url);
        const source = new FakeEventSource();
        sources.push(source);
        return source;
      },
      setTimeout: (handler) => {
        pending.push(handler);
        return handler;
      },
      clearTimeout: () => undefined,
      onEvent: () => undefined,
      onStateChange: (state) => states.push(state),
    });

    stream.start();
    sources[0].onopen?.(new Event("open"));
    sources[0].emit(item("1"));
    sources[0].fail();
    expect(urls[0]).toContain("after=0");
    expect(states.at(-1)?.status).toBe("reconnecting");
    pending.shift()?.();
    expect(urls[1]).toContain("after=1");
    stream.stop();
    expect(sources[1].closed).toBe(true);
  });
});
