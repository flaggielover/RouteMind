import { describe, expect, it } from "vitest";
import { demoDataSource } from "../data/demoSnapshot";
import { projectCityZoneDrilldown } from "./cityZoneDrilldown";

describe("city and zone drilldown", () => {
  it("derives zone-backed metrics from the snapshot and aggregates at low zoom", () => {
    const snapshot = demoDataSource.getSnapshot();
    const projection = projectCityZoneDrilldown(snapshot, 6, new Date("2026-08-22T09:49:00Z"));

    expect(projection.sourceLabel).toBe("DEMO source");
    expect(projection.freshness).toBe("fresh");
    expect(projection.aggregation).toBe("city");
    expect(projection.zones).toHaveLength(1);
    expect(projection.zones[0]?.orderCount).toBe(3);
    expect(projection.zones[0]?.routeCount).toBe(3);
    expect(projection.derivedFromSnapshot).toBe(true);
  });

  it("switches to zone detail and exposes units, supply, risk, and routes", () => {
    const projection = projectCityZoneDrilldown(
      demoDataSource.getSnapshot(),
      11,
      new Date("2026-08-22T09:49:00Z"),
    );

    expect(projection.aggregation).toBe("zone");
    expect(projection.zones).toHaveLength(3);
    expect(projection.zones.every((zone) => zone.densityPer100 >= 0)).toBe(true);
    expect(projection.zones.every((zone) => zone.riskIndex >= 0 && zone.riskIndex <= 1)).toBe(true);
  });

  it("marks stale, empty, and unavailable sources explicitly", () => {
    const snapshot = demoDataSource.getSnapshot();
    expect(projectCityZoneDrilldown(snapshot, 11, new Date("2026-08-23T09:49:00Z")).freshness).toBe(
      "stale",
    );
    const empty = { ...snapshot, orders: [], couriers: [], merchants: [] };
    expect(projectCityZoneDrilldown(empty, 11, new Date("2026-08-22T09:49:00Z")).freshness).toBe(
      "empty",
    );
    const unavailable = { ...snapshot, availability: "unavailable" as const };
    expect(
      projectCityZoneDrilldown(unavailable, 11, new Date("2026-08-22T09:49:00Z")).freshness,
    ).toBe("unavailable");
  });
});
