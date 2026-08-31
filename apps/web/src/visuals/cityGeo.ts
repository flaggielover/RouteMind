export type CityId = "shanghai" | "shenzhen" | "chengdu";
export type LngLat = readonly [longitude: number, latitude: number];
export type TrajectoryState = "active" | "recent" | "selected";
export type CourierAgentState = "on-route" | "available" | "rebalancing";
export type OperationalLodMode = "city" | "district" | "selected";

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

export interface CourierAgent {
  id: string;
  cityId: CityId;
  state: CourierAgentState;
  path: readonly LngLat[];
  position: LngLat;
  baseProgress: number;
  velocity: number;
  risk: number;
  trajectoryId?: string;
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
  coordinate: LngLat;
  polygon: readonly LngLat[];
  pressure: number;
  courierSupply: number;
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
  courierAgents: readonly CourierAgent[];
  trajectories: readonly CourierTrajectory[];
  nodes: readonly OperationalNode[];
  hotspots: readonly SpatialHotspot[];
  riskZones: readonly SpatialRiskZone[];
  flows: readonly AggregateFlow[];
  provenance: "deterministic-demo";
  generatedAt: string;
}

export interface CityOperationalLod {
  mode: OperationalLodMode;
  courierAgents: readonly CourierAgent[];
  trajectories: readonly CourierTrajectory[];
  focusCoordinate: LngLat;
}

export interface CityOperationalLodOptions {
  mode: OperationalLodMode;
  focusCoordinate?: LngLat;
  selectedTrajectoryId?: string | null;
}

export interface CityDemoDensity {
  courierCount: number;
  emphasizedTrajectoryCount: number;
  districtTrajectoryCount: number;
}

export const CITY_DEMO_DENSITY: Readonly<Record<CityId, CityDemoDensity>> = Object.freeze({
  shanghai: { courierCount: 120, emphasizedTrajectoryCount: 32, districtTrajectoryCount: 16 },
  shenzhen: { courierCount: 90, emphasizedTrajectoryCount: 26, districtTrajectoryCount: 12 },
  chengdu: { courierCount: 104, emphasizedTrajectoryCount: 28, districtTrajectoryCount: 14 },
});

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

interface RoadCorridor {
  fromAnchor: number;
  toAnchor: number;
  points: readonly LngLat[];
}

