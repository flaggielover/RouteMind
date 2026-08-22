import { Navigation, Store, Truck, UserRound } from "lucide-react";
import type { Courier, DataAvailability, DataSourceMode, Order } from "../domain/model";
import { configuredTileMapAdapter } from "../domain/geospatial";

interface OperationsMapProps {
  orders: readonly Order[];
  couriers: readonly Courier[];
  selectedOrderId: string;
  onSelectOrder: (orderId: string) => void;
  availability: DataAvailability;
  source: DataSourceMode;
  generatedAt: string;
}

export function OperationsMap({
  orders,
  couriers,
  selectedOrderId,
  onSelectOrder,
  availability,
  source,
  generatedAt,
}: OperationsMapProps) {
  const selected = orders.find((order) => order.id === selectedOrderId) ?? orders[0];
  const mapAdapter = configuredTileMapAdapter(import.meta.env.VITE_MAP_TILE_URL_TEMPLATE);
  const mapCapabilities = mapAdapter.capabilities;
  return (
    <section className="panel map-panel" aria-labelledby="map-title">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">{mapCapabilities.providerLabel}</p>
          <h2 id="map-title">City dispatch map</h2>
        </div>
        <span className="panel-meta">
          {sourceLabel(source)} · {formatFreshness(generatedAt)}
        </span>
      </div>
      <div
        className="map-canvas"
        aria-label={`${mapCapabilities.providerLabel} dispatch map with live order and courier markers`}
      >
        {mapCapabilities.mode === "provider" && mapCapabilities.tileUrlTemplate && (
          <div
            className="map-tile-layer"
            aria-label={`${mapCapabilities.providerLabel} tile layer`}
            style={{
              backgroundImage: `url(${mapCapabilities.tileUrlTemplate
                .replace("{z}", "12")
                .replace("{x}", "3375")
                .replace("{y}", "1660")})`,
            }}
          />
        )}
        <div className="map-grid" aria-hidden="true" />
        <div className="map-road road-one" aria-hidden="true" />
        <div className="map-road road-two" aria-hidden="true" />
        <div className="map-road road-three" aria-hidden="true" />
        {selected?.route.map((point, index) => (
          <span
            className="route-node"
            key={`${selected.id}-route-${index}`}
            style={{ left: `${point.x}%`, top: `${point.y}%` }}
            aria-hidden="true"
          />
        ))}
        {orders.map((order) => {
          const origin = order.route[0];
          if (!origin) return null;
          return (
            <button
              className={`map-marker order-marker ${order.id === selectedOrderId ? "selected" : ""}`}
              key={order.id}
              style={{ left: `${origin.x}%`, top: `${origin.y}%` }}
              onClick={() => onSelectOrder(order.id)}
              aria-label={`Select order ${order.shortId}`}
              title={`Order ${order.shortId}`}
            >
              <Store size={15} aria-hidden="true" />
            </button>
          );
        })}
        {couriers.map((courier) => (
          <span
            className={`map-marker courier-marker courier-${courier.status}`}
            key={courier.id}
            style={{ left: `${courier.position.x}%`, top: `${courier.position.y}%` }}
            title={`${courier.name}, ${courier.status.replace("_", " ")}`}
          >
            <Truck size={14} aria-hidden="true" />
          </span>
        ))}
        <span
          className="map-marker destination-marker"
          style={{ left: "75%", top: "37%" }}
          title="Customer destination"
        >
          <UserRound size={14} aria-hidden="true" />
        </span>
        <div className="map-scale" aria-hidden="true">
          <span />
          <small>1 km</small>
        </div>
        {availability !== "ready" && (
          <div className="map-state" role="status">
            {availability === "loading"
              ? "Loading operational map projections"
              : availability === "degraded"
                ? "Map projection degraded"
                : "Map projection unavailable"}
          </div>
        )}
        {availability === "ready" &&
          orders.length > 0 &&
          orders.every((order) => !order.route[0]) && (
            <div className="map-state" role="status">
              Route geometry is unavailable from this source
            </div>
          )}
        <div className="map-legend" aria-label="Map legend">
          <span>
            <i className="legend-dot legend-order" /> orders
          </span>
          <span>
            <i className="legend-dot legend-courier" /> couriers
          </span>
          <span>
            <i className="legend-dot legend-route" /> active route
          </span>
        </div>
      </div>
      <div className="map-footer">
        <span>
          <Navigation size={14} aria-hidden="true" /> {selected?.shortId ?? "No order selected"}
        </span>
        <span>{selected?.destination ?? "Awaiting destination"}</span>
        <span className="map-capability">
          {mapCapabilities.mode === "provider" ? mapCapabilities.attribution : "Offline fallback"}
        </span>
      </div>
    </section>
  );
}

function sourceLabel(source: DataSourceMode): string {
  return source === "live" ? "Live" : source === "demo" ? "Demo" : "Replay";
}

function formatFreshness(value: string): string {
  if (!value) return "freshness pending";
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? value
    : `updated ${date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`;
}
