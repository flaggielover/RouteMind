import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { demoDataSource } from "../data/demoSnapshot";
import { replayDataSource } from "../data/liveSnapshot";
import type { RealtimeConnectionState, RealtimeItem } from "../data/realtime";
import { ActivityStream } from "./ActivityStream";

const idleRealtime: RealtimeConnectionState = {
  status: "disabled",
  cursor: "0",
  detail: "disabled",
  appliedEvents: 0,
  staleReason: null,
  recentEvents: [],
};

function liveItem(): RealtimeItem {
  return {
    schemaVersion: "v1",
    cursor: "42",
    replay: true,
    stale: false,
    staleReason: null,
    event: {
      specVersion: "1.0",
      eventId: "event-42",
      eventType: "order.status.changed",
      occurredAt: "2026-08-22T10:00:00Z",
      producer: "business-api",
      aggregateId: "order-2041",
      aggregateVersion: 8,
      correlationId: "correlation-1",
      causationId: null,
      traceId: "0123456789abcdef0123456789abcdef",
      payload: {},
    },
  };
}

describe("activity stream projection", () => {
  it("labels deterministic demo activity and source", () => {
    render(<ActivityStream snapshot={demoDataSource.getSnapshot()} realtime={idleRealtime} />);

    expect(screen.getByRole("heading", { name: "Activity stream" })).toBeInTheDocument();
    expect(screen.getByText("Demo source")).toBeInTheDocument();
    expect(screen.getAllByText("Demo")).not.toHaveLength(0);
    expect(screen.getAllByText("Deterministic lifecycle fixture").length).toBeGreaterThan(0);
  });

  it("shows live cursor and trace context while replay remains explicit", () => {
    const liveState: RealtimeConnectionState = {
      ...idleRealtime,
      status: "connected",
      cursor: "42",
      recentEvents: [liveItem()],
    };
    const liveSnapshot = { ...demoDataSource.getSnapshot(), source: "live" as const };
    const { rerender } = render(<ActivityStream snapshot={liveSnapshot} realtime={liveState} />);

    expect(screen.getByText("Cursor 42")).toBeInTheDocument();
    expect(screen.getByText(/trace 0123456789ab/)).toBeInTheDocument();
    expect(screen.getByText("Live")).toBeInTheDocument();

    rerender(<ActivityStream snapshot={replayDataSource.getSnapshot()} realtime={idleRealtime} />);
    expect(screen.getByText("Replay source")).toBeInTheDocument();
    expect(screen.getByText("No verified replay activity is available.")).toBeInTheDocument();
  });
});
