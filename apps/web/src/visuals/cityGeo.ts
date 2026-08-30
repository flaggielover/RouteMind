export type CityId = "shanghai" | "shenzhen" | "chengdu";
export type LngLat = readonly [longitude: number, latitude: number];
export type TrajectoryState = "active" | "recent" | "selected";

export interface CityGeoContext {
  id: CityId;
  name: string;
  nameZh: string;
  center: LngLat;
  bounds: readonly [southWest: LngLat, northEast: LngLat];
  zoom: number;
  pitch: number;
  bearing: number;
  seed: number;
  character: string;
  fallbackWaterways: readonly (readonly LngLat[])[];
  anchors: readonly CityAnchor[];
}

export interface CityAnchor {
  id: string;
  label: string;
  coordinate: LngLat;
  role: "merchant" | "customer" | "hub";
}

export interface CourierTrajectory {
  id: string;
  cityId: CityId;
  courierId: string;
  orderId: string;
  state: TrajectoryState;
  points: readonly LngLat[];
  merchantId: string;
  customerId: string;
  etaMinutes: number;
  distanceKilometres: number;
  slaRisk: number;
  strategy: string;
  currentProgress: number;
}

export interface OperationalNode {
  id: string;
  cityId: CityId;
  kind: "courier" | "merchant" | "customer";
  label: string;
  coordinate: LngLat;
  status: string;
  trajectoryId?: string;
}

export interface SpatialHotspot {
  id: string;
  cityId: CityId;
  coordinate: LngLat;
  pressure: number;
  courierSupply: number;
  risk: number;
}

export interface SpatialRiskZone {
  id: string;
  cityId: CityId;
  label: string;
  polygon: readonly LngLat[];
  risk: number;
}

export interface AggregateFlow {
  id: string;
  cityId: CityId;
  from: LngLat;
  to: LngLat;
  courierCount: number;
  risk: number;
  label: string;
}

export interface CityOperationalDataset {
  city: CityGeoContext;
  trajectories: readonly CourierTrajectory[];
  nodes: readonly OperationalNode[];
  hotspots: readonly SpatialHotspot[];
  riskZones: readonly SpatialRiskZone[];
  flows: readonly AggregateFlow[];
  provenance: "deterministic-demo";
  generatedAt: string;
}

const SHANGHAI_ANCHORS: readonly CityAnchor[] = [
  {
    id: "sh-peoples-square",
    label: "People's Square hub",
    coordinate: [121.4737, 31.2304],
    role: "hub",
  },
  { id: "sh-jingan", label: "Jing'an merchant", coordinate: [121.4492, 31.2296], role: "merchant" },
  {
    id: "sh-lujiazui",
    label: "Lujiazui delivery",
    coordinate: [121.5052, 31.2397],
    role: "customer",
  },
  {
    id: "sh-xujiahui",
    label: "Xujiahui merchant",
    coordinate: [121.4374, 31.1884],
    role: "merchant",
  },
  { id: "sh-yangpu", label: "Yangpu delivery", coordinate: [121.5265, 31.2638], role: "customer" },
  { id: "sh-hongkou", label: "Hongkou hub", coordinate: [121.4934, 31.2576], role: "hub" },
];

const SHENZHEN_ANCHORS: readonly CityAnchor[] = [
  { id: "sz-futian", label: "Futian hub", coordinate: [114.0579, 22.5431], role: "hub" },
  {
    id: "sz-nanshan",
    label: "Nanshan merchant",
    coordinate: [113.9304, 22.5329],
    role: "merchant",
  },
  {
    id: "sz-qianhai",
    label: "Qianhai delivery",
    coordinate: [113.8955, 22.5153],
    role: "customer",
  },
  { id: "sz-luohu", label: "Luohu merchant", coordinate: [114.1178, 22.5487], role: "merchant" },
  { id: "sz-buji", label: "Buji delivery", coordinate: [114.1219, 22.6028], role: "customer" },
  { id: "sz-longhua", label: "Longhua hub", coordinate: [114.0328, 22.6567], role: "hub" },
];

const CHENGDU_ANCHORS: readonly CityAnchor[] = [
  { id: "cd-tianfu", label: "Tianfu Square hub", coordinate: [104.0668, 30.657], role: "hub" },
  { id: "cd-wuhou", label: "Wuhou merchant", coordinate: [104.0431, 30.6384], role: "merchant" },
  {
    id: "cd-chenghua",
    label: "Chenghua delivery",
    coordinate: [104.1016, 30.6719],
    role: "customer",
  },
  {
    id: "cd-qingyang",
    label: "Qingyang merchant",
    coordinate: [104.0392, 30.6813],
    role: "merchant",
  },
  {
    id: "cd-jinjiang",
    label: "Jinjiang delivery",
    coordinate: [104.1172, 30.6221],
    role: "customer",
  },
  { id: "cd-gaoxin", label: "Gaoxin hub", coordinate: [104.0655, 30.5708], role: "hub" },
];

