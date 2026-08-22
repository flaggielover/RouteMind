import {
  AlertTriangle,
  ArrowUpRight,
  Bike,
  CheckCircle2,
  CircleDot,
  Clock3,
  Gauge,
  ListFilter,
  PackageCheck,
  RefreshCw,
  Route,
  ShieldCheck,
  Store,
  UserRound,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { BrowserRouter, Navigate, Route as RouterRoute, Routes } from "react-router-dom";
import { demoDataSource } from "./data/demoSnapshot";
import { probeServices } from "./data/health";
import { liveDataSource, replayDataSource } from "./data/liveSnapshot";
import { simulationDataSource } from "./data/simulation";
import {
  createCustomerOrder,
  createIdempotencyKey,
  recordCourierLocation,
  transitionCourierOrder,
  transitionCourierShift,
  transitionMerchantOrder,
  type CourierCommandResult,
  type CustomerOrderCommandResult,
} from "./data/orderCommands";
import {
  applyRealtimeItem,
  createRealtimeStream,
  type RealtimeConnectionState,
} from "./data/realtime";
import type {
  DataSourceMode,
  OperationsDataSource,
  ServiceHealth,
  SimulationCommand,
} from "./domain/model";
import { countOpenExceptions, findOrder, orderStatusLabel, statusTone } from "./domain/selectors";
import { AppShell } from "./components/AppShell";
import { LifecycleTimeline } from "./components/LifecycleTimeline";
import { MetricCell } from "./components/MetricCell";
import { OperationsMap } from "./components/OperationsMap";
import { ActivityStream } from "./components/ActivityStream";
import { SimulationControlPanel } from "./components/SimulationControlPanel";
import { StatusPill } from "./components/StatusPill";
import type { Order, OperationsSnapshot } from "./domain/model";
import "./styles.css";

interface AppProps {
  dataSource?: OperationsDataSource;
  healthProbe?: () => Promise<ServiceHealth[]>;
}

export default function App({ dataSource, healthProbe = probeServices }: AppProps) {
  const suppliedDataSource = dataSource;
  const [activeDataSource, setActiveDataSource] = useState<OperationsDataSource>(
    suppliedDataSource ?? liveDataSource,
  );
  const initialSnapshot = useMemo(() => activeDataSource.getSnapshot(), [activeDataSource]);
  const [snapshot, setSnapshot] = useState(initialSnapshot);
  const [health, setHealth] = useState<ServiceHealth[]>([...snapshot.health]);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [realtime, setRealtime] = useState<RealtimeConnectionState>({
    status: suppliedDataSource ? "disabled" : "connecting",
    cursor: "0",
    detail: suppliedDataSource
      ? "Realtime disabled for supplied data source"
      : "Connecting to live event stream",
    appliedEvents: 0,
    staleReason: null,
    recentEvents: [],
  });

  useEffect(() => {
    setSnapshot(initialSnapshot);
    if (!activeDataSource.loadSnapshot) return;
    let mounted = true;
    void activeDataSource.loadSnapshot().then((loaded) => {
      if (mounted) setSnapshot(loaded);
    });
    return () => {
      mounted = false;
    };
  }, [activeDataSource, initialSnapshot]);

  useEffect(() => {
    if (activeDataSource !== liveDataSource) {
      setRealtime({
        status: "disabled",
        cursor: "0",
        detail: "Realtime disabled for non-live data source",
        appliedEvents: 0,
        staleReason: null,
        recentEvents: [],
      });
      return;
    }
    if (typeof EventSource === "undefined") {
      setRealtime({
        status: "degraded",
        cursor: "0",
        detail: "Browser EventSource is unavailable",
        appliedEvents: 0,
        staleReason: "Browser EventSource is unavailable",
        recentEvents: [],
      });
      return;
    }
    const endpoint = `${import.meta.env.VITE_BUSINESS_API_URL ?? "http://localhost:18080"}/api/v1/events/stream`;
    const stream = createRealtimeStream({
      endpoint,
      onEvent: (item) => setSnapshot((current) => applyRealtimeItem(current, item)),
      onStateChange: setRealtime,
    });
    stream.start();
    return () => stream.stop();
  }, [activeDataSource]);

  const refreshHealth = useCallback(async () => {
    setIsRefreshing(true);
    try {
      setHealth(await healthProbe());
    } finally {
      setIsRefreshing(false);
    }
  }, [healthProbe]);

  const changeSource = useCallback(
    (mode: DataSourceMode) => {
      if (suppliedDataSource) return;
      setActiveDataSource(
        mode === "live"
          ? liveDataSource
          : mode === "demo"
            ? demoDataSource
            : mode === "replay"
              ? replayDataSource
              : simulationDataSource,
      );
    },
    [suppliedDataSource],
  );

  const controlSimulation = useCallback(
    async (command: SimulationCommand) => {
      if (!activeDataSource.controlSimulation) return;
      setSnapshot(await activeDataSource.controlSimulation(command));
    },
    [activeDataSource],
  );

  useEffect(() => {
    void refreshHealth();
  }, [refreshHealth]);

  return (
    <BrowserRouter>
      <AppShell
        health={health}
        source={snapshot.source}
        availability={snapshot.availability}
        sourceDetail={snapshot.sourceDetail}
        realtime={realtime}
        onSourceChange={changeSource}
        onRefreshHealth={() => void refreshHealth()}
      >
        <AppRoutes
          snapshot={snapshot}
          realtime={realtime}
          health={health}
          onSimulationControl={controlSimulation}
        />
      </AppShell>
      {isRefreshing && (
        <span className="sr-only" role="status">
          Refreshing service health
        </span>
      )}
    </BrowserRouter>
  );
}

export function AppRoutes({
  snapshot,
  realtime,
  health,
  onSimulationControl,
}: {
  snapshot: OperationsSnapshot;
  realtime: RealtimeConnectionState;
  health: readonly ServiceHealth[];
  onSimulationControl?: (command: SimulationCommand) => Promise<void>;
}) {
  return (
    <Routes>
      <RouterRoute
        path="/operations"
        element={
          <OperationsView
            snapshot={snapshot}
            realtime={realtime}
            health={health}
            onSimulationControl={onSimulationControl}
          />
        }
      />
      <RouterRoute path="/strategy" element={<StrategyView snapshot={snapshot} />} />
      <RouterRoute
        path="/customer"
        element={<CustomerView snapshot={snapshot} realtime={realtime} />}
      />
      <RouterRoute path="/merchant" element={<MerchantView snapshot={snapshot} />} />
      <RouterRoute path="/courier" element={<CourierView snapshot={snapshot} />} />
      <RouterRoute path="*" element={<Navigate to="/operations" replace />} />
    </Routes>
  );
}

function OperationsView({
  snapshot,
  realtime,
  health,
  onSimulationControl,
}: {
  snapshot: OperationsSnapshot;
  realtime: RealtimeConnectionState;
  health: readonly ServiceHealth[];
  onSimulationControl?: (command: SimulationCommand) => Promise<void>;
}) {
  const [selectedOrderId, setSelectedOrderId] = useState(snapshot.orders[0]?.id ?? "");
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [zoneFilter, setZoneFilter] = useState("all");
  const [lifecycleFilter, setLifecycleFilter] = useState("all");
  const [exceptionsOnly, setExceptionsOnly] = useState(false);
  const [freshOnly, setFreshOnly] = useState(false);
  const selectedOrder = snapshot.orders.length ? findOrder(snapshot, selectedOrderId) : undefined;
  const filteredOrders = snapshot.orders.filter((order) => {
    const courier = snapshot.couriers.find(
      (candidate) => candidate.id === snapshot.dispatch.selectedCourier,
    );
    const zoneMatches = zoneFilter === "all" || courier?.zone === zoneFilter;
    const lifecycleMatches = lifecycleFilter === "all" || order.status === lifecycleFilter;
    const exceptionMatches =
      !exceptionsOnly || (order.priority === "priority" && order.status !== "DELIVERED");
    const freshnessMatches = !freshOnly || Boolean(snapshot.generatedAt);
    return zoneMatches && lifecycleMatches && exceptionMatches && freshnessMatches;
  });
  const filteredCouriers = snapshot.couriers.filter(
    (courier) => zoneFilter === "all" || courier.zone === zoneFilter,
  );
  const exceptionOrders = snapshot.orders.filter(
    (order) => order.priority === "priority" && order.status !== "DELIVERED",
  );
  const availableCouriers = snapshot.couriers.filter(
    (courier) => courier.status === "available",
  ).length;
  const supplyGap = snapshot.orders.length - availableCouriers;
  const zones = new Set(snapshot.couriers.map((courier) => courier.zone).filter(Boolean)).size;
  const openExceptions = countOpenExceptions(snapshot);
  const hasDispatchLatency = snapshot.availability === "ready" && snapshot.dispatch.latencyMs > 0;
  return (
    <div className="page-stack">
      <section className="page-intro">
        <div>
          <p className="eyebrow">Operations / live board</p>
          <h2>Keep the city moving.</h2>
          <p className="lede">
            A single view of demand, supply, and the decisions connecting them.
          </p>
        </div>
        <div className="intro-actions">
          <span className="last-updated">
            <CircleDot size={13} /> Snapshot {formatFreshness(snapshot.generatedAt)}
          </span>
          <button
            className="button button-primary"
            type="button"
            aria-expanded={filtersOpen}
            onClick={() => setFiltersOpen((open) => !open)}
          >
            <ListFilter size={15} /> Filter board
          </button>
        </div>
      </section>
      {filtersOpen && (
        <section className="operations-filters" aria-label="Operations filters">
          <label>
            Zone
            <select value={zoneFilter} onChange={(event) => setZoneFilter(event.target.value)}>
              <option value="all">All zones</option>
              {[...new Set(snapshot.couriers.map((courier) => courier.zone))].map((zone) => (
                <option key={zone} value={zone}>
                  {zone}
                </option>
              ))}
            </select>
          </label>
          <label>
            Lifecycle
            <select
              value={lifecycleFilter}
              onChange={(event) => setLifecycleFilter(event.target.value)}
            >
              <option value="all">All lifecycle states</option>
              {Object.entries(orderStatusLabel).map(([status, label]) => (
                <option key={status} value={status}>
                  {label}
                </option>
              ))}
            </select>
          </label>
          <label className="filter-check">
            <input
              type="checkbox"
              checked={exceptionsOnly}
              onChange={(event) => setExceptionsOnly(event.target.checked)}
            />
            Exceptions only
          </label>
          <label className="filter-check">
            <input
              type="checkbox"
              checked={freshOnly}
              onChange={(event) => setFreshOnly(event.target.checked)}
            />
            Has freshness
          </label>
          <span className="filter-result">
            Showing {filteredOrders.length} of {snapshot.orders.length}
          </span>
        </section>
      )}
      {snapshot.availability !== "ready" && (
        <section className={`projection-state projection-${snapshot.availability}`} role="status">
          <strong>
            {snapshot.availability === "loading"
              ? "Loading operational projections"
              : snapshot.availability === "degraded"
                ? "Operational projections degraded"
                : "Operational projections unavailable"}
          </strong>
          <span>{snapshot.sourceDetail}</span>
        </section>
      )}
      {snapshot.source === "simulation" && snapshot.simulation && onSimulationControl && (
        <SimulationControlPanel
          snapshot={snapshot.simulation}
          demandCount={snapshot.orders.length}
          supplyCount={snapshot.couriers.length}
          trafficLabel="seeded 1.0x"
          onControl={onSimulationControl}
        />
      )}
      <section className="operations-health" aria-label="Operations projection health">
        <div>
          <p className="eyebrow">Projection health</p>
          <strong>{health.length ? "Service checks" : "Checking service health"}</strong>
        </div>
        <div className="operations-health-items">
          {(health.length
            ? health
            : [{ service: "business-api", label: "Business API", status: "checking" as const }]
          ).map((item) => (
            <StatusPill key={item.service} status={item.status} label={item.label} />
          ))}
          <span className="health-freshness">
            {snapshot.generatedAt
              ? `Snapshot ${formatFreshness(snapshot.generatedAt)}`
              : "Snapshot freshness pending"}
          </span>
        </div>
      </section>
      <section className="metric-grid" aria-label="Operational metrics">
        <MetricCell
          label="Active orders"
          value={`${snapshot.orders.length}`}
          detail={openExceptions ? `${openExceptions} need attention` : "No recorded exceptions"}
          icon={PackageCheck}
          tone="accent"
        />
        <MetricCell
          label="Available couriers"
          value={`${availableCouriers}`}
          detail={zones ? `Across ${zones} zone${zones === 1 ? "" : "s"}` : "Zone data pending"}
          icon={Bike}
          tone="success"
        />
        <MetricCell
          label="Assignment latency"
          value={hasDispatchLatency ? `${snapshot.dispatch.latencyMs} ms` : "-"}
          detail={hasDispatchLatency ? "Last decision" : "Decision latency unavailable"}
          icon={Gauge}
        />
        <MetricCell
          label="Exceptions"
          value={`${openExceptions}`}
          detail="Priority queue"
          icon={AlertTriangle}
          tone="warning"
        />
      </section>
      {openExceptions > 0 && (
        <div className="exception-banner" role="alert">
          <AlertTriangle size={16} aria-hidden="true" />
          <strong>{openExceptions} priority exception needs attention</strong>
          <span>Review the selected order before assigning another route.</span>
        </div>
      )}
      <section className="operations-alerts" aria-label="Operations alerts and imbalance">
        <section className="panel alert-panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Exception queue</p>
              <h2>
                {exceptionOrders.length} recorded alert{exceptionOrders.length === 1 ? "" : "s"}
              </h2>
            </div>
            <AlertTriangle size={17} className="heading-icon" />
          </div>
          {exceptionOrders.length ? (
            <div className="alert-list">
              {exceptionOrders.map((order) => (
                <button
                  key={order.id}
                  className="alert-item"
                  type="button"
                  onClick={() => setSelectedOrderId(order.id)}
                >
                  <span>
                    <strong>{order.shortId}</strong>
                    <small>{order.destination}</small>
                  </span>
                  <span className="alert-link">
                    Inspect <ArrowUpRight size={13} />
                  </span>
                </button>
              ))}
            </div>
          ) : (
            <p className="empty-state">No recorded exceptions in this snapshot.</p>
          )}
        </section>
        <section className="panel alert-panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Supply / demand</p>
              <h2>{supplyGap > 0 ? `${supplyGap} order gap` : "Covered"}</h2>
            </div>
            <Gauge size={17} className="heading-icon" />
          </div>
          <dl className="detail-list">
            <div>
              <dt>Orders in snapshot</dt>
              <dd>{snapshot.orders.length}</dd>
            </div>
            <div>
              <dt>Available couriers</dt>
              <dd>{availableCouriers}</dd>
            </div>
            <div>
              <dt>Overtime risk</dt>
              <dd className="muted-label">Unavailable from source</dd>
            </div>
          </dl>
        </section>
      </section>
      <section className="primary-grid">
        <OperationsMap
          orders={filteredOrders}
          couriers={filteredCouriers}
          selectedOrderId={selectedOrderId}
          onSelectOrder={setSelectedOrderId}
          availability={snapshot.availability}
          source={snapshot.source}
          generatedAt={snapshot.generatedAt}
        />
        <OrderQueue
          orders={filteredOrders}
          selectedOrderId={selectedOrderId}
          onSelectOrder={setSelectedOrderId}
          availability={snapshot.availability}
        />
      </section>
      <section className="secondary-grid">
        <section className="panel lifecycle-panel" aria-labelledby="lifecycle-title">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Selected order</p>
              <h2 id="lifecycle-title">{selectedOrder?.shortId ?? "No order"} lifecycle</h2>
              <span className="entity-freshness">
                {snapshot.source} source ·{" "}
                {snapshot.generatedAt ? formatFreshness(snapshot.generatedAt) : "freshness pending"}
              </span>
            </div>
            {selectedOrder ? (
              <StatusPill
                status={statusTone(selectedOrder.status) === "success" ? "healthy" : "checking"}
                label={orderStatusLabel[selectedOrder.status]}
              />
            ) : (
              <StatusPill status="checking" label="No live orders" />
            )}
          </div>
          {selectedOrder ? (
            <LifecycleTimeline order={selectedOrder} />
          ) : (
            <p className="empty-state">No orders are present in the selected source.</p>
          )}
        </section>
        <section className="panel activity-panel" aria-labelledby="activity-title">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Decision trace</p>
              <h2 id="activity-title">Dispatch activity</h2>
            </div>
            <Route size={17} className="heading-icon" />
          </div>
          <div className="decision-callout">
            <div className="decision-icon">
              <Route size={17} />
            </div>
            <div>
              <strong>
                {snapshot.dispatch.strategy} <span>v{snapshot.dispatch.version}</span>
              </strong>
              <p>{snapshot.dispatch.rationale}</p>
            </div>
          </div>
          <dl className="detail-list">
            <div>
              <dt>Selected courier</dt>
              <dd>{snapshot.dispatch.selectedCourier}</dd>
            </div>
            <div>
              <dt>Decision latency</dt>
              <dd>{snapshot.dispatch.latencyMs} ms</dd>
            </div>
            <div>
              <dt>Trace</dt>
              <dd>dispatch-4d19</dd>
            </div>
          </dl>
          <ActivityStream snapshot={snapshot} realtime={realtime} />
          <button className="text-button" type="button">
            Open decision details <ArrowUpRight size={14} />
          </button>
        </section>
      </section>
      <section className="entity-drawers" aria-label="Selected entity details">
        <section className="panel entity-drawer">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Order detail</p>
              <h2>{selectedOrder?.shortId ?? "No order selected"}</h2>
            </div>
            <PackageCheck size={17} className="heading-icon" />
          </div>
          {selectedOrder ? (
            <dl className="detail-list">
              <div>
                <dt>Route points</dt>
                <dd>{selectedOrder.route.length || "Unavailable"}</dd>
              </div>
              <div>
                <dt>Order version</dt>
                <dd>{selectedOrder.version ?? "Not supplied"}</dd>
              </div>
              <div>
                <dt>Source</dt>
                <dd>
                  {snapshot.source} · {formatFreshness(snapshot.generatedAt)}
                </dd>
              </div>
            </dl>
          ) : (
            <p className="empty-state">Select an order to inspect its state.</p>
          )}
        </section>
        <section className="panel entity-drawer">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Courier detail</p>
              <h2>{snapshot.dispatch.selectedCourier}</h2>
            </div>
            <Bike size={17} className="heading-icon" />
          </div>
          {snapshot.couriers.find((courier) => courier.id === snapshot.dispatch.selectedCourier) ? (
            <dl className="detail-list">
              {(() => {
                const courier = snapshot.couriers.find(
                  (item) => item.id === snapshot.dispatch.selectedCourier,
                )!;
                return (
                  <>
                    <div>
                      <dt>Zone</dt>
                      <dd>{courier.zone}</dd>
                    </div>
                    <div>
                      <dt>Status</dt>
                      <dd>{courier.status.replace("_", " ")}</dd>
                    </div>
                    <div>
                      <dt>Position</dt>
                      <dd>
                        {courier.position.x}, {courier.position.y}
                      </dd>
                    </div>
                  </>
                );
              })()}
            </dl>
          ) : (
            <p className="empty-state">Courier detail unavailable from this source.</p>
          )}
        </section>
      </section>
    </div>
  );
}

function OrderQueue({
  orders,
  selectedOrderId,
  onSelectOrder,
  availability,
}: {
  orders: readonly Order[];
  selectedOrderId: string;
  onSelectOrder: (id: string) => void;
  availability: OperationsSnapshot["availability"];
}) {
  return (
    <section className="panel queue-panel" aria-labelledby="queue-title">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Demand queue</p>
          <h2 id="queue-title">Orders in motion</h2>
        </div>
        <span className="count-badge">{orders.length}</span>
      </div>
      <div className="queue-list">
        {orders.length === 0 ? (
          <p className="empty-state queue-empty">
            {availability === "loading"
              ? "Loading live orders"
              : availability === "unavailable"
                ? "Orders are unavailable from this source"
                : "No orders are present in the selected source"}
          </p>
        ) : (
          orders.map((order) => (
            <button
              className={`queue-item ${order.id === selectedOrderId ? "selected" : ""}`}
              key={order.id}
              onClick={() => onSelectOrder(order.id)}
              type="button"
            >
              <span
                className={`queue-status status-tone-${statusTone(order.status)}`}
                aria-hidden="true"
              />
              <span className="queue-copy">
                <strong>
                  {order.shortId} <span>{order.customerName}</span>
                </strong>
                <small>
                  {order.merchantName} · {order.destination}
                </small>
              </span>
              <span className="queue-side">
                <strong>{order.eta}</strong>
                <small>{orderStatusLabel[order.status]}</small>
              </span>
            </button>
          ))
        )}
      </div>
      <button className="text-button" type="button">
        View all orders <ArrowUpRight size={14} />
      </button>
    </section>
  );
}

function RolePage({
  eyebrow,
  title,
  lede,
  children,
  icon: Icon,
}: {
  eyebrow: string;
  title: string;
  lede: string;
  children: React.ReactNode;
  icon: typeof Route;
}) {
  return (
    <div className="page-stack">
      <section className="page-intro role-intro">
        <div>
          <p className="eyebrow">{eyebrow}</p>
          <h2>{title}</h2>
          <p className="lede">{lede}</p>
        </div>
        <div className="role-intro-icon" aria-hidden="true">
          <Icon size={25} />
        </div>
      </section>
      {children}
    </div>
  );
}

function StrategyView({ snapshot }: { snapshot: OperationsSnapshot }) {
  return (
    <RolePage
      eyebrow="Strategy lab / control"
      title="Decisions you can inspect."
      lede="Compare registered strategies against the same operational snapshot."
      icon={Gauge}
    >
      <section className="content-grid-two">
        <section className="panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Active policy</p>
              <h2>{snapshot.dispatch.strategy}</h2>
            </div>
            <StatusPill status="healthy" label="Registered" />
          </div>
          <div className="strategy-score">
            <span>Assignment quality</span>
            <strong>92.4</strong>
            <small>+4.8 vs nearest baseline</small>
          </div>
          <dl className="detail-list">
            <div>
              <dt>Version</dt>
              <dd>{snapshot.dispatch.version}</dd>
            </div>
            <div>
              <dt>Last decision</dt>
              <dd>{snapshot.dispatch.latencyMs} ms</dd>
            </div>
            <div>
              <dt>Shadow mode</dt>
              <dd>Ready</dd>
            </div>
          </dl>
        </section>
        <section className="panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Baseline comparison</p>
              <h2>Registered strategies</h2>
            </div>
            <ShieldCheck size={17} className="heading-icon" />
          </div>
          <div className="strategy-row active">
            <span>
              <strong>weighted-greedy</strong>
              <small>v1.0.0 · active</small>
            </span>
            <b>92.4</b>
            <StatusPill status="healthy" label="Live" />
          </div>
          <div className="strategy-row">
            <span>
              <strong>nearest</strong>
              <small>v1.0.0 · baseline</small>
            </span>
            <b>87.6</b>
            <span className="muted-label">Reference</span>
          </div>
          <button className="text-button" type="button">
            Open strategy registry <ArrowUpRight size={14} />
          </button>
        </section>
      </section>
    </RolePage>
  );
}

type CustomerCommandState =
  { kind: "pending"; idempotencyKey: string } | CustomerOrderCommandResult | null;

type CourierCommandState =
  { kind: "pending"; idempotencyKey: string } | CourierCommandResult | null;

function CustomerView({
  snapshot,
  realtime,
}: {
  snapshot: OperationsSnapshot;
  realtime: RealtimeConnectionState;
}) {
  const order = snapshot.orders[0];
  const [command, setCommand] = useState<CustomerCommandState>(null);
  const [idempotencyKey, setIdempotencyKey] = useState(createIdempotencyKey);
  const commandAvailable = snapshot.source === "live" && snapshot.availability === "ready";
  const trackingStatus =
    realtime.status === "connected"
      ? "healthy"
      : realtime.status === "disabled"
        ? "checking"
        : "unavailable";
  const trackingLabel =
    realtime.status === "connected"
      ? "Live tracking"
      : realtime.status === "disabled"
        ? "Tracking paused"
        : "Tracking degraded";

  const submitOrder = async () => {
    if (!commandAvailable || command?.kind === "pending") return;
    setCommand({ kind: "pending", idempotencyKey });
    const result = await createCustomerOrder({ idempotencyKey });
    setCommand(result);
    if (result.kind === "success") setIdempotencyKey(createIdempotencyKey());
  };

  return (
    <RolePage
      eyebrow="Customer / order tracking"
      title="Your delivery, clearly explained."
      lede="The same lifecycle state, translated into a calm customer view."
      icon={UserRound}
    >
      <section className="content-grid-two">
        <section className="panel customer-order">
          {!order ? (
            <p className="empty-state">No order is available in the selected source.</p>
          ) : (
            <>
              <div className="panel-heading">
                <div>
                  <p className="eyebrow">Order {order.shortId}</p>
                  <h2>{order.merchantName}</h2>
                </div>
                <StatusPill
                  status={
                    order.status === "DELIVERED"
                      ? "healthy"
                      : order.status === "OUT_FOR_DELIVERY"
                        ? "busy"
                        : "checking"
                  }
                  label={orderStatusLabel[order.status]}
                />
              </div>
              <div className="customer-destination">
                <MapPinIcon />
                <div>
                  <span>Delivered to</span>
                  <strong>{order.destination}</strong>
                </div>
              </div>
              <LifecycleTimeline order={order} />
              <div className="customer-tracking-meta">
                <StatusPill status={trackingStatus} label={trackingLabel} />
                <span>
                  Version {order.version ?? "unknown"} · {snapshot.sourceDetail}
                </span>
              </div>
            </>
          )}
        </section>
        <section className="panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Courier</p>
              <h2>Ari Singh</h2>
            </div>
            <Bike size={18} className="heading-icon" />
          </div>
          <div className="courier-card">
            <div className="avatar">AS</div>
            <div>
              <strong>Delivery complete</strong>
              <p>Thanks for using RouteMind.</p>
            </div>
          </div>
          <div className="customer-command" aria-label="Create customer order">
            <div className="panel-heading">
              <div>
                <p className="eyebrow">Java command</p>
                <h2>Start a new order</h2>
              </div>
              <RefreshCw size={18} className="heading-icon" />
            </div>
            <p className="panel-copy">
              Creates durable order state through the customer command boundary. The same
              idempotency key is kept for a retry.
            </p>
            <button
              className="button button-primary"
              type="button"
              disabled={!commandAvailable || command?.kind === "pending"}
              onClick={() => void submitOrder()}
            >
              <RefreshCw size={15} className={command?.kind === "pending" ? "spin" : undefined} />
              {command?.kind === "pending" ? "Submitting..." : "Create order"}
            </button>
            {!commandAvailable && (
              <p className="command-note" role="status">
                {snapshot.source === "live"
                  ? snapshot.availability === "degraded"
                    ? "Live data is degraded; commands are temporarily unavailable."
                    : "Waiting for the live Java snapshot."
                  : "Writing is disabled for demo and replay sources."}
              </p>
            )}
            {command?.kind === "success" && (
              <div className="command-result" role="status">
                <strong>
                  {command.replayed ? "Idempotent replay acknowledged" : "Order created"}
                </strong>
                <span>
                  {command.orderId} · {command.status} · version {command.version}
                </span>
                <small>
                  Trace {command.traceId ?? "not returned"} · key {command.idempotencyKey}
                </small>
              </div>
            )}
            {command?.kind === "error" && (
              <div className="command-result command-error" role="alert">
                <strong>Command not accepted: {command.code}</strong>
                <span>
                  {command.failureState === "unavailable" || command.failureState === "timeout"
                    ? "The same idempotency key can be retried."
                    : command.failureState === "conflict"
                      ? "Refresh the order before retrying this stale command."
                      : "Resolve the validation before retrying."}
                </span>
                <small>
                  Trace {command.traceId ?? "not returned"} · key {command.idempotencyKey}
                </small>
              </div>
            )}
          </div>
        </section>
      </section>
    </RolePage>
  );
}

function MerchantView({ snapshot }: { snapshot: OperationsSnapshot }) {
  const [command, setCommand] = useState<CustomerCommandState>(null);
  const order =
    snapshot.orders.find((candidate) =>
      ["CREATED", "CONFIRMED", "PREPARING"].includes(candidate.status),
    ) ?? snapshot.orders[0];
  const nextCommand = order
    ? order.status === "CREATED"
      ? { target: "CONFIRMED" as const, label: "Accept order" }
      : order.status === "CONFIRMED"
        ? { target: "PREPARING" as const, label: "Start preparation" }
        : order.status === "PREPARING"
          ? { target: "READY_FOR_PICKUP" as const, label: "Mark ready" }
          : null
    : null;
  const commandAvailable = snapshot.source === "live" && snapshot.availability === "ready";
  const ordersInPrep = snapshot.orders.filter(
    (candidate) => candidate.status === "PREPARING",
  ).length;
  const handoffsNext = snapshot.orders.filter(
    (candidate) => candidate.status === "READY_FOR_PICKUP",
  ).length;
  const prepMinutes = snapshot.merchants[0]?.prepMinutes ?? 0;
  const readyEvent = order?.events.find((event) => event.status === "READY_FOR_PICKUP");
  const submitTransition = async () => {
    if (!order || !nextCommand || !commandAvailable || command?.kind === "pending") return;
    const idempotencyKey = `merchant-${nextCommand.target.toLowerCase()}-${order.id}-${order.version ?? 0}`;
    setCommand({ kind: "pending", idempotencyKey });
    const result = await transitionMerchantOrder({
      orderId: order.id,
      target: nextCommand.target,
      expectedVersion: order.version ?? 0,
      idempotencyKey,
    });
    setCommand(result);
  };
  return (
    <RolePage
      eyebrow="Merchant / kitchen queue"
      title="Prep with the handoff in view."
      lede="See preparation load and courier handoffs without leaving the order context."
      icon={Store}
    >
      <section className="content-grid-two">
        <section className="panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Kitchen queue</p>
              <h2>Today at a glance</h2>
            </div>
            <StatusPill status="busy" label="Busy" />
          </div>
          <div className="merchant-stats">
            <div>
              <strong>{ordersInPrep}</strong>
              <span>orders in prep</span>
            </div>
            <div>
              <strong>{prepMinutes > 0 ? `${prepMinutes}m` : "Unavailable"}</strong>
              <span>avg prep time</span>
            </div>
            <div>
              <strong>{handoffsNext}</strong>
              <span>handoffs next</span>
            </div>
          </div>
          {snapshot.merchants.map((merchant) => (
            <div className="merchant-row" key={merchant.id}>
              <span>
                <strong>{merchant.name}</strong>
                <small>
                  {merchant.queue} orders queued · {merchant.prepMinutes}m prep
                </small>
              </span>
              <StatusPill status={merchant.status} />
            </div>
          ))}
        </section>
        <section className="panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Next handoff</p>
              <h2>RM-2043</h2>
            </div>
            <PackageCheck size={18} className="heading-icon" />
          </div>
          <div className="handoff-state">
            <div className="handoff-icon">
              <Clock3 size={19} />
            </div>
            <div>
              <strong>{order ? orderStatusLabel[order.status] : "No order available"}</strong>
              <p>
                {order
                  ? `${order.merchantName} · ${order.shortId} · version ${order.version ?? "unknown"}`
                  : "Select a live order to operate"}
              </p>
            </div>
          </div>
          <div className="readiness-details" aria-label="Readiness timing">
            <span>
              Expected ready <strong>{order?.eta ?? "Unavailable"}</strong>
            </span>
            <span>
              Actual ready <strong>{readyEvent?.at ?? "Not recorded"}</strong>
            </span>
          </div>
          {nextCommand && (
            <button
              className="button button-primary"
              type="button"
              disabled={!commandAvailable || command?.kind === "pending"}
              onClick={() => void submitTransition()}
            >
              <CheckCircle2
                size={15}
                className={command?.kind === "pending" ? "spin" : undefined}
              />
              {command?.kind === "pending" ? "Submitting..." : nextCommand.label}
            </button>
          )}
          {!commandAvailable && (
            <p className="command-note" role="status">
              {snapshot.source === "live"
                ? snapshot.availability === "degraded"
                  ? "Live data is degraded; commands are temporarily unavailable."
                  : "Waiting for the live Java snapshot."
                : "Writing is disabled for demo and replay sources."}
            </p>
          )}
          {command?.kind === "success" && (
            <div className="command-result" role="status">
              <strong>
                {command.replayed ? "Idempotent replay acknowledged" : "Merchant command accepted"}
              </strong>
              <span>
                {command.orderId} · {command.status} · version {command.version}
              </span>
              <small>
                Trace {command.traceId ?? "not returned"} · key {command.idempotencyKey}
              </small>
            </div>
          )}
          {command?.kind === "error" && (
            <div className="command-result command-error" role="alert">
              <strong>Command not accepted: {command.code}</strong>
              <span>
                {command.failureState === "unavailable" || command.failureState === "timeout"
                  ? "The same idempotency key can be retried."
                  : command.failureState === "conflict"
                    ? "Refresh the order before retrying this stale command."
                    : "Resolve the validation before retrying."}
              </span>
              <small>
                Trace {command.traceId ?? "not returned"} · key {command.idempotencyKey}
              </small>
            </div>
          )}
        </section>
      </section>
    </RolePage>
  );
}

function CourierView({ snapshot }: { snapshot: OperationsSnapshot }) {
  const courier = snapshot.couriers[0];
  const [command, setCommand] = useState<CustomerCommandState>(null);
  const [shiftCommand, setShiftCommand] = useState<CourierCommandState>(null);
  const [locationCommand, setLocationCommand] = useState<CourierCommandState>(null);
  const [localShift, setLocalShift] = useState<"ONLINE" | "OFFLINE" | null>(null);
  const [shiftVersion, setShiftVersion] = useState(0);
  const order =
    snapshot.orders.find((candidate) =>
      ["ASSIGNED", "ACCEPTED", "ARRIVED", "PICKED_UP", "OUT_FOR_DELIVERY"].includes(
        candidate.status,
      ),
    ) ?? snapshot.orders.find((candidate) => candidate.status !== "DELIVERED");
  const nextCommand = order
    ? order.status === "ASSIGNED"
      ? { target: "ACCEPTED" as const, label: "Accept task" }
      : order.status === "ACCEPTED"
        ? { target: "ARRIVED" as const, label: "Arrive merchant" }
        : order.status === "ARRIVED"
          ? { target: "PICKED_UP" as const, label: "Confirm pickup" }
          : order.status === "PICKED_UP" || order.status === "OUT_FOR_DELIVERY"
            ? { target: "DELIVERED" as const, label: "Complete delivery" }
            : null
    : null;
  const commandAvailable =
    snapshot.source === "live" && snapshot.availability === "ready" && Boolean(courier);
  const online = localShift ?? (courier?.status === "offline" ? "OFFLINE" : "ONLINE");
  const submitOrderTransition = async () => {
    if (!courier || !order || !nextCommand || !commandAvailable || command?.kind === "pending")
      return;
    const expectedVersion = order.version;
    if (expectedVersion === undefined) {
      setCommand({
        kind: "error",
        failureState: "validation",
        code: "version_unavailable",
        status: 0,
        traceId: null,
        retryable: false,
        idempotencyKey: `courier-${nextCommand.target.toLowerCase()}-${order.id}-unknown`,
      });
      return;
    }
    const idempotencyKey = `courier-${nextCommand.target.toLowerCase()}-${order.id}-${expectedVersion}`;
    setCommand({ kind: "pending", idempotencyKey });
    setCommand(
      await transitionCourierOrder({
        orderId: order.id,
        target: nextCommand.target,
        expectedVersion,
        idempotencyKey,
      }),
    );
  };
  const submitShift = async (target: "ONLINE" | "OFFLINE") => {
    if (!courier || !commandAvailable || shiftCommand?.kind === "pending") return;
    const idempotencyKey = `courier-shift-${target.toLowerCase()}-${courier.id}-${shiftVersion}`;
    setShiftCommand({ kind: "pending", idempotencyKey });
    const result = await transitionCourierShift({
      courierId: courier.id,
      target,
      expectedVersion: shiftVersion,
      idempotencyKey,
    });
    setShiftCommand(result);
    if (result.kind === "success") {
      setLocalShift(target);
      setShiftVersion(result.version);
    }
  };
  const submitLocation = async () => {
    if (!courier || !commandAvailable || locationCommand?.kind === "pending") return;
    const observedAt = new Date().toISOString();
    const idempotencyKey = `courier-location-${courier.id}-${observedAt}`;
    setLocationCommand({ kind: "pending", idempotencyKey });
    setLocationCommand(
      await recordCourierLocation({
        courierId: courier.id,
        latitude: courier.position.y,
        longitude: courier.position.x,
        observedAt,
        idempotencyKey,
      }),
    );
  };
  return (
    <RolePage
      eyebrow="Courier / active route"
      title="A focused shift, one next action."
      lede="A courier view keeps the next handoff and route state legible at a glance."
      icon={Bike}
    >
      <section className="content-grid-two">
        <section className="panel">
          {!courier ? (
            <p className="empty-state">No courier is available in the selected source.</p>
          ) : (
            <>
              <div className="panel-heading">
                <div>
                  <p className="eyebrow">Shift status</p>
                  <h2>{courier.name}</h2>
                </div>
                <StatusPill
                  status={online === "ONLINE" ? "available" : "offline"}
                  label={online === "ONLINE" ? "Online" : "Offline"}
                />
              </div>
              <div className="shift-summary">
                <div className="avatar courier-avatar">
                  {courier.name.slice(0, 2).toUpperCase()}
                </div>
                <div>
                  <strong>{courier.zone}</strong>
                  <p>
                    {order
                      ? `${order.shortId} · ${orderStatusLabel[order.status]}`
                      : "No assigned task"}
                  </p>
                </div>
              </div>
              <div className="courier-metrics">
                <div>
                  <span>Shift</span>
                  <strong>{snapshot.source === "live" ? "Live" : "Fixture"}</strong>
                </div>
                <div>
                  <span>Distance</span>
                  <strong>{snapshot.source === "live" ? "Projection" : "Fixture"}</strong>
                </div>
                <div>
                  <span>Location</span>
                  <strong>{snapshot.availability === "ready" ? "Fresh" : "Degraded"}</strong>
                </div>
              </div>
              <div className="courier-actions">
                <button
                  className="button button-secondary"
                  type="button"
                  disabled={
                    !commandAvailable || shiftCommand?.kind === "pending" || online === "ONLINE"
                  }
                  onClick={() => void submitShift("ONLINE")}
                >
                  <Bike size={15} /> Go online
                </button>
                <button
                  className="button button-secondary"
                  type="button"
                  disabled={
                    !commandAvailable || shiftCommand?.kind === "pending" || online === "OFFLINE"
                  }
                  onClick={() => void submitShift("OFFLINE")}
                >
                  <CircleDot size={15} /> Go offline
                </button>
                <button
                  className="button button-secondary"
                  type="button"
                  disabled={!commandAvailable || locationCommand?.kind === "pending"}
                  onClick={() => void submitLocation()}
                >
                  <NavigationIcon /> Send location
                </button>
              </div>
            </>
          )}
          {!commandAvailable && (
            <p className="command-note" role="status">
              {snapshot.source === "live"
                ? snapshot.availability === "degraded"
                  ? "Live data is degraded; commands are temporarily unavailable."
                  : "Waiting for the live Java snapshot."
                : "Writing is disabled for demo and replay sources."}
            </p>
          )}
          {shiftCommand?.kind === "error" && (
            <div className="command-result command-error" role="alert">
              <strong>Shift command not accepted: {shiftCommand.code}</strong>
              <small>
                Trace {shiftCommand.traceId ?? "not returned"} · key {shiftCommand.idempotencyKey}
              </small>
            </div>
          )}
          {locationCommand?.kind === "success" && (
            <div className="command-result" role="status">
              <strong>Location recorded: {locationCommand.status}</strong>
              <small>
                Trace {locationCommand.traceId ?? "not returned"} · key{" "}
                {locationCommand.idempotencyKey}
              </small>
            </div>
          )}
        </section>
        <section className="panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Next stop</p>
              <h2>{order?.shortId ?? "No active route"}</h2>
            </div>
            <Route size={18} className="heading-icon" />
          </div>
          {!order ? (
            <p className="empty-state">No active route is available in the selected source.</p>
          ) : (
            <div className="next-stop">
              <div className="stop-icon">
                <NavigationIcon />
              </div>
              <div>
                <strong>{order.destination}</strong>
                <p>
                  {order.customerName} · ETA {order.eta}
                </p>
              </div>
            </div>
          )}
          {nextCommand && (
            <button
              className="button button-primary"
              type="button"
              disabled={!commandAvailable || command?.kind === "pending"}
              onClick={() => void submitOrderTransition()}
            >
              <CheckCircle2
                size={15}
                className={command?.kind === "pending" ? "spin" : undefined}
              />
              {command?.kind === "pending" ? "Submitting..." : nextCommand.label}
            </button>
          )}
          {command?.kind === "success" && (
            <div className="command-result" role="status">
              <strong>
                {command.replayed ? "Idempotent replay acknowledged" : "Courier command accepted"}
              </strong>
              <span>
                {command.orderId} · {command.status} · version {command.version}
              </span>
              <small>
                Trace {command.traceId ?? "not returned"} · key {command.idempotencyKey}
              </small>
            </div>
          )}
          {command?.kind === "error" && (
            <div className="command-result command-error" role="alert">
              <strong>Command not accepted: {command.code}</strong>
              <small>
                Trace {command.traceId ?? "not returned"} · key {command.idempotencyKey}
              </small>
            </div>
          )}
        </section>
      </section>
    </RolePage>
  );
}

function MapPinIcon() {
  return (
    <span className="inline-icon">
      <UserRound size={16} />
    </span>
  );
}
function NavigationIcon() {
  return (
    <span className="inline-icon">
      <ArrowUpRight size={16} />
    </span>
  );
}

function formatFreshness(value: string): string {
  if (!value) return "freshness pending";
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? value
    : `updated ${date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`;
}