const CITY_ROAD_CORRIDORS: Readonly<Record<CityId, readonly RoadCorridor[]>> = {
  shanghai: [
    {
      fromAnchor: 1,
      toAnchor: 2,
      points: [
        [121.4492, 31.2296],
        [121.458, 31.2302],
        [121.4678, 31.231],
        [121.4737, 31.2304],
        [121.4818, 31.233],
        [121.4894, 31.2358],
        [121.4968, 31.2372],
        [121.5052, 31.2397],
      ],
    },
    {
      fromAnchor: 3,
      toAnchor: 4,
      points: [
        [121.4374, 31.1884],
        [121.4458, 31.197],
        [121.4536, 31.207],
        [121.465, 31.2168],
        [121.4772, 31.225],
        [121.4896, 31.234],
        [121.4994, 31.244],
        [121.5106, 31.253],
        [121.5265, 31.2638],
      ],
    },
    {
      fromAnchor: 1,
      toAnchor: 4,
      points: [
        [121.4492, 31.2296],
        [121.454, 31.237],
        [121.463, 31.244],
        [121.474, 31.2485],
        [121.484, 31.252],
        [121.4934, 31.2576],
        [121.506, 31.2605],
        [121.518, 31.262],
        [121.5265, 31.2638],
      ],
    },
    {
      fromAnchor: 3,
      toAnchor: 2,
      points: [
        [121.4374, 31.1884],
        [121.449, 31.192],
        [121.459, 31.198],
        [121.469, 31.206],
        [121.479, 31.213],
        [121.489, 31.219],
        [121.497, 31.227],
        [121.501, 31.234],
        [121.5052, 31.2397],
      ],
    },
    {
      fromAnchor: 0,
      toAnchor: 4,
      points: [
        [121.4737, 31.2304],
        [121.476, 31.239],
        [121.481, 31.247],
        [121.489, 31.253],
        [121.4934, 31.2576],
        [121.503, 31.259],
        [121.514, 31.261],
        [121.5265, 31.2638],
      ],
    },
    {
      fromAnchor: 1,
      toAnchor: 2,
      points: [
        [121.4492, 31.2296],
        [121.451, 31.221],
        [121.46, 31.216],
        [121.471, 31.2165],
        [121.482, 31.22],
        [121.492, 31.226],
        [121.499, 31.232],
        [121.5052, 31.2397],
      ],
    },
    {
      fromAnchor: 3,
      toAnchor: 4,
      points: [
        [121.4374, 31.1884],
        [121.448, 31.184],
        [121.46, 31.186],
        [121.472, 31.194],
        [121.484, 31.205],
        [121.495, 31.219],
        [121.505, 31.235],
        [121.514, 31.249],
        [121.5265, 31.2638],
      ],
    },
    {
      fromAnchor: 5,
      toAnchor: 2,
      points: [
        [121.4934, 31.2576],
        [121.496, 31.252],
        [121.498, 31.247],
        [121.5, 31.243],
        [121.5052, 31.2397],
      ],
    },
  ],
  shenzhen: [
    {
      fromAnchor: 1,
      toAnchor: 2,
      points: [
        [113.9304, 22.5329],
        [113.923, 22.529],
        [113.913, 22.525],
        [113.903, 22.521],
        [113.8955, 22.5153],
      ],
    },
    {
      fromAnchor: 1,
      toAnchor: 4,
      points: [
        [113.9304, 22.5329],
        [113.952, 22.535],
        [113.978, 22.536],
        [114.004, 22.539],
        [114.028, 22.542],
        [114.0579, 22.5431],
        [114.083, 22.548],
        [114.104, 22.562],
        [114.116, 22.581],
        [114.1219, 22.6028],
      ],
    },
    {
      fromAnchor: 3,
      toAnchor: 2,
      points: [
        [114.1178, 22.5487],
        [114.098, 22.547],
        [114.078, 22.545],
        [114.0579, 22.5431],
        [114.032, 22.541],
        [114.006, 22.537],
        [113.979, 22.532],
        [113.951, 22.525],
        [113.925, 22.52],
        [113.8955, 22.5153],
      ],
    },
    {
      fromAnchor: 3,
      toAnchor: 4,
      points: [
        [114.1178, 22.5487],
        [114.119, 22.559],
        [114.118, 22.573],
        [114.119, 22.588],
        [114.1219, 22.6028],
      ],
    },
    {
      fromAnchor: 5,
      toAnchor: 0,
      points: [
        [114.0328, 22.6567],
        [114.034, 22.637],
        [114.039, 22.619],
        [114.044, 22.598],
        [114.049, 22.578],
        [114.053, 22.56],
        [114.0579, 22.5431],
      ],
    },
    {
      fromAnchor: 1,
      toAnchor: 3,
      points: [
        [113.9304, 22.5329],
        [113.953, 22.535],
        [113.979, 22.537],
        [114.006, 22.54],
        [114.033, 22.542],
        [114.0579, 22.5431],
        [114.083, 22.545],
        [114.101, 22.547],
        [114.1178, 22.5487],
      ],
    },
    {
      fromAnchor: 5,
      toAnchor: 2,
      points: [
        [114.0328, 22.6567],
        [114.017, 22.638],
        [114.001, 22.619],
        [113.984, 22.599],
        [113.965, 22.579],
        [113.945, 22.56],
        [113.925, 22.543],
        [113.91, 22.529],
        [113.8955, 22.5153],
      ],
    },
    {
      fromAnchor: 0,
      toAnchor: 4,
      points: [
        [114.0579, 22.5431],
        [114.073, 22.548],
        [114.088, 22.555],
        [114.101, 22.566],
        [114.11, 22.578],
        [114.116, 22.591],
        [114.1219, 22.6028],
      ],
    },
  ],
  chengdu: [
    {
      fromAnchor: 1,
      toAnchor: 2,
      points: [
        [104.0431, 30.6384],
        [104.052, 30.642],
        [104.061, 30.648],
        [104.0668, 30.657],
        [104.075, 30.663],
        [104.086, 30.668],
        [104.1016, 30.6719],
      ],
    },
    {
      fromAnchor: 3,
      toAnchor: 4,
      points: [
        [104.0392, 30.6813],
        [104.047, 30.673],
        [104.056, 30.665],
        [104.0668, 30.657],
        [104.079, 30.648],
        [104.093, 30.638],
        [104.105, 30.628],
        [104.1172, 30.6221],
      ],
    },
    {
      fromAnchor: 1,
      toAnchor: 4,
      points: [
        [104.0431, 30.6384],
        [104.051, 30.631],
        [104.062, 30.626],
        [104.075, 30.622],
        [104.09, 30.619],
        [104.104, 30.619],
        [104.1172, 30.6221],
      ],
    },
    {
      fromAnchor: 3,
      toAnchor: 2,
      points: [
        [104.0392, 30.6813],
        [104.05, 30.688],
        [104.064, 30.691],
        [104.078, 30.689],
        [104.091, 30.682],
        [104.1016, 30.6719],
      ],
    },
    {
      fromAnchor: 5,
      toAnchor: 2,
      points: [
        [104.0655, 30.5708],
        [104.066, 30.587],
        [104.068, 30.603],
        [104.072, 30.619],
        [104.08, 30.637],
        [104.09, 30.654],
        [104.1016, 30.6719],
      ],
    },
    {
      fromAnchor: 1,
      toAnchor: 4,
      points: [
        [104.0431, 30.6384],
        [104.039, 30.624],
        [104.043, 30.609],
        [104.053, 30.596],
        [104.066, 30.589],
        [104.081, 30.59],
        [104.096, 30.598],
        [104.108, 30.609],
        [104.1172, 30.6221],
      ],
    },
    {
      fromAnchor: 3,
      toAnchor: 4,
      points: [
        [104.0392, 30.6813],
        [104.047, 30.696],
        [104.061, 30.705],
        [104.078, 30.707],
        [104.095, 30.701],
        [104.108, 30.689],
        [104.116, 30.674],
        [104.12, 30.657],
        [104.1172, 30.6221],
      ],
    },
    {
      fromAnchor: 5,
      toAnchor: 2,
      points: [
        [104.0655, 30.5708],
        [104.079, 30.579],
        [104.092, 30.591],
        [104.101, 30.606],
        [104.106, 30.624],
        [104.107, 30.643],
        [104.104, 30.659],
        [104.1016, 30.6719],
      ],
    },
  ],
};

