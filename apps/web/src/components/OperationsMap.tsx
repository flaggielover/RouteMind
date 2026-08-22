import { Navigation, Store, Truck, UserRound } from "lucide-react";
import type { Courier, Order } from "../domain/model";

interface OperationsMapProps {
  orders: readonly Order[];
  couriers: readonly Courier[];
  selectedOrderId: string;
  onSelectOrder: (orderId: string) => void;
}

export function OperationsMap({
  orders,
  couriers,
  selectedOrderId,
  onSelectOrder,
}: OperationsMapProps) {
  const selected = orders.find((order) => order.id === selectedOrderId) ?? orders[0];
  return (
    <section className="panel map-panel" aria-labelledby="map-title">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Live planning surface</p>
          <h2 id="map-title">City dispatch map</h2>
        </div>
        <span className="panel-meta">12:48 local</span>
      </div>
      <div
        className="map-canvas"
        aria-label="Schematic city dispatch map with live order and courier markers"
      >
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
        {orders.map((order) => (
          <button
            className={`map-marker order-marker ${order.id === selectedOrderId ? "selected" : ""}`}
            key={order.id}
            style={{ left: `${order.route[0].x}%`, top: `${order.route[0].y}%` }}
            onClick={() => onSelectOrder(order.id)}
            aria-label={`Select order ${order.shortId}`}
            title={`Order ${order.shortId}`}
          >
            <Store size={15} aria-hidden="true" />
          </button>
        ))}
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
      </div>
    </section>
  );
}
