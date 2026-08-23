import { describe, expect, it } from "vitest";
import { demoDataSource } from "../data/demoSnapshot";
import type { RealtimeConnectionState } from "../data/realtime";
import type { ServiceHealth } from "./model";
import { projectReliabilityCenter } from "./reliabilityCenter";

const disabledRealtime: RealtimeConnectionState = {
  status: "disabled",
  cursor: "0",
  detail: "Realtime disabled for supplied data source",
  appliedEvents: 0,
  staleReason: null,
  recentEvents: [],
};

const healthy: ServiceHealth[] = [
  {
    service: "business-api",
    label: "Business API",
    status: "healthy",
    endpoint: "/actuator/health",
    checkedAt: "2026-08-24T00:00:00Z",
    detail: "UP",
  },
];

describe("Reliability Center projection", () => {
  it("labels demo evidence as fixture and keeps missing reconciliation unavailable", () => {
    const projection = projectReliabilityCenter(
      demoDataSource.getSnapshot(),
      healthy,
      disabledRealtime,
    );

    expect(projection.status).toBe("fixture");
    expect(projection.invariants).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ name: "Continuous reconciliation", status: "unavailable" }),
      ]),
    );
    expect(projection.recovery).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ label: "Autonomous remediation", status: "unavailable" }),
      ]),
    );
  });

  it("surfaces live degradation, stale couriers, and stream recovery evidence", () => {
    const snapshot = {
      ...demoDataSource.getSnapshot(),
      source: "live" as const,
      availability: "degraded" as const,
      sourceDetail: "Live data is degraded; courier location stale",
      couriers: demoDataSource
        .getSnapshot()
        .couriers.map((courier) => ({ ...courier, stale: courier.id === "courier-17" })),
    };
    const realtime: RealtimeConnectionState = {
      ...disabledRealtime,
      status: "stale",
      detail: "Stream cursor is stale",
      staleReason: "No event received within bounded interval",
    };

    const projection = projectReliabilityCenter(snapshot, healthy, realtime);

    expect(projection.status).toBe("degraded");
    expect(projection.invariants).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ name: "Courier freshness", status: "failed" }),
      ]),
    );
    expect(projection.timeline).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ label: "Realtime stream", status: "failed" }),
      ]),
    );
    expect(projection.recovery).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ label: "Stream recovery", status: "failed" }),
      ]),
    );
  });
});
