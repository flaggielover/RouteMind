export type GeoOperationsSource = "DEMO" | "SIMULATION" | "REPLAY" | "BENCHMARK";
export type GeoOperationsScope = "national" | "multi-city" | "city";
export type GeoAggregationLevel = "city-centroid" | "operational-point";

export interface GeoCitySignal {
  cityId: string;
  cityName: string;
  latitude: number;
  longitude: number;
  orderVolume: number;
  supplyCount: number;
  riskIndex: number;
  strategy: string;
}

export interface MultiCityGeoProjection {
  source: GeoOperationsSource;
  sourceLabel: string;
  scope: GeoOperationsScope;
  aggregationLevel: GeoAggregationLevel;
  rawPointsVisible: boolean;
  zoom: number;
  cities: readonly GeoCitySignal[];
  totalOrders: number;
  totalSupply: number;
  averageRiskIndex: number;
  projectionDigest: string;
}

const SOURCE_LABELS: Record<GeoOperationsSource, string> = {
  DEMO: "DEMO data",
  SIMULATION: "SIMULATION data",
  REPLAY: "REPLAY data",
  BENCHMARK: "BENCHMARK data",
};

export function createMultiCityGeoProjection(
  cities: readonly GeoCitySignal[],
  scope: GeoOperationsScope,
  source: GeoOperationsSource,
): MultiCityGeoProjection {
  if (!cities.length) throw new RangeError("At least one city signal is required");
  const ids = cities.map((city) => city.cityId);
  if (new Set(ids).size !== ids.length) throw new RangeError("City signal ids must be unique");
  cities.forEach(validateCitySignal);
  const rawPointsVisible = scope === "city";
  const aggregationLevel: GeoAggregationLevel = rawPointsVisible
    ? "operational-point"
    : "city-centroid";
  const zoom = scope === "national" ? 4 : scope === "multi-city" ? 6 : 11;
  const totalOrders = cities.reduce((sum, city) => sum + city.orderVolume, 0);
  const totalSupply = cities.reduce((sum, city) => sum + city.supplyCount, 0);
  const averageRiskIndex = cities.reduce((sum, city) => sum + city.riskIndex, 0) / cities.length;
  return {
    source,
    sourceLabel: SOURCE_LABELS[source],
    scope,
    aggregationLevel,
    rawPointsVisible,
    zoom,
    cities: cities.map((city) => ({ ...city })),
    totalOrders,
    totalSupply,
    averageRiskIndex,
    projectionDigest: digest({ source, scope, aggregationLevel, cities }),
  };
}

function validateCitySignal(city: GeoCitySignal): void {
  if (!city.cityId.trim() || !city.cityName.trim() || !city.strategy.trim()) {
    throw new RangeError("City signal identity must not be blank");
  }
  if (
    !Number.isFinite(city.latitude) ||
    city.latitude < -90 ||
    city.latitude > 90 ||
    !Number.isFinite(city.longitude) ||
    city.longitude < -180 ||
    city.longitude > 180
  ) {
    throw new RangeError("City signal coordinates must be valid WGS84 values");
  }
  if (
    !Number.isFinite(city.orderVolume) ||
    city.orderVolume < 0 ||
    !Number.isFinite(city.supplyCount) ||
    city.supplyCount < 0 ||
    !Number.isFinite(city.riskIndex) ||
    city.riskIndex < 0 ||
    city.riskIndex > 1
  ) {
    throw new RangeError("City signal metrics must be finite and bounded");
  }
}

function digest(value: unknown): string {
  const encoded = JSON.stringify(value, Object.keys(value as object).sort());
  let hash = 2166136261;
  for (const character of encoded) hash = Math.imul(hash ^ character.charCodeAt(0), 16777619);
  return (hash >>> 0).toString(16).padStart(8, "0").repeat(8);
}

export const demoMultiCitySignals: readonly GeoCitySignal[] = Object.freeze([
  {
    cityId: "shanghai",
    cityName: "Shanghai",
    latitude: 31.2304,
    longitude: 121.4737,
    orderVolume: 1820,
    supplyCount: 620,
    riskIndex: 0.38,
    strategy: "risk-aware",
  },
  {
    cityId: "shenzhen",
    cityName: "Shenzhen",
    latitude: 22.5431,
    longitude: 114.0579,
    orderVolume: 1560,
    supplyCount: 540,
    riskIndex: 0.42,
    strategy: "weighted-greedy",
  },
  {
    cityId: "chengdu",
    cityName: "Chengdu",
    latitude: 30.657,
    longitude: 104.0668,
    orderVolume: 1240,
    supplyCount: 460,
    riskIndex: 0.31,
    strategy: "nearest",
  },
]);
