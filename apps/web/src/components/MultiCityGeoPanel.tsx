import { Globe2, MapPinned, ShieldAlert, Truck } from "lucide-react";
import { useMemo, useState } from "react";
import {
  createMultiCityGeoProjection,
  demoMultiCitySignals,
  type GeoOperationsScope,
} from "../domain/multiCityGeo";

const scopes: readonly { value: GeoOperationsScope; label: string }[] = [
  { value: "national", label: "National" },
  { value: "multi-city", label: "Multi-city" },
  { value: "city", label: "City detail" },
];

export function MultiCityGeoPanel() {
  const [scope, setScope] = useState<GeoOperationsScope>("national");
  const projection = useMemo(
    () => createMultiCityGeoProjection(demoMultiCitySignals, scope, "DEMO"),
    [scope],
  );

  return (
    <section className="panel multi-city-panel" aria-labelledby="multi-city-title">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">{projection.sourceLabel} · coordinate-backed signals</p>
          <h2 id="multi-city-title">Multi-city operations</h2>
        </div>
        <span className="panel-meta">Digest {projection.projectionDigest.slice(0, 10)}</span>
      </div>
      <div className="geo-scope-tabs" role="tablist" aria-label="Geo operations scope">
        {scopes.map((item) => (
          <button
            key={item.value}
            className={`geo-scope-tab ${scope === item.value ? "active" : ""}`}
            type="button"
            role="tab"
            aria-selected={scope === item.value}
            onClick={() => setScope(item.value)}
          >
            {item.label}
          </button>
        ))}
      </div>
      <div className="geo-summary" aria-label={`${projection.scope} geo summary`}>
        <div>
          <Globe2 size={16} />
          <span>
            <strong>{projection.cities.length}</strong>
            <small>cities</small>
          </span>
        </div>
        <div>
          <MapPinned size={16} />
          <span>
            <strong>{projection.totalOrders.toLocaleString()}</strong>
            <small>orders</small>
          </span>
        </div>
        <div>
          <Truck size={16} />
          <span>
            <strong>{projection.totalSupply.toLocaleString()}</strong>
            <small>supply</small>
          </span>
        </div>
        <div>
          <ShieldAlert size={16} />
          <span>
            <strong>{Math.round(projection.averageRiskIndex * 100)}%</strong>
            <small>average risk</small>
          </span>
        </div>
      </div>
      <div className="geo-scope-note" role="status">
        {projection.rawPointsVisible
          ? "City detail: operational points may render within this city."
          : `Scope zoom ${projection.zoom}: city-centroid aggregation hides raw points at ${projection.scope} scale.`}
      </div>
      <ul className="geo-city-list" aria-label="City operation signals">
        {projection.cities.map((city) => (
          <li key={city.cityId}>
            <span>
              <strong>{city.cityName}</strong>
              <small>
                {city.latitude.toFixed(2)}, {city.longitude.toFixed(2)} · {city.strategy}
              </small>
            </span>
            <span className="geo-city-metrics">
              <b>{city.orderVolume.toLocaleString()} orders</b>
              <small>{Math.round(city.riskIndex * 100)}% risk</small>
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}
