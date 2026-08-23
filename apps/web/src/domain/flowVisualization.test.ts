import { describe, expect, it } from "vitest";
import { demoDataSource } from "../data/demoSnapshot";
import { projectDataBackedFlows } from "./flowVisualization";

describe("data-backed flow projection", () => {
  const now = new Date("2026-08-22T09:49:00Z");

  it("aggregates route-bearing orders with direction, units, and evidence ids", () => {
    const projection = projectDataBackedFlows(demoDataSource.getSnapshot(), now);

    expect(projection.freshness).toBe("fresh");
    expect(projection.derivedFrom).toBe("order-route-records");
    expect(projection.routeBearingOrders).toBe(3);
    expect(projection.representedOrders).toBe(3);
    expect(projection.flows.length).toBeGreaterThan(0);
    expect(projection.flows.every((flow) => flow.orderCount > 0)).toBe(true);
    expect(projection.flows.every((flow) => flow.confidence >= 0 && flow.confidence <= 1)).toBe(
      true,
    );
    expect(projection.flows.flatMap((flow) => flow.evidenceOrderIds)).toEqual(
      expect.arrayContaining(["order-2041", "order-2042", "order-2043"]),
    );
    expect(projection.flows[0]).toMatchObject({
      direction: expect.any(String),
      recencyMinutes: 1,
    });
  });

  it("keeps stale, unavailable, and route-less source states honest", () => {
    const snapshot = demoDataSource.getSnapshot();
    const stale = projectDataBackedFlows(snapshot, new Date("2026-08-24T09:49:00Z"));
    expect(stale.freshness).toBe("stale");
    expect(stale.flows.length).toBeGreaterThan(0);

    const unavailable = projectDataBackedFlows({ ...snapshot, availability: "unavailable" }, now);
    expect(unavailable.freshness).toBe("unavailable");
    expect(unavailable.flows).toEqual([]);
    expect(unavailable.emptyReason).toMatch(/unavailable/);

    const routeLess = projectDataBackedFlows(
      { ...snapshot, orders: snapshot.orders.map((order) => ({ ...order, route: [] })) },
      now,
    );
    expect(routeLess.flows).toEqual([]);
    expect(routeLess.emptyReason).toMatch(/route records/);
  });
});
