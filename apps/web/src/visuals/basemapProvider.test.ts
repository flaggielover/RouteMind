import { describe, expect, it, vi } from "vitest";
import {
  OPENFREEMAP_LIBERTY_STYLE_URL,
  applyRouteMindBasemapTheme,
  openFreeMapLibertyProvider,
  resolveBasemapProvider,
  resolveRouteMindBasemapPaint,
  type BasemapStyleLayer,
} from "./basemapProvider";

describe("basemap provider boundary", () => {
  it("uses the complete credential-free OpenFreeMap Liberty style by default", () => {
    expect(resolveBasemapProvider()).toBe(openFreeMapLibertyProvider);
    expect(openFreeMapLibertyProvider.styleUrl).toBe(OPENFREEMAP_LIBERTY_STYLE_URL);
    expect(openFreeMapLibertyProvider.qualityTier).toBe("full-vector");
    expect(openFreeMapLibertyProvider.credentialRequirement).toBe("none");
    expect(openFreeMapLibertyProvider.attribution).toContain("OpenStreetMap");
    expect(openFreeMapLibertyProvider.themePolicy).toBe("routemind-graphite");
  });

  it("preserves an explicitly configured provider style and attribution", () => {
    const provider = resolveBasemapProvider({
      styleUrl: " https://tiles.example/styles/city ",
      attribution: "Example Maps",
      label: "Example City",
    });
    expect(provider).toMatchObject({
      id: "configured-maplibre-style",
      label: "Example City",
      styleUrl: "https://tiles.example/styles/city",
      attribution: "Example Maps",
      qualityTier: "configured",
      themePolicy: "preserve-provider",
    });
    expect(provider.customAttribution).toContain("Example Maps");
  });
});

describe("RouteMind full-vector basemap theme", () => {
  const layer = (id: string, type: string): BasemapStyleLayer => ({ id, type });
  const value = (id: string, type: string, property: string) =>
    resolveRouteMindBasemapPaint(layer(id, type)).find((mutation) => mutation.property === property)
      ?.value;

  it("keeps separate water, land-use, and urban texture colors", () => {
    expect(value("water", "fill", "fill-color")).toBe("#12333d");
    expect(value("park", "fill", "fill-color")).toBe("#19312a");
    expect(value("landuse_residential", "fill", "fill-color")).toBe("#1c282e");
    expect(value("landcover_wetland", "fill", "fill-color")).toBe("#19343a");
    expect(value("landuse_hospital", "fill", "fill-color")).toBe("#30262b");
  });

  it("preserves a legible hierarchy across road, bridge, tunnel, rail, and water lines", () => {
    expect(value("road_motorway", "line", "line-color")).toBe("#60747a");
    expect(value("road_secondary_tertiary", "line", "line-color")).toBe("#455a60");
    expect(value("road_minor", "line", "line-color")).toBe("#34484e");
    expect(value("bridge_motorway_casing", "line", "line-color")).toBe("#172328");
    expect(value("tunnel_trunk_primary", "line", "line-opacity")).toBe(0.62);
    expect(value("road_major_rail", "line", "line-color")).toBe("#66787a");
    expect(value("waterway_river", "line", "line-color")).toBe("#3a7480");
  });

  it("keeps city, district, road, water, and POI labels at different emphasis", () => {
    expect(value("label_city", "symbol", "text-opacity")).toBe(0.7);
    expect(value("label_other", "symbol", "text-opacity")).toBe(0.45);
    expect(value("highway-name-major", "symbol", "text-opacity")).toBe(0.66);
    expect(value("water_name_point_label", "symbol", "text-color")).toBe("#77aeb4");
    expect(value("poi_r7", "symbol", "icon-opacity")).toBe(0.24);
  });

  it("changes paint only and tolerates unsupported provider properties", () => {
    const setPaintProperty = vi.fn((_: string, property: string) => {
      if (property === "icon-opacity") throw new Error("not supported");
    });
    const map = {
      getStyle: () => ({
        layers: [layer("background", "background"), layer("label_city", "symbol")],
      }),
      setPaintProperty,
    };
    expect(applyRouteMindBasemapTheme(map)).toBe(5);
    expect(setPaintProperty).toHaveBeenCalledWith("background", "background-color", "#111c21");
    expect(setPaintProperty).toHaveBeenCalledWith("label_city", "text-color", "#d1ddda");
  });
});
