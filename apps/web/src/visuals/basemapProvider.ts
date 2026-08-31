export const OPENFREEMAP_LIBERTY_STYLE_URL = "https://tiles.openfreemap.org/styles/liberty";

export type BasemapThemePolicy = "routemind-graphite" | "preserve-provider";

export interface BasemapProviderConfig {
  id: string;
  label: string;
  styleUrl: string;
  dataProvenance: string;
  attribution: string;
  customAttribution: readonly string[];
  credentialRequirement: "none" | "provider-managed";
  qualityTier: "full-vector" | "configured";
  themePolicy: BasemapThemePolicy;
}

export interface ResolveBasemapProviderOptions {
  styleUrl?: string;
  attribution?: string;
  label?: string;
}

export const openFreeMapLibertyProvider: BasemapProviderConfig = Object.freeze({
  id: "openfreemap-liberty",
  label: "OpenFreeMap Liberty",
  styleUrl: OPENFREEMAP_LIBERTY_STYLE_URL,
  dataProvenance: "OpenStreetMap via the OpenMapTiles schema and OpenFreeMap",
  attribution: "OpenFreeMap · OpenMapTiles · OpenStreetMap contributors",
  customAttribution: Object.freeze(["RouteMind DEMO operations"]),
  credentialRequirement: "none",
  qualityTier: "full-vector",
  themePolicy: "routemind-graphite",
});

export function resolveBasemapProvider(
  options: ResolveBasemapProviderOptions = {},
): BasemapProviderConfig {
  const styleUrl = options.styleUrl?.trim();
  if (!styleUrl) return openFreeMapLibertyProvider;
  const attribution = options.attribution?.trim();
  return Object.freeze({
    id: "configured-maplibre-style",
    label: options.label?.trim() || "Configured MapLibre provider",
    styleUrl,
    dataProvenance: "Configured external MapLibre style and its declared sources",
    attribution: attribution || "Attribution supplied by the configured style sources",
    customAttribution: Object.freeze(
      ["RouteMind DEMO operations", attribution].filter((item): item is string => Boolean(item)),
    ),
    credentialRequirement: "provider-managed",
    qualityTier: "configured",
    themePolicy: "preserve-provider",
  });
}

export interface BasemapStyleLayer {
  id: string;
  type: string;
  source?: string;
  "source-layer"?: string;
}

export interface BasemapPaintMutation {
  property: string;
  value: unknown;
}

export interface BasemapThemeTarget {
  getStyle(): { layers?: readonly BasemapStyleLayer[] };
  setPaintProperty(layerId: string, property: string, value: unknown): void;
}

const LAND = "#111c21";
const HALO = "#091318";

function fillMutations(id: string): readonly BasemapPaintMutation[] {
  let color = "#182329";
  let opacity = 0.9;
  if (id === "water" || id.includes("water")) color = "#12333d";
  else if (id.includes("park")) color = "#19312a";
  else if (id.includes("wood")) color = "#1b302b";
  else if (id.includes("grass")) color = "#20342e";
  else if (id.includes("wetland")) color = "#19343a";
  else if (id.includes("sand")) color = "#342f29";
  else if (id.includes("residential")) {
    color = "#1c282e";
    opacity = 0.82;
  } else if (id.includes("hospital")) color = "#30262b";
  else if (id.includes("school")) color = "#2d2e2a";
  else if (id.includes("cemetery")) color = "#252d2a";
  else if (id.includes("pitch")) color = "#24352f";
  else if (id.includes("track")) color = "#26312e";
  else if (id.includes("road_area")) color = "#29363a";
  else if (id.includes("building")) color = "#24343a";
  return [
    { property: "fill-color", value: color },
    { property: "fill-opacity", value: opacity },
  ];
}

function roadColor(id: string): string {
  if (id.includes("casing")) return id.startsWith("bridge") ? "#172328" : "#081115";
  if (id.includes("motorway")) return "#60747a";
  if (id.includes("trunk_primary")) return "#52676d";
  if (id.includes("secondary_tertiary")) return "#455a60";
  if (id.includes("street") || id.includes("minor")) return "#34484e";
  if (id.includes("service_track")) return "#2c3e43";
  if (id.includes("path_pedestrian")) return "#33474b";
  if (id.includes("link")) return "#4c6267";
  return "#354a50";
}

function roadOpacity(id: string): number {
  if (id.startsWith("tunnel")) return id.includes("casing") ? 0.5 : 0.62;
  if (id.includes("service_track") || id.includes("path_pedestrian")) return 0.55;
  if (id.includes("minor") || id.includes("street")) return 0.68;
  if (id.includes("casing")) return 0.86;
  return 0.88;
}

