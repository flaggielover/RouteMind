import { describe, expect, it } from "vitest";
import {
  createMultiCityGeoProjection,
  demoMultiCitySignals,
  type GeoCitySignal,
} from "./multiCityGeo";

describe("multi-city geo operations projection", () => {
  it("aggregates coordinate-backed city signals at national scope", () => {
    const projection = createMultiCityGeoProjection(demoMultiCitySignals, "national", "DEMO");

    expect(projection.sourceLabel).toBe("DEMO data");
    expect(projection.aggregationLevel).toBe("city-centroid");
    expect(projection.rawPointsVisible).toBe(false);
    expect(projection.zoom).toBe(4);
    expect(projection.totalOrders).toBe(4620);
    expect(projection.totalSupply).toBe(1620);
    expect(projection.cities[0]?.latitude).toBe(31.2304);
    expect(projection.projectionDigest).toHaveLength(64);
  });

  it("enables operational points only at city scope", () => {
    const projection = createMultiCityGeoProjection(demoMultiCitySignals, "city", "SIMULATION");

    expect(projection.sourceLabel).toBe("SIMULATION data");
    expect(projection.aggregationLevel).toBe("operational-point");
    expect(projection.rawPointsVisible).toBe(true);
    expect(projection.zoom).toBe(11);
  });

  it("rejects duplicate ids, invalid coordinates, and unbounded risk", () => {
    const invalid: GeoCitySignal = { ...demoMultiCitySignals[0]!, cityId: "" };
    expect(() => createMultiCityGeoProjection([], "national", "DEMO")).toThrow(/At least/);
    expect(() => createMultiCityGeoProjection([invalid], "national", "DEMO")).toThrow(/identity/);
    expect(() =>
      createMultiCityGeoProjection(
        [demoMultiCitySignals[0]!, { ...demoMultiCitySignals[0]! }],
        "multi-city",
        "DEMO",
      ),
    ).toThrow(/unique/);
    expect(() =>
      createMultiCityGeoProjection(
        [{ ...demoMultiCitySignals[0]!, latitude: 91 }],
        "national",
        "DEMO",
      ),
    ).toThrow(/coordinates/);
    expect(() =>
      createMultiCityGeoProjection(
        [{ ...demoMultiCitySignals[0]!, riskIndex: 2 }],
        "national",
        "DEMO",
      ),
    ).toThrow(/metrics/);
  });
});
