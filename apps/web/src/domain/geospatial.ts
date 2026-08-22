export type MapEntityKind = "order" | "courier" | "merchant" | "zone";

export type MapCapabilityStatus = "available" | "not_configured" | "unavailable";

export type MapProjectionMode = "provider" | "local-fallback";

export interface GeographicCoordinate {
  latitude: number;
  longitude: number;
}

export interface MapBounds {
  north: number;
  south: number;
  east: number;
  west: number;
}

export interface MapMarker {
  id: string;
  kind: Exclude<MapEntityKind, "zone">;
  label: string;
  coordinate: GeographicCoordinate;
}

export interface MapRoute {
  id: string;
  label: string;
  coordinates: readonly GeographicCoordinate[];
}

export interface MapZone {
  id: string;
  label: string;
  polygon: readonly GeographicCoordinate[];
}

export interface MapSelection {
  kind: MapEntityKind;
  id: string;
}

export interface MapCapabilities {
  providerId: string;
  providerLabel: string;
  mode: MapProjectionMode;
  tiles: MapCapabilityStatus;
  routing: MapCapabilityStatus;
  attributionRequired: boolean;
  detail: string;
}

export interface MapProjectionInput {
  markers: readonly MapMarker[];
  routes: readonly MapRoute[];
  zones: readonly MapZone[];
  generatedAt: string;
  selection?: MapSelection | null;
  bounds?: MapBounds;
}

export interface MapProjection {
  mode: MapProjectionMode;
  generatedAt: string;
  bounds: MapBounds;
  center: GeographicCoordinate;
  zoom: number;
  markers: readonly MapMarker[];
  routes: readonly MapRoute[];
  zones: readonly MapZone[];
  selection: MapSelection | null;
  capabilities: MapCapabilities;
}

export interface GeospatialMapAdapter {
  readonly capabilities: MapCapabilities;
  project(input: MapProjectionInput): MapProjection;
  select(projection: MapProjection, selection: MapSelection | null): MapProjection;
}

export const localFallbackBounds: MapBounds = Object.freeze({
  north: 31.275,
  south: 31.185,
  east: 121.525,
  west: 121.415,
});

export const localSchematicMapCapabilities: MapCapabilities = Object.freeze({
  providerId: "local-schematic",
  providerLabel: "Local schematic fallback",
  mode: "local-fallback",
  tiles: "not_configured",
  routing: "not_configured",
  attributionRequired: false,
  detail: "No external tiles or paid routing credentials are required",
});

export function createGeographicCoordinate(input: GeographicCoordinate): GeographicCoordinate {
  if (
    !Number.isFinite(input.latitude) ||
    input.latitude < -90 ||
    input.latitude > 90 ||
    !Number.isFinite(input.longitude) ||
    input.longitude < -180 ||
    input.longitude > 180
  ) {
    throw new RangeError("Geographic coordinates must be finite and within WGS84 bounds");
  }
  return { latitude: input.latitude, longitude: input.longitude };
}

export function createMapBounds(input: MapBounds): MapBounds {
  const north = createGeographicCoordinate({ latitude: input.north, longitude: 0 }).latitude;
  const south = createGeographicCoordinate({ latitude: input.south, longitude: 0 }).latitude;
  const east = createGeographicCoordinate({ latitude: 0, longitude: input.east }).longitude;
  const west = createGeographicCoordinate({ latitude: 0, longitude: input.west }).longitude;
  if (north <= south || east <= west) {
    throw new RangeError(
      "Map bounds must have north greater than south and east greater than west",
    );
  }
  return { north, south, east, west };
}

export function normalizedToGeographicCoordinate(
  point: { x: number; y: number },
  bounds: MapBounds = localFallbackBounds,
): GeographicCoordinate {
  if (
    !Number.isFinite(point.x) ||
    !Number.isFinite(point.y) ||
    point.x < 0 ||
    point.x > 100 ||
    point.y < 0 ||
    point.y > 100
  ) {
    throw new RangeError("Schematic map coordinates must be finite percentages from 0 to 100");
  }
  const validBounds = createMapBounds(bounds);
  return createGeographicCoordinate({
    latitude: validBounds.south + ((100 - point.y) / 100) * (validBounds.north - validBounds.south),
    longitude: validBounds.west + (point.x / 100) * (validBounds.east - validBounds.west),
  });
}

function projectCoordinate(coordinate: GeographicCoordinate): GeographicCoordinate {
  return createGeographicCoordinate(coordinate);
}

function projectMarkers(markers: readonly MapMarker[]): readonly MapMarker[] {
  return markers.map((marker) => ({
    ...marker,
    coordinate: projectCoordinate(marker.coordinate),
  }));
}

function projectRoutes(routes: readonly MapRoute[]): readonly MapRoute[] {
  return routes.map((route) => ({
    ...route,
    coordinates: route.coordinates.map(projectCoordinate),
  }));
}

function projectZones(zones: readonly MapZone[]): readonly MapZone[] {
  return zones.map((zone) => ({
    ...zone,
    polygon: zone.polygon.map(projectCoordinate),
  }));
}

export const localSchematicMapAdapter: GeospatialMapAdapter = {
  capabilities: localSchematicMapCapabilities,
  project(input) {
    const bounds = createMapBounds(input.bounds ?? localFallbackBounds);
    const center = createGeographicCoordinate({
      latitude: (bounds.north + bounds.south) / 2,
      longitude: (bounds.east + bounds.west) / 2,
    });
    return {
      mode: "local-fallback",
      generatedAt: input.generatedAt,
      bounds,
      center,
      zoom: 12,
      markers: projectMarkers(input.markers),
      routes: projectRoutes(input.routes),
      zones: projectZones(input.zones),
      selection: input.selection ?? null,
      capabilities: localSchematicMapCapabilities,
    };
  },
  select(projection, selection) {
    return { ...projection, selection };
  },
};
