import { describe, expect, it } from "vitest";
import { cityGeoCatalog, cityIds, createCityOperationalDataset, selectionExists } from "./cityGeo";

describe("three-city geographic operations data", () => {
  it("defines unique real WGS84 contexts for the approved cities", () => {
    expect(cityIds).toEqual(["shanghai", "shenzhen", "chengdu"]);
    expect(new Set(cityIds.map((id) => cityGeoCatalog[id].seed)).size).toBe(3);
    cityIds.forEach((id) => {
      const city = cityGeoCatalog[id];
      expect(city.center[0]).toBeGreaterThan(100);
      expect(city.center[1]).toBeGreaterThan(20);
      expect(city.bounds[0][0]).toBeLessThan(city.center[0]);
      expect(city.bounds[1][0]).toBeGreaterThan(city.center[0]);
    });
  });

  it("is deterministic while keeping city route structures distinct", () => {
    const shanghai = createCityOperationalDataset("shanghai");
    expect(createCityOperationalDataset("shanghai")).toEqual(shanghai);
    const shenzhen = createCityOperationalDataset("shenzhen");
    const chengdu = createCityOperationalDataset("chengdu");
    expect(shanghai.trajectories[0]?.points).not.toEqual(shenzhen.trajectories[0]?.points);
    expect(shenzhen.trajectories[0]?.points).not.toEqual(chengdu.trajectories[0]?.points);
    expect(chengdu.trajectories[0]?.points).toHaveLength(9);
    expect(shenzhen.trajectories).toHaveLength(11);
  });

  it("keeps all generated points inside each selected city bounds", () => {
    cityIds.forEach((id) => {
      const dataset = createCityOperationalDataset(id);
      const [[west, south], [east, north]] = dataset.city.bounds;
      dataset.trajectories
        .flatMap((route) => route.points)
        .forEach(([longitude, latitude]) => {
          expect(longitude).toBeGreaterThanOrEqual(west);
          expect(longitude).toBeLessThanOrEqual(east);
          expect(latitude).toBeGreaterThanOrEqual(south);
          expect(latitude).toBeLessThanOrEqual(north);
        });
    });
  });

  it("detects a stale selection after a city switch", () => {
    const shanghai = createCityOperationalDataset("shanghai");
    const shenzhen = createCityOperationalDataset("shenzhen");
    const selected = shanghai.trajectories[0]!.id;
    expect(selectionExists(shanghai, selected)).toBe(true);
    expect(selectionExists(shenzhen, selected)).toBe(false);
  });
});
