import { describe, expect, it } from "vitest";
import { demoDataSource } from "../data/demoSnapshot";
import { projectGeoAnalyticalLayers } from "./geoAnalyticalLayers";

describe("geo analytical layer projection", () => {
  const now = new Date("2026-08-22T09:49:00Z");

  it("projects units, scales, evidence counts, and flow records from the snapshot", () => {
    const projection = projectGeoAnalyticalLayers(demoDataSource.getSnapshot(), now);
    const orders = projection.definitions.find((definition) => definition.id === "orders");
    const flow = projection.definitions.find((definition) => definition.id === "flow");

    expect(projection.freshness).toBe("fresh");
    expect(orders).toMatchObject({ availability: "available", unit: "orders / zone" });
    expect(flow).toMatchObject({ availability: "available", scale: "0–N orders" });
    expect(projection.values.orders.length).toBeGreaterThan(0);
    expect(projection.values.orders[0]?.evidenceCount).toBeGreaterThanOrEqual(0);
    expect(projection.values.flow.length).toBeGreaterThan(0);
  });

  it("does not infer travel or integrity metrics without source fields", () => {
    const projection = projectGeoAnalyticalLayers(demoDataSource.getSnapshot(), now);
    expect(
      projection.definitions.find((definition) => definition.id === "congestion"),
    )?.toMatchObject({
      availability: "unavailable",
    });
    expect(
      projection.definitions.find((definition) => definition.id === "travel-degradation"),
    )?.toMatchObject({
      availability: "unavailable",
    });
    expect(
      projection.definitions.find((definition) => definition.id === "integrity"),
    )?.toMatchObject({
      availability: "unavailable",
    });
    expect(projection.values.congestion).toEqual([]);
    expect(projection.values["travel-degradation"]).toEqual([]);
  });
});
