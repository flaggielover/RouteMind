import { describe, expect, it } from "vitest";
import {
  CITY_DEMO_DENSITY,
  cityGeoCatalog,
  cityIds,
  createCityOperationalDataset,
  projectCityOperationalLod,
  selectionExists,
} from "./cityGeo";

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
    cityIds.forEach((id) => {
      const dataset = createCityOperationalDataset(id);
      expect(dataset.courierAgents).toHaveLength(CITY_DEMO_DENSITY[id].courierCount);
      expect(dataset.trajectories).toHaveLength(CITY_DEMO_DENSITY[id].emphasizedTrajectoryCount);
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
      dataset.courierAgents.forEach((agent) => {
        expect(agent.position[0]).toBeGreaterThanOrEqual(west);
        expect(agent.position[0]).toBeLessThanOrEqual(east);
        expect(agent.position[1]).toBeGreaterThanOrEqual(south);
        expect(agent.position[1]).toBeLessThanOrEqual(north);
        agent.path.forEach(([longitude, latitude]) => {
          expect(longitude).toBeGreaterThanOrEqual(west);
          expect(longitude).toBeLessThanOrEqual(east);
          expect(latitude).toBeGreaterThanOrEqual(south);
          expect(latitude).toBeLessThanOrEqual(north);
        });
      });
    });
  });

  it("binds every emphasized semantic route to one member of the full courier population", () => {
    cityIds.forEach((id) => {
      const dataset = createCityOperationalDataset(id);
      expect(new Set(dataset.courierAgents.map((agent) => agent.id)).size).toBe(
        CITY_DEMO_DENSITY[id].courierCount,
      );
      dataset.trajectories.forEach((route) => {
        const agent = dataset.courierAgents.find((candidate) => candidate.id === route.courierId);
        expect(agent?.trajectoryId).toBe(route.id);
        expect(agent?.path).toEqual(route.points);
        expect(route.points[0]).toEqual(
          dataset.city.anchors.find((anchor) => anchor.id === route.merchantId)?.coordinate,
        );
        expect(route.points.at(-1)).toEqual(
          dataset.city.anchors.find((anchor) => anchor.id === route.customerId)?.coordinate,
        );
      });
    });
  });

  it("projects stable city, district, and selected-courier LOD membership", () => {
    cityIds.forEach((id) => {
      const dataset = createCityOperationalDataset(id);
      const city = projectCityOperationalLod(dataset, { mode: "city" });
      const district = projectCityOperationalLod(dataset, {
        mode: "district",
        focusCoordinate: dataset.hotspots[0]!.coordinate,
      });
      const selectedRoute = dataset.trajectories[3]!;
      const selected = projectCityOperationalLod(dataset, {
        mode: "selected",
        selectedTrajectoryId: selectedRoute.id,
      });

      expect(city.courierAgents).toHaveLength(CITY_DEMO_DENSITY[id].courierCount);
      expect(city.trajectories).toHaveLength(CITY_DEMO_DENSITY[id].emphasizedTrajectoryCount);
      expect(district.trajectories).toHaveLength(CITY_DEMO_DENSITY[id].districtTrajectoryCount);
      expect(district.courierAgents.length).toBeLessThan(city.courierAgents.length);
      expect(selected.trajectories).toHaveLength(5);
      expect(selected.trajectories[0]?.id).toBe(selectedRoute.id);
      expect(selected.courierAgents.some((agent) => agent.id === selectedRoute.courierId)).toBe(
        true,
      );
      expect(selected.courierAgents.length).toBeLessThan(district.courierAgents.length);
      expect(
        projectCityOperationalLod(dataset, {
          mode: "selected",
          selectedTrajectoryId: selectedRoute.id,
        }),
      ).toEqual(selected);
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
