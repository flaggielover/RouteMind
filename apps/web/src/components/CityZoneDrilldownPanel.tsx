import { Map, Route, ShieldAlert, Store, Truck } from "lucide-react";
import { useMemo, useState } from "react";
import type { OperationsSnapshot } from "../domain/model";
import { projectCityZoneDrilldown } from "../domain/cityZoneDrilldown";

interface CityZoneDrilldownPanelProps {
  snapshot: OperationsSnapshot;
}

export function CityZoneDrilldownPanel({ snapshot }: CityZoneDrilldownPanelProps) {
  const [zoom, setZoom] = useState(11);
  const projection = useMemo(() => projectCityZoneDrilldown(snapshot, zoom), [snapshot, zoom]);
  const freshnessLabel =
    projection.freshness === "fresh"
      ? "Fresh snapshot"
      : projection.freshness === "stale"
        ? "Stale snapshot"
        : projection.freshness === "empty"
          ? "Empty source"
          : "Source unavailable";

  return (
    <section className="panel city-zone-panel" aria-labelledby="city-zone-title">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">
            {projection.sourceLabel} · {freshnessLabel}
          </p>
          <h2 id="city-zone-title">City / zone drilldown</h2>
        </div>
        <span className="panel-meta">{projection.aggregation} aggregation</span>
      </div>
      <div className="city-zone-toolbar">
        <label htmlFor="city-zone-zoom">
          Zoom <strong>{zoom}</strong>
        </label>
        <input
          id="city-zone-zoom"
          type="range"
          min="4"
          max="12"
          step="1"
          value={zoom}
          onChange={(event) => setZoom(Number(event.target.value))}
          aria-describedby="city-zone-zoom-note"
        />
        <span id="city-zone-zoom-note" className="city-zone-zoom-note">
          {projection.aggregation === "city" ? "City aggregate" : "Zone detail"}
        </span>
      </div>
      <div className="city-zone-legend" aria-label="City zone legend">
        <span>
          <Map size={13} /> {projection.sourceLabel}
        </span>
        <span>
          <Store size={13} /> orders / merchants
        </span>
        <span>
          <Truck size={13} /> supply
        </span>
        <span>
          <ShieldAlert size={13} /> risk 0-100%
        </span>
        <span>
          <Route size={13} /> routes
        </span>
      </div>
      {projection.freshness !== "fresh" && (
        <div className="city-zone-state" role="status">
          {projection.freshness === "stale"
            ? "Snapshot is stale; metrics remain visible for inspection."
            : projection.freshness === "empty"
              ? "No orders, merchants, or couriers are present in this source."
              : "City and zone metrics are unavailable from this source."}
        </div>
      )}
      {projection.zones.length ? (
        <div
          className="city-zone-table-wrap"
          role="region"
          aria-label="City and zone metrics table"
          tabIndex={0}
        >
          <table className="city-zone-table">
            <caption className="sr-only">Source-backed city and zone operational metrics</caption>
            <thead>
              <tr>
                <th scope="col">Area</th>
                <th scope="col">Orders</th>
                <th scope="col">Merchants</th>
                <th scope="col">Supply</th>
                <th scope="col">Density / 100</th>
                <th scope="col">Risk</th>
                <th scope="col">Routes</th>
              </tr>
            </thead>
            <tbody>
              {projection.zones.map((zone) => (
                <tr key={zone.zoneId}>
                  <th scope="row">{zone.zoneLabel}</th>
                  <td data-label="Orders">{zone.orderCount}</td>
                  <td data-label="Merchants">{zone.merchantCount}</td>
                  <td data-label="Supply">
                    {zone.availableCourierCount}/{zone.courierCount}
                  </td>
                  <td data-label="Density / 100">{zone.densityPer100.toFixed(1)}</td>
                  <td data-label="Risk">{Math.round(zone.riskIndex * 100)}%</td>
                  <td data-label="Routes">{zone.routeCount}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="empty-state">No city or zone rows can be projected from this source.</p>
      )}
      <p className="city-zone-footnote">
        Derived from the selected Operations snapshot; schematic route bucketing is descriptive, not
        a new durable record.
      </p>
    </section>
  );
}
