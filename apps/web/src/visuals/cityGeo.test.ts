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
    expect(chengdu.trajectories[0]?.points.length).toBeGreaterThanOrEqual(7);
    expect(shenzhen.trajectories).toHaveLength(8);
    cityIds.forEach((id) => {
      const dataset = createCityOperationalDataset(id);
      expect(dataset.trajectories.every((route) => route.points.length >= 5)).toBe(true);
      expect(dataset.riskZones).toHaveLength(10);
      expect(dataset.riskZones.every((zone) => zone.polygon.length === 7)).toBe(true);
    });
  });

  it("uses road-corridor turns and hexagonal risk cells instead of free-space arcs and boxes", () => {
    cityIds.forEach((id) => {
      const dataset = createCityOperationalDataset(id);
      dataset.trajectories.forEach((route) => {
        const segmentBearings = route.points.slice(1).map((point, index) => {
          const previous = route.points[index]!;
          return Math.atan2(point[1] - previous[1], point[0] - previous[0]);
        });
        expect(new Set(segmentBearings.map((bearing) => bearing.toFixed(2))).size).toBeGreaterThan(
          2,
        );
      });
      dataset.riskZones.forEach((zone) => {
        expect(new Set(zone.polygon.slice(0, -1).map((point) => point.join(","))).size).toBe(6);
        expect(zone.polygon[0]).toEqual(zone.polygon.at(-1));
      });
    });
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