export const cityGeoCatalog: Readonly<Record<CityId, CityGeoContext>> = Object.freeze({
  shanghai: {
    id: "shanghai",
    name: "Shanghai",
    nameZh: "上海",
    center: [121.4737, 31.2304],
    bounds: [
      [121.405, 31.165],
      [121.555, 31.285],
    ],
    zoom: 11.55,
    pitch: 38,
    bearing: -9,
    seed: 31023,
    character: "Cross-river metropolitan delivery flow",
    fallbackWaterways: [
      [
        [121.489, 31.285],
        [121.491, 31.257],
        [121.498, 31.233],
        [121.506, 31.208],
        [121.512, 31.165],
      ],
    ],
    anchors: SHANGHAI_ANCHORS,
  },
  shenzhen: {
    id: "shenzhen",
    name: "Shenzhen",
    nameZh: "深圳",
    center: [114.0579, 22.5431],
    bounds: [
      [113.86, 22.46],
      [114.19, 22.69],
    ],
    zoom: 10.7,
    pitch: 35,
    bearing: -16,
    seed: 22054,
    character: "East-west multi-cluster balancing",
    fallbackWaterways: [
      [
        [113.86, 22.49],
        [113.94, 22.486],
        [114.03, 22.493],
        [114.11, 22.505],
        [114.19, 22.515],
      ],
    ],
    anchors: SHENZHEN_ANCHORS,
  },
  chengdu: {
    id: "chengdu",
    name: "Chengdu",
    nameZh: "成都",
    center: [104.0668, 30.657],
    bounds: [
      [103.985, 30.545],
      [104.15, 30.73],
    ],
    zoom: 10.95,
    pitch: 42,
    bearing: 8,
    seed: 30057,
    character: "Ring and radial local delivery circulation",
    fallbackWaterways: [
      [
        [104.01, 30.71],
        [104.036, 30.681],
        [104.059, 30.654],
        [104.084, 30.621],
        [104.108, 30.575],
      ],
    ],
    anchors: CHENGDU_ANCHORS,
  },
});

export const cityIds = Object.freeze(Object.keys(cityGeoCatalog) as CityId[]);

export function isCityId(value: string): value is CityId {
  return cityIds.includes(value as CityId);
}

function seededUnit(seed: number, index: number): number {
  let value = (seed + index * 0x6d2b79f5) | 0;
  value = Math.imul(value ^ (value >>> 15), value | 1);
  value ^= value + Math.imul(value ^ (value >>> 7), value | 61);
  return ((value ^ (value >>> 14)) >>> 0) / 4294967296;
}

function curveBetween(from: LngLat, to: LngLat, bend: number): readonly LngLat[] {
  return Array.from({ length: 7 }, (_, index) => {
    const t = index / 6;
    const arch = Math.sin(t * Math.PI) * bend;
    return [
      from[0] + (to[0] - from[0]) * t + arch * (to[1] - from[1]),
      from[1] + (to[1] - from[1]) * t - arch * (to[0] - from[0]),
    ] as const;
  });
}

function ringRoute(city: CityGeoContext, index: number): readonly LngLat[] {
  const radiusLng = 0.021 + (index % 3) * 0.009;
  const radiusLat = 0.017 + (index % 2) * 0.008;
  const start = (index * Math.PI) / 4;
  return Array.from({ length: 9 }, (_, pointIndex) => {
    const angle = start + (pointIndex / 8) * Math.PI * 1.32;
    return [
      city.center[0] + Math.cos(angle) * radiusLng,
      city.center[1] + Math.sin(angle) * radiusLat,
    ] as const;
  });
}

function routePoints(city: CityGeoContext, index: number): readonly LngLat[] {
  if (city.id === "chengdu" && index % 2 === 0) return ringRoute(city, index);
  const from = city.anchors[index % city.anchors.length]!.coordinate;
  const to = city.anchors[(index * 2 + 3) % city.anchors.length]!.coordinate;
  const direction = index % 2 === 0 ? 1 : -1;
  const bend = city.id === "shanghai" ? 0.12 * direction : 0.055 * direction;
  return curveBetween(from, to, bend);
}

