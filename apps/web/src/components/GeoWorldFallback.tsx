import type { CityOperationalDataset, LngLat } from "../visuals/cityGeo";

interface GeoWorldFallbackProps {
  dataset: CityOperationalDataset;
  reason?: string;
}

function project(dataset: CityOperationalDataset, point: LngLat): readonly [number, number] {
  const [[west, south], [east, north]] = dataset.city.bounds;
  return [
    ((point[0] - west) / (east - west)) * 100,
    (1 - (point[1] - south) / (north - south)) * 100,
  ];
}

function points(dataset: CityOperationalDataset, path: readonly LngLat[]): string {
  return path.map((point) => project(dataset, point).join(",")).join(" ");
}

export function GeoWorldFallback({
  dataset,
  reason = "Map capability unavailable",
}: GeoWorldFallbackProps) {
  return (
    <section className="geo-world-fallback" aria-label={`${dataset.city.name} geographic fallback`}>
      <svg
        viewBox="0 0 100 100"
        role="img"
        aria-label={`${dataset.city.name} static courier route geography`}
      >
        <rect width="100" height="100" className="geo-fallback-land" />
        {dataset.city.fallbackWaterways.map((waterway, index) => (
          <polyline
            key={`water-${index}`}
            points={points(dataset, waterway)}
            className="geo-fallback-water"
          />
        ))}
        {dataset.riskZones.map((zone) => (
          <polygon
            key={zone.id}
            points={points(dataset, zone.polygon)}
            className="geo-fallback-risk"
          />
        ))}
        {dataset.trajectories.map((route) => (
          <polyline
            key={route.id}
            points={points(dataset, route.points)}
            className={
              route.state === "active" ? "geo-fallback-route active" : "geo-fallback-route recent"
            }
          />
        ))}
        {dataset.nodes.map((node) => {
          const [x, y] = project(dataset, node.coordinate);
          return (
            <circle
              key={node.id}
              cx={x}
              cy={y}
              r={node.kind === "courier" ? 1.2 : 0.8}
              className={`geo-fallback-node ${node.kind}`}
            />
          );
        })}
        {dataset.courierAgents
          .filter((_, index) => index % 5 === 0)
          .map((agent) => {
            const [x, y] = project(dataset, agent.position);
            return (
              <circle key={agent.id} cx={x} cy={y} r={0.55} className="geo-fallback-node courier" />
            );
          })}
      </svg>
      <div className="geo-fallback-copy">
        <span>GEOGRAPHIC FALLBACK / DEMO</span>
        <strong>
          {dataset.city.name} / {dataset.city.nameZh}
        </strong>
        <small>{dataset.city.character}</small>
      </div>
      <dl className="geo-fallback-metrics">
        <div>
          <dt>Synthetic couriers</dt>
          <dd>{dataset.courierAgents.length}</dd>
        </div>
        <div>
          <dt>Routes</dt>
          <dd>{dataset.trajectories.length}</dd>
        </div>
        <div>
          <dt>Source</dt>
          <dd>SIMULATED</dd>
        </div>
      </dl>
      <p className="geo-fallback-reason">
        {reason}. Static geographic context and operational summaries remain available.
      </p>
    </section>
  );
}

export default GeoWorldFallback;