function lineMutations(id: string): readonly BasemapPaintMutation[] {
  if (id.includes("waterway")) {
    return [
      { property: "line-color", value: "#3a7480" },
      { property: "line-opacity", value: 0.78 },
    ];
  }
  if (id.includes("rail")) {
    return [
      { property: "line-color", value: id.includes("hatching") ? "#303f43" : "#66787a" },
      { property: "line-opacity", value: id.includes("hatching") ? 0.42 : 0.62 },
    ];
  }
  if (id.includes("boundary")) {
    return [
      { property: "line-color", value: id.includes("disputed") ? "#8c7051" : "#4d6064" },
      { property: "line-opacity", value: id.includes("disputed") ? 0.62 : 0.48 },
    ];
  }
  if (id.includes("road") || id.startsWith("tunnel") || id.startsWith("bridge")) {
    return [
      { property: "line-color", value: roadColor(id) },
      { property: "line-opacity", value: roadOpacity(id) },
    ];
  }
  if (id.includes("park")) {
    return [
      { property: "line-color", value: "#29483e" },
      { property: "line-opacity", value: 0.7 },
    ];
  }
  return [
    { property: "line-color", value: "#415358" },
    { property: "line-opacity", value: 0.56 },
  ];
}

function symbolMutations(id: string): readonly BasemapPaintMutation[] {
  if (id.startsWith("road_one_way")) return [{ property: "icon-opacity", value: 0.5 }];
  const mutations: BasemapPaintMutation[] = [
    { property: "text-halo-color", value: HALO },
    { property: "text-halo-width", value: 1.2 },
  ];
  if (id.includes("water")) {
    mutations.push(
      { property: "text-color", value: "#77aeb4" },
      { property: "text-opacity", value: 0.7 },
    );
  } else if (id.includes("highway-name-major")) {
    mutations.push(
      { property: "text-color", value: "#a4b2b2" },
      { property: "text-opacity", value: 0.66 },
    );
  } else if (id.includes("highway-name")) {
    mutations.push(
      { property: "text-color", value: "#839596" },
      { property: "text-opacity", value: 0.48 },
    );
  } else if (id.includes("label_city") || id.includes("label_state")) {
    mutations.push(
      { property: "text-color", value: "#d1ddda" },
      { property: "text-opacity", value: 0.7 },
    );
  } else if (id.includes("label_town") || id.includes("label_village")) {
    mutations.push(
      { property: "text-color", value: "#a9bcba" },
      { property: "text-opacity", value: 0.58 },
    );
  } else if (id.includes("label_other")) {
    mutations.push(
      { property: "text-color", value: "#879b9a" },
      { property: "text-opacity", value: 0.45 },
    );
  } else if (id.includes("poi") || id.includes("airport")) {
    mutations.push(
      { property: "text-color", value: "#7e9191" },
      { property: "text-opacity", value: 0.42 },
      { property: "icon-opacity", value: 0.24 },
    );
  } else {
    mutations.push(
      { property: "text-color", value: "#93a4a4" },
      { property: "text-opacity", value: 0.6 },
      { property: "icon-opacity", value: 0.5 },
    );
  }
  return mutations;
}

export function resolveRouteMindBasemapPaint(
  layer: BasemapStyleLayer,
): readonly BasemapPaintMutation[] {
  const id = layer.id.toLowerCase();
  if (layer.type === "background") return [{ property: "background-color", value: LAND }];
  if (layer.type === "raster") {
    return [
      { property: "raster-saturation", value: -0.82 },
      { property: "raster-contrast", value: 0.16 },
      { property: "raster-brightness-max", value: 0.36 },
    ];
  }
  if (layer.type === "fill") return fillMutations(id);
  if (layer.type === "fill-extrusion") {
    return [
      { property: "fill-extrusion-color", value: "#293b40" },
      { property: "fill-extrusion-opacity", value: 0.62 },
    ];
  }
  if (layer.type === "line") return lineMutations(id);
  if (layer.type === "symbol") return symbolMutations(id);
  return [];
}

export function applyRouteMindBasemapTheme(map: BasemapThemeTarget): number {
  let applied = 0;
  for (const layer of map.getStyle().layers ?? []) {
    for (const mutation of resolveRouteMindBasemapPaint(layer)) {
      try {
        map.setPaintProperty(layer.id, mutation.property, mutation.value);
        applied += 1;
      } catch {
        // Provider styles may omit a paint capability; preserve their source value.
      }
    }
  }
  return applied;
}