function zonePolygon(center: LngLat, width: number, height: number): readonly LngLat[] {
  return [
    [center[0] - width, center[1] - height],
    [center[0] + width, center[1] - height * 0.72],
    [center[0] + width * 0.82, center[1] + height],
    [center[0] - width * 0.9, center[1] + height * 0.78],
  ];
}

export function createCityOperationalDataset(cityId: CityId): CityOperationalDataset {
  const city = cityGeoCatalog[cityId];
  const routeCount = cityId === "shenzhen" ? 11 : 10;
  const trajectories = Array.from({ length: routeCount }, (_, index): CourierTrajectory => {
    const risk = 0.12 + seededUnit(city.seed, index) * 0.64;
    return {
      id: `${city.id}-trajectory-${index + 1}`,
      cityId: city.id,
      courierId: `${city.id.slice(0, 2).toUpperCase()}-C${String(index + 11).padStart(2, "0")}`,
      orderId: `${city.id.slice(0, 2).toUpperCase()}-O${2040 + index}`,
      state: index < 6 ? "active" : "recent",
      points: routePoints(city, index),
      merchantId: city.anchors[index % city.anchors.length]!.id,
      customerId: city.anchors[(index * 2 + 3) % city.anchors.length]!.id,
      etaMinutes: 5 + Math.round(seededUnit(city.seed, index + 30) * 18),
      distanceKilometres: Number((1.8 + seededUnit(city.seed, index + 60) * 8.4).toFixed(1)),
      slaRisk: Number(risk.toFixed(2)),
      strategy: index % 3 === 0 ? "risk-aware" : "weighted-greedy",
      currentProgress: Number((0.22 + seededUnit(city.seed, index + 90) * 0.62).toFixed(2)),
    };
  });
  const nodes: OperationalNode[] = city.anchors.map((anchor) => ({
    id: anchor.id,
    cityId,
    kind: anchor.role === "hub" ? "merchant" : anchor.role,
    label: anchor.label,
    coordinate: anchor.coordinate,
    status:
      anchor.role === "merchant"
        ? "pickup origin"
        : anchor.role === "customer"
          ? "delivery destination"
          : "dispatch hub",
  }));
  trajectories
    .filter((trajectory) => trajectory.state === "active")
    .forEach((trajectory) => {
      const routeIndex = Math.min(
        trajectory.points.length - 1,
        Math.floor(trajectory.currentProgress * trajectory.points.length),
      );
      nodes.push({
        id: trajectory.courierId,
        cityId,
        kind: "courier",
        label: `Courier ${trajectory.courierId}`,
        coordinate: trajectory.points[routeIndex]!,
        status: "on route",
        trajectoryId: trajectory.id,
      });
    });
  const hotspots = city.anchors.slice(0, 5).map((anchor, index): SpatialHotspot => ({
    id: `${city.id}-hotspot-${index + 1}`,
    cityId,
    coordinate: anchor.coordinate,
    pressure: Number((0.35 + seededUnit(city.seed, index + 120) * 0.6).toFixed(2)),
    courierSupply: Number((0.28 + seededUnit(city.seed, index + 140) * 0.62).toFixed(2)),
    risk: Number((0.14 + seededUnit(city.seed, index + 160) * 0.72).toFixed(2)),
  }));
  const riskZones = hotspots.slice(0, 3).map((hotspot, index): SpatialRiskZone => ({
    id: `${city.id}-risk-zone-${index + 1}`,
    cityId,
    label: `${city.anchors[index]!.label} SLA zone`,
    polygon: zonePolygon(hotspot.coordinate, city.id === "shenzhen" ? 0.018 : 0.012, 0.009),
    risk: hotspot.risk,
  }));
  const flows = [0, 1, 2].map((index): AggregateFlow => ({
    id: `${city.id}-flow-${index + 1}`,
    cityId,
    from: city.anchors[index]!.coordinate,
    to: city.anchors[(index + 3) % city.anchors.length]!.coordinate,
    courierCount: 14 + Math.round(seededUnit(city.seed, index + 180) * 36),
    risk: Number((0.18 + seededUnit(city.seed, index + 200) * 0.58).toFixed(2)),
    label: `${city.anchors[index]!.label} to ${city.anchors[(index + 3) % city.anchors.length]!.label}`,
  }));
  return {
    city,
    trajectories,
    nodes,
    hotspots,
    riskZones,
    flows,
    provenance: "deterministic-demo",
    generatedAt: "2026-08-31T08:00:00Z",
  };
}

export function selectionExists(
  dataset: CityOperationalDataset,
  trajectoryId: string | null,
): boolean {
  return trajectoryId === null || dataset.trajectories.some((route) => route.id === trajectoryId);
}