export function isCityId(value: string): value is CityId {
  return cityIds.includes(value as CityId);
}

function seededUnit(seed: number, index: number): number {
  let value = (seed + index * 0x6d2b79f5) | 0;
  value = Math.imul(value ^ (value >>> 15), value | 1);
  value ^= value + Math.imul(value ^ (value >>> 7), value | 61);
  return ((value ^ (value >>> 14)) >>> 0) / 4294967296;
}

function clamp(value: number, minimum: number, maximum: number): number {
  return Math.min(maximum, Math.max(minimum, value));
}

function pointAlongPath(path: readonly LngLat[], progress: number): LngLat {
  if (path.length < 2) return path[0] ?? [0, 0];
  const bounded = clamp(progress, 0, 0.999999);
  const scaled = bounded * (path.length - 1);
  const index = Math.floor(scaled);
  const local = scaled - index;
  const from = path[index] ?? path[0]!;
  const to = path[index + 1] ?? from;
  return [from[0] + (to[0] - from[0]) * local, from[1] + (to[1] - from[1]) * local];
}

function routeVariant(
  city: CityGeoContext,
  corridor: RoadCorridor,
  variantIndex: number,
): readonly LngLat[] {
  const [[west, south], [east, north]] = city.bounds;
  const maximumOffset = city.id === "shenzhen" ? 0.00135 : 0.0009;
  const direction = seededUnit(city.seed, variantIndex + 2_000) * 2 - 1;
  const amplitude = maximumOffset * (0.28 + seededUnit(city.seed, variantIndex + 2_100) * 0.72);
  return corridor.points.map((point, pointIndex, points): LngLat => {
    if (pointIndex === 0 || pointIndex === points.length - 1) return point;
    const previous = points[pointIndex - 1] ?? point;
    const next = points[pointIndex + 1] ?? point;
    const dx = next[0] - previous[0];
    const dy = next[1] - previous[1];
    const magnitude = Math.hypot(dx, dy) || 1;
    const taper = Math.sin((Math.PI * pointIndex) / (points.length - 1));
    const localNoise = 0.72 + seededUnit(city.seed, variantIndex * 37 + pointIndex + 2_200) * 0.28;
    return [
      clamp(point[0] + (-dy / magnitude) * amplitude * direction * taper * localNoise, west, east),
      clamp(point[1] + (dx / magnitude) * amplitude * direction * taper * localNoise, south, north),
    ];
  });
}

const CITY_COURIER_PREFIX: Readonly<Record<CityId, string>> = {
  shanghai: "SH",
  shenzhen: "SZ",
  chengdu: "CD",
};

