import { describe, expect, it } from "vitest";
import {
  createGeographicCoordinate,
  configuredTileMapAdapter,
  localFallbackBounds,
  localSchematicMapAdapter,
  localSchematicMapCapabilities,
  normalizedToGeographicCoordinate,
} from "./geospatial";

describe("provider-neutral geospatial contract", () => {
  it("accepts WGS84 coordinates and rejects invalid values", () => {
    expect(createGeographicCoordinate({ latitude: 31.23, longitude: 121.47 })).toEqual({
      latitude: 31.23,
      longitude: 121.47,
    });
    expect(() => createGeographicCoordinate({ latitude: 91, longitude: 0 })).toThrow(RangeError);
    expect(() => createGeographicCoordinate({ latitude: 0, longitude: 181 })).toThrow(RangeError);
  });

  it("maps normalized schematic points into the declared fallback bounds", () => {
    expect(normalizedToGeographicCoordinate({ x: 0, y: 100 })).toEqual({
      latitude: localFallbackBounds.south,
      longitude: localFallbackBounds.west,
    });
    expect(normalizedToGeographicCoordinate({ x: 100, y: 0 })).toEqual({
      latitude: localFallbackBounds.north,
      longitude: localFallbackBounds.east,
    });
    expect(() => normalizedToGeographicCoordinate({ x: 101, y: 50 })).toThrow(RangeError);
  });

  it("declares local fallback capabilities without paid provider requirements", () => {
    expect(localSchematicMapCapabilities.mode).toBe("local-fallback");
    expect(localSchematicMapCapabilities.tiles).toBe("not_configured");
    expect(localSchematicMapCapabilities.routing).toBe("not_configured");
    expect(localSchematicMapCapabilities.attributionRequired).toBe(false);
  });

  it("projects markers, routes, zones, and selection without mutating input", () => {
    const input = {
      generatedAt: "2026-08-22T10:00:00Z",
      markers: [
        {
          id: "order-1",
          kind: "order" as const,
          label: "Order 1",
          coordinate: { latitude: 31.23, longitude: 121.47 },
        },
      ],
      routes: [
        {
          id: "route-1",
          label: "Order 1 route",
          coordinates: [{ latitude: 31.23, longitude: 121.47 }],
        },
      ],
      zones: [
        {
          id: "zone-1",
          label: "North Loop",
          polygon: [
            { latitude: 31.24, longitude: 121.46 },
            { latitude: 31.25, longitude: 121.48 },
          ],
        },
      ],
      selection: { kind: "order" as const, id: "order-1" },
    };

    const projection = localSchematicMapAdapter.project(input);
    expect(projection.mode).toBe("local-fallback");
    expect(projection.markers).toHaveLength(1);
    expect(projection.routes[0]?.coordinates).toHaveLength(1);
    expect(projection.zones[0]?.polygon).toHaveLength(2);
    expect(projection.selection).toEqual(input.selection);
    expect(
      localSchematicMapAdapter.select(projection, { kind: "zone", id: "zone-1" }).selection,
    ).toEqual({ kind: "zone", id: "zone-1" });
    expect(input.markers[0]?.coordinate).toEqual({ latitude: 31.23, longitude: 121.47 });
  });

  it("uses a configured tile provider only when its template is explicit", () => {
    expect(configuredTileMapAdapter(undefined).capabilities.mode).toBe("local-fallback");
    const adapter = configuredTileMapAdapter("https://tiles.example/{z}/{x}/{y}.png");
    expect(adapter.capabilities.mode).toBe("provider");
    expect(adapter.capabilities.tiles).toBe("available");
    expect(adapter.capabilities.attributionRequired).toBe(true);
    expect(() => configuredTileMapAdapter("https://tiles.example/{z}/{y}.png")).toThrow();
  });
});