function courierId(cityId: CityId, index: number): string {
  return `${CITY_COURIER_PREFIX[cityId]}-C${String(index + 1).padStart(3, "0")}`;
}

function normalizedDistance(city: CityGeoContext, first: LngLat, second: LngLat): number {
  const longitudeSpan = city.bounds[1][0] - city.bounds[0][0];
  const latitudeSpan = city.bounds[1][1] - city.bounds[0][1];
  return Math.hypot((first[0] - second[0]) / longitudeSpan, (first[1] - second[1]) / latitudeSpan);
}

function routeFocus(route: CourierTrajectory): LngLat {
  return pointAlongPath(route.points, 0.5);
}

function hexCell(
  center: LngLat,
  radiusLongitude: number,
  radiusLatitude: number,
): readonly LngLat[] {
  return Array.from({ length: 7 }, (_, index) => {
    const angle = (Math.PI / 3) * (index % 6) + Math.PI / 6;
    return [
      center[0] + Math.cos(angle) * radiusLongitude,
      center[1] + Math.sin(angle) * radiusLatitude,
    ] as const;
  });
}

export function createCityOperationalDataset(cityId: CityId): CityOperationalDataset {
  const city = cityGeoCatalog[cityId];
  const corridors = CITY_ROAD_CORRIDORS[cityId];
  const density = CITY_DEMO_DENSITY[cityId];
  const routeCount = density.emphasizedTrajectoryCount;
  const trajectories = Array.from({ length: routeCount }, (_, index): CourierTrajectory => {
    const risk = 0.12 + seededUnit(city.seed, index) * 0.64;
    const corridor = corridors[index % corridors.length]!;
    const points = routeVariant(city, corridor, index);
    return {
      id: `${city.id}-trajectory-${index + 1}`,
      cityId: city.id,
      courierId: courierId(city.id, index),
      orderId: `${CITY_COURIER_PREFIX[city.id]}-O${2040 + index}`,
      state: index % 5 === 4 ? "recent" : "active",
      points,
      merchantId: city.anchors[corridor.fromAnchor]!.id,
      customerId: city.anchors[corridor.toAnchor]!.id,
      etaMinutes: 5 + Math.round(seededUnit(city.seed, index + 30) * 18),
      distanceKilometres: Number((1.8 + seededUnit(city.seed, index + 60) * 8.4).toFixed(1)),
      slaRisk: Number(risk.toFixed(2)),
      strategy: index % 3 === 0 ? "risk-aware" : "weighted-greedy",
      currentProgress: Number((0.22 + seededUnit(city.seed, index + 90) * 0.62).toFixed(2)),
    };
  });
  const courierAgents = Array.from({ length: density.courierCount }, (_, index): CourierAgent => {
    const emphasized = trajectories[index];
    const corridor = corridors[index % corridors.length]!;
    const path = emphasized?.points ?? routeVariant(city, corridor, index + routeCount);
    const baseProgress = Number((0.04 + seededUnit(city.seed, index + 320) * 0.9).toFixed(4));
    const state: CourierAgentState = emphasized
      ? emphasized.state === "recent"
        ? "rebalancing"
        : "on-route"
      : index % 7 === 0
        ? "available"
        : index % 5 === 0
          ? "rebalancing"
          : "on-route";
    return {
      id: courierId(city.id, index),
      cityId,
      state,
      path,
      position: pointAlongPath(path, baseProgress),
      baseProgress,
      velocity: Number((0.0035 + seededUnit(city.seed, index + 420) * 0.0075).toFixed(5)),
      risk:
        emphasized?.slaRisk ??
        Number((0.08 + seededUnit(city.seed, index + 520) * 0.78).toFixed(2)),
      ...(emphasized ? { trajectoryId: emphasized.id } : {}),
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
  const hotspots = city.anchors.slice(0, 5).map((anchor, index): SpatialHotspot => ({
    id: `${city.id}-hotspot-${index + 1}`,
    cityId,
    coordinate: anchor.coordinate,
    pressure: Number((0.35 + seededUnit(city.seed, index + 120) * 0.6).toFixed(2)),
    courierSupply: Number((0.28 + seededUnit(city.seed, index + 140) * 0.62).toFixed(2)),
    risk: Number((0.14 + seededUnit(city.seed, index + 160) * 0.72).toFixed(2)),
  }));
  const riskZones = hotspots.flatMap((hotspot, hotspotIndex) =>
    [0, 1].map((cellIndex): SpatialRiskZone => {
      const radiusLongitude =
        city.id === "shenzhen" ? 0.0084 : city.id === "chengdu" ? 0.0062 : 0.0054;
      const radiusLatitude = city.id === "shenzhen" ? 0.0052 : 0.0044;
      const direction = hotspotIndex % 2 === 0 ? 1 : -1;
      const coordinate: LngLat =
        cellIndex === 0
          ? hotspot.coordinate
          : [
              hotspot.coordinate[0] + radiusLongitude * 1.45 * direction,
              hotspot.coordinate[1] + radiusLatitude * 1.05,
            ];
      const localRisk = Math.min(0.96, hotspot.risk * (cellIndex === 0 ? 1 : 0.78));
      return {
        id: `${city.id}-risk-cell-${hotspotIndex + 1}-${cellIndex + 1}`,
        cityId,
        label: `${city.anchors[hotspotIndex]!.label} SLA cell`,
        coordinate,
        polygon: hexCell(coordinate, radiusLongitude, radiusLatitude),
        pressure: hotspot.pressure,
        courierSupply: hotspot.courierSupply,
        risk: Number(localRisk.toFixed(2)),
      };
    }),
  );
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
    courierAgents,
    trajectories,
    nodes,
    hotspots,
    riskZones,
    flows,
    provenance: "deterministic-demo",
    generatedAt: "2026-08-31T08:00:00Z",
  };
}

export function projectCityOperationalLod(
  dataset: CityOperationalDataset,
  options: CityOperationalLodOptions,
): CityOperationalLod {
  const focusCoordinate = options.focusCoordinate ?? dataset.city.center;
  if (options.mode === "city") {
    return {
      mode: "city",
      courierAgents: dataset.courierAgents,
      trajectories: dataset.trajectories,
      focusCoordinate,
    };
  }

  const selected = options.selectedTrajectoryId
    ? (dataset.trajectories.find((route) => route.id === options.selectedTrajectoryId) ?? null)
    : null;
  const routeFocusCoordinate = selected ? routeFocus(selected) : focusCoordinate;
  const rankedRoutes = [...dataset.trajectories].sort((first, second) => {
    if (selected && first.id === selected.id) return -1;
    if (selected && second.id === selected.id) return 1;
    const distanceDifference =
      normalizedDistance(dataset.city, routeFocus(first), routeFocusCoordinate) -
      normalizedDistance(dataset.city, routeFocus(second), routeFocusCoordinate);
    if (Math.abs(distanceDifference) > 0.000001) return distanceDifference;
    const riskDifference = second.slaRisk - first.slaRisk;
    if (Math.abs(riskDifference) > 0.000001) return riskDifference;
    return first.id.localeCompare(second.id);
  });
  const trajectoryLimit =
    options.mode === "selected"
      ? Math.min(5, rankedRoutes.length)
      : CITY_DEMO_DENSITY[dataset.city.id].districtTrajectoryCount;
  const trajectories = rankedRoutes.slice(0, trajectoryLimit);
  const requiredCourierIds = new Set(trajectories.map((route) => route.courierId));
  const courierLimit =
    options.mode === "selected"
      ? Math.min(22, dataset.courierAgents.length)
      : Math.round(dataset.courierAgents.length * 0.42);
  const rankedCouriers = [...dataset.courierAgents].sort((first, second) => {
    if (selected && first.id === selected.courierId) return -1;
    if (selected && second.id === selected.courierId) return 1;
    const distanceDifference =
      normalizedDistance(dataset.city, first.position, routeFocusCoordinate) -
      normalizedDistance(dataset.city, second.position, routeFocusCoordinate);
    if (Math.abs(distanceDifference) > 0.000001) return distanceDifference;
    return first.id.localeCompare(second.id);
  });
  const visibleCourierIds = new Set(rankedCouriers.slice(0, courierLimit).map((agent) => agent.id));
  requiredCourierIds.forEach((id) => visibleCourierIds.add(id));
  return {
    mode: options.mode,
    courierAgents: dataset.courierAgents.filter((agent) => visibleCourierIds.has(agent.id)),
    trajectories,
    focusCoordinate: routeFocusCoordinate,
  };
}

export function selectionExists(
  dataset: CityOperationalDataset,
  trajectoryId: string | null,
): boolean {
  return trajectoryId === null || dataset.trajectories.some((route) => route.id === trajectoryId);
}
