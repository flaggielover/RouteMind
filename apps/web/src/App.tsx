import {
  AlertTriangle,
  ArrowUpRight,
  Bike,
  CircleDot,
  Gauge,
  ListFilter,
  PackageCheck,
  Route,
} from "lucide-react";
import { lazy, Suspense, useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";
import { BrowserRouter, Navigate, Route as RouterRoute, Routes } from "react-router-dom";
import { demoDataSource } from "./data/demoSnapshot";
import { probeServices } from "./data/health";
import { liveDataSource, loadLiveSnapshot } from "./data/liveSnapshot";
import { replayDataSource } from "./data/replay";
import { simulationDataSource } from "./data/simulation";
import {
  applyRealtimeItem,
  createAuthenticatedRealtimeStream,
  type RealtimeConnectionState,
} from "./data/realtime";
import {
  loadBrowserTenantSession,
  sessionScope,
  type TenantSession,
  type TenantSessionProvider,
} from "./data/session";
import type {
  DataSourceMode,
  OperationsDataSource,
  ReplayCommand,
  ServiceHealth,
  SimulationCommand,
  Role,
} from "./domain/model";
import { roles } from "./domain/model";
import { countOpenExceptions, findOrder, orderStatusLabel, statusTone } from "./domain/selectors";
import { AppShell } from "./components/AppShell";
import { LifecycleTimeline } from "./components/LifecycleTimeline";
import { MetricCell } from "./components/MetricCell";
import { OperationsMap } from "./components/OperationsMap";
import { MultiCityGeoPanel } from "./components/MultiCityGeoPanel";
import { CityZoneDrilldownPanel } from "./components/CityZoneDrilldownPanel";
import { FlowVisualizationPanel } from "./components/FlowVisualizationPanel";
import { GeoAnalyticalLayersPanel } from "./components/GeoAnalyticalLayersPanel";
import { DecisionXrayPanel } from "./components/DecisionXrayPanel";
import { ReliabilityCenterPanel } from "./components/ReliabilityCenterPanel";
import { TwinVisualizationPanel } from "./components/TwinVisualizationPanel";
import { ActivityStream } from "./components/ActivityStream";
import { SimulationControlPanel } from "./components/SimulationControlPanel";
import { ReplayPlaybackPanel } from "./components/ReplayPlaybackPanel";
import { StatusPill } from "./components/StatusPill";
import { OperationsAnalyticalStrip } from "./components/AnalyticalVisualizationFoundation";
import { OperationsMotionCoordinator } from "./components/OperationsMotionCoordinator";
import { UrbanFieldFallback } from "./components/UrbanFieldFallback";
import type { UrbanFieldSceneController } from "./components/UrbanFieldScene";
import { CourierView, CustomerView, MerchantView, StrategyView } from "./routes/RoleViews";
import type { Order, OperationsSnapshot } from "./domain/model";
import { toUrbanFieldState } from "./visuals/urbanFieldState";
import "./styles.css";

const LazyUrbanFieldScene = lazy(() => import("./components/UrbanFieldScene"));

interface AppProps {
  dataSource?: OperationsDataSource;
  healthProbe?: () => Promise<ServiceHealth[]>;
  sessionProvider?: TenantSessionProvider;
}

export default function App({
  dataSource,
  healthProbe = probeServices,
  sessionProvider = loadBrowserTenantSession,
}: AppProps) {
  const suppliedDataSource = dataSource;
  const [activeDataSource, setActiveDataSource] = useState<OperationsDataSource>(
    suppliedDataSource ?? liveDataSource,
  );
  const initialSnapshot = useMemo(() => activeDataSource.getSnapshot(), [activeDataSource]);
  const [snapshot, setSnapshot] = useState(initialSnapshot);
  const [health, setHealth] = useState<ServiceHealth[]>([...snapshot.health]);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [session, setSession] = useState<TenantSession | null>(null);
  const [sessionDetail, setSessionDetail] = useState("Verifying tenant session");
  const [sessionEpoch, setSessionEpoch] = useState(0);
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
    let mounted = true;
    if (activeDataSource === liveDataSource && !suppliedDataSource) {
      setSession(null);
      setSessionDetail("Verifying tenant session");
      void sessionProvider().then(async (result) => {
        if (!mounted) return;
        setSessionDetail(result.detail);
        if (!result.ok || !result.session) {
          setSnapshot({
            ...liveDataSource.getSnapshot(),
            availability: "unavailable",
            sourceDetail: `Live unavailable: ${result.detail}`,
          });
          return;
        }
        setSnapshot({
          ...liveDataSource.getSnapshot(),
          identityScope: sessionScope(result.session),
        });
        setSession(result.session);
        const loaded = await loadLiveSnapshot(result.session);
        if (mounted) setSnapshot(loaded);
      });
    } else {
      setSession(null);
      setSessionDetail("Isolated non-production source");
      if (activeDataSource.loadSnapshot) {
        void activeDataSource.loadSnapshot().then((loaded) => {
          if (mounted) setSnapshot(loaded);
        });
      }
    }
    return () => {
      mounted = false;
    };
  }, [activeDataSource, initialSnapshot, sessionEpoch, sessionProvider, suppliedDataSource]);

  useEffect(() => {
    const reload = () => {
      setSession(null);
      setSessionDetail("Tenant session changed; cached data cleared");
      setSnapshot(liveDataSource.getSnapshot());
      setSessionEpoch((epoch) => epoch + 1);
    };
    window.addEventListener("routemind:session-changed", reload);
    return () => window.removeEventListener("routemind:session-changed", reload);
  }, []);

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
    if (!session) {
      setRealtime({
        status: "degraded",
        cursor: "0",
        detail: "Verified tenant session is required for realtime",
        appliedEvents: 0,
        staleReason: "Verified tenant session is required for realtime",
        recentEvents: [],
      });
      return;
    }
    const endpoint = `${import.meta.env.VITE_BUSINESS_API_URL ?? "http://localhost:18080"}/api/v1/events/stream`;
    const stream = createAuthenticatedRealtimeStream({
      endpoint,
      session,
      onEvent: (item) =>
        setSnapshot((current) => applyRealtimeItem(current, item, session.tenantId)),
      onStateChange: setRealtime,
    });
    stream.start();
    return () => stream.stop();
  }, [activeDataSource, session]);

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

  const controlReplay = useCallback(
    async (command: ReplayCommand) => {
      if (!activeDataSource.controlReplay) return;
      setSnapshot(await activeDataSource.controlReplay(command));
    },
    [activeDataSource],
  );

  useEffect(() => {
    void refreshHealth();
  }, [refreshHealth]);

  const allowedRoles = useMemo<readonly Role[]>(
    () =>
      suppliedDataSource || activeDataSource !== liveDataSource
        ? roles
        : session && snapshot.identityScope === sessionScope(session)
          ? session.roles
          : [],
    [activeDataSource, session, snapshot.identityScope, suppliedDataSource],
  );

  return (
    <BrowserRouter>
      <AppShell
        health={health}
        source={snapshot.source}
        availability={snapshot.availability}
        sourceDetail={snapshot.sourceDetail}
        realtime={realtime}
        session={session}
        sessionDetail={sessionDetail}
        allowedRoles={allowedRoles}
        onSourceChange={changeSource}
        onRefreshHealth={() => void refreshHealth()}
      >
        <AppRoutes
          snapshot={snapshot}
          realtime={realtime}
          health={health}
          onSimulationControl={controlSimulation}
          onReplayControl={controlReplay}
          session={session}
          allowedRoles={allowedRoles}
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
  onReplayControl,
  session,
  allowedRoles = roles,
}: {
  snapshot: OperationsSnapshot;
  realtime: RealtimeConnectionState;
  health: readonly ServiceHealth[];
  onSimulationControl?: (command: SimulationCommand) => Promise<void>;
  onReplayControl?: (command: ReplayCommand) => Promise<void>;
  session?: TenantSession | null;
  allowedRoles?: readonly Role[];
}) {
  const authorize = (role: Role, element: ReactNode) =>
    allowedRoles.includes(role) ? element : <UnauthorizedRole role={role} />;
  const fallback = allowedRoles[0];
  return (
    <Routes>
      <RouterRoute
        path="/operations"
        element={authorize(
          "operations",
          <OperationsView
            snapshot={snapshot}
            realtime={realtime}
            health={health}
            onSimulationControl={onSimulationControl}
            onReplayControl={onReplayControl}
          />,
        )}
      />
      <RouterRoute
        path="/strategy"
        element={authorize("strategy", <StrategyView snapshot={snapshot} />)}
      />
      <RouterRoute
        path="/customer"
        element={authorize(
          "customer",
          <CustomerView snapshot={snapshot} realtime={realtime} session={session} />,
        )}
      />
      <RouterRoute
        path="/merchant"
        element={authorize("merchant", <MerchantView snapshot={snapshot} session={session} />)}
      />
      <RouterRoute
        path="/courier"
        element={authorize("courier", <CourierView snapshot={snapshot} session={session} />)}
      />
      <RouterRoute
        path="*"
        element={
          fallback ? <Navigate to={`/${fallback}`} replace /> : <UnauthorizedRole role={null} />
        }
      />
    </Routes>
  );
}

function UnauthorizedRole({ role }: { role: Role | null }) {
  return (
    <section className="access-boundary" role="alert" aria-labelledby="access-boundary-title">
      <AlertTriangle size={22} aria-hidden="true" />
      <div>
        <p className="eyebrow">Identity boundary</p>
        <h2 id="access-boundary-title">Workspace access unavailable</h2>
        <p>
          {role
            ? `The verified session is not authorized for the ${role} workspace.`
            : "A verified tenant session with a RouteMind role is required."}
        </p>
      </div>
    </section>
  );
}

function OperationsView({
  snapshot,
  realtime,
  health,
  onSimulationControl,
  onReplayControl,
}: {
  snapshot: OperationsSnapshot;
  realtime: RealtimeConnectionState;
  health: readonly ServiceHealth[];
  onSimulationControl?: (command: SimulationCommand) => Promise<void>;
  onReplayControl?: (command: ReplayCommand) => Promise<void>;
}) {
  const [selectedOrderId, setSelectedOrderId] = useState(snapshot.orders[0]?.id ?? "");
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [zoneFilter, setZoneFilter] = useState("all");
  const [lifecycleFilter, setLifecycleFilter] = useState("all");
  const [exceptionsOnly, setExceptionsOnly] = useState(false);
  const [freshOnly, setFreshOnly] = useState(false);
  const [decisionDetailsOpen, setDecisionDetailsOpen] = useState(false);
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
  const hasDispatchLatency =
    snapshot.availability === "ready" && snapshot.dispatch.latencyMs !== null;
  const urbanFieldState = useMemo(() => toUrbanFieldState(snapshot), [snapshot]);
  const sceneControllerRef = useRef<UrbanFieldSceneController | null>(null);
  const sourceModeLabel =
    snapshot.source === "live" ? "LIVE" : `${snapshot.source.toUpperCase()} · NON-PRODUCTION`;
  const filtersActive =
    zoneFilter !== "all" || lifecycleFilter !== "all" || exceptionsOnly || freshOnly;
  const clearFilters = () => {
    setZoneFilter("all");
    setLifecycleFilter("all");
    setExceptionsOnly(false);
    setFreshOnly(false);
  };
  return (
    <OperationsMotionCoordinator sceneControllerRef={sceneControllerRef}>
      <div className="page-stack">
        <section className="page-intro" data-motion-section="overview">
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
          <section
            className="operations-filters"
            data-motion-section="filters"
            aria-label="Operations filters"
          >
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
          <section
            className={`projection-state projection-${snapshot.availability}`}
            data-motion-section="projection"
            role="status"
          >
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
          <div data-motion-section="simulation">
            <SimulationControlPanel
              snapshot={snapshot.simulation}
              demandCount={snapshot.orders.length}
              supplyCount={snapshot.couriers.length}
              trafficLabel="seeded 1.0x"
              onControl={onSimulationControl}
            />
          </div>
        )}
        {snapshot.source === "replay" && snapshot.replay && onReplayControl && (
          <div data-motion-section="replay">
            <ReplayPlaybackPanel snapshot={snapshot.replay} onControl={onReplayControl} />
          </div>
        )}
        {(snapshot.source === "simulation" || snapshot.source === "replay") && (
          <TwinVisualizationPanel snapshot={snapshot} />
        )}
        <div className="operations-spatial-story">
          <section
            className="operations-hero"
            data-motion-section="spatial"
            aria-labelledby="urban-field-title"
          >
            <div
              className="operations-hero-stage"
              data-pointer-target="scene"
              data-pointer-id="urban-field"
            >
              <div className="operations-hero-heading">
                <div>
                  <p className="eyebrow">Urban operational field</p>
                  <h2 id="urban-field-title">City pressure, rendered as a living system.</h2>
                </div>
                <span className={`hero-mode-badge hero-mode-${snapshot.source}`}>
                  {sourceModeLabel}
                </span>
              </div>
              <Suspense fallback={<UrbanFieldFallback state={urbanFieldState} />}>
                <LazyUrbanFieldScene state={urbanFieldState} controllerRef={sceneControllerRef} />
              </Suspense>
              <p className="hero-provenance">
                {urbanFieldState.provenance === "snapshot-derived"
                  ? "Derived from the selected operational snapshot."
                  : "Deterministic visual demo state; not a production telemetry claim."}
              </p>
            </div>
            <aside className="operations-hero-rail" aria-label="Urban field semantic state">
              <div className="hero-rail-heading">
                <p className="eyebrow">System readout</p>
                <strong>{snapshot.dispatch.strategy}</strong>
                <span>strategy active</span>
              </div>
              <HeroMeter label="Order pressure" value={urbanFieldState.pressure} tone="teal" />
              <HeroMeter label="Courier supply" value={urbanFieldState.supply} tone="amber" />
              <HeroMeter label="SLA risk" value={urbanFieldState.risk} tone="risk" />
              <HeroMeter label="Traffic load" value={urbanFieldState.traffic} tone="slate" />
              <HeroMeter label="Twin fidelity" value={urbanFieldState.twinFidelity} tone="teal" />
              <div className="hero-rail-footnote">
                <span className="hero-status-dot" />
                <span>Signal mapping ready for live spatial state</span>
              </div>
            </aside>
          </section>
          <div className="operations-analytics" data-motion-section="analytics">
            <OperationsAnalyticalStrip snapshot={snapshot} />
          </div>
        </div>
        <section
          className="operations-health"
          data-motion-section="health"
          aria-label="Operations projection health"
        >
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
        <section
          className="metric-grid"
          data-motion-section="metrics"
          aria-label="Operational metrics"
        >
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
        <div data-motion-section="detail">
          <MultiCityGeoPanel />
        </div>
        <div data-motion-section="detail">
          <CityZoneDrilldownPanel snapshot={snapshot} />
        </div>
        <div data-motion-section="detail">
          <FlowVisualizationPanel snapshot={snapshot} />
        </div>
        <div data-motion-section="research">
          <GeoAnalyticalLayersPanel snapshot={snapshot} />
        </div>
        <div data-motion-section="research">
          <DecisionXrayPanel snapshot={snapshot} />
        </div>
        <div data-motion-section="reliability">
          <ReliabilityCenterPanel snapshot={snapshot} health={health} realtime={realtime} />
        </div>
        {openExceptions > 0 && (
          <div className="exception-banner" role="alert">
            <AlertTriangle size={16} aria-hidden="true" />
            <strong>{openExceptions} priority exception needs attention</strong>
            <span>Review the selected order before assigning another route.</span>
          </div>
        )}
        <section
          className="operations-alerts"
          data-motion-section="alerts"
          aria-label="Operations alerts and imbalance"
        >
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
        <section className="primary-grid" data-motion-section="detail">
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
            filtersActive={filtersActive}
            onClearFilters={clearFilters}
          />
        </section>
        <section className="secondary-grid" data-motion-section="detail">
          <section className="panel lifecycle-panel" aria-labelledby="lifecycle-title">
            <div className="panel-heading">
              <div>
                <p className="eyebrow">Selected order</p>
                <h2 id="lifecycle-title">{selectedOrder?.shortId ?? "No order"} lifecycle</h2>
                <span className="entity-freshness">
                  {snapshot.source} source ·{" "}
                  {snapshot.generatedAt
                    ? formatFreshness(snapshot.generatedAt)
                    : "freshness pending"}
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
                <dd>
                  {snapshot.dispatch.latencyMs === null
                    ? "Unavailable"
                    : `${snapshot.dispatch.latencyMs} ms`}
                </dd>
              </div>
              <div>
                <dt>Trace</dt>
                <dd>
                  {selectedOrder?.operational?.decision.requestId ??
                    snapshot.decisionLedger?.requestId ??
                    "Unavailable"}
                </dd>
              </div>
            </dl>
            <ActivityStream snapshot={snapshot} realtime={realtime} />
            <button
              className="text-button"
              type="button"
              aria-expanded={decisionDetailsOpen}
              aria-controls="decision-details"
              onClick={() => setDecisionDetailsOpen((open) => !open)}
            >
              {decisionDetailsOpen ? "Hide decision details" : "Open decision details"}{" "}
              <ArrowUpRight size={14} />
            </button>
            {decisionDetailsOpen && (
              <div
                className="decision-details"
                id="decision-details"
                role="region"
                aria-label="Decision details"
              >
                <dl className="detail-list">
                  <div>
                    <dt>Strategy version</dt>
                    <dd>{snapshot.dispatch.version}</dd>
                  </div>
                  <div>
                    <dt>Decision source</dt>
                    <dd>
                      {snapshot.source} · {formatFreshness(snapshot.generatedAt)}
                    </dd>
                  </div>
                  <div>
                    <dt>Rationale</dt>
                    <dd>{snapshot.dispatch.rationale}</dd>
                  </div>
                </dl>
              </div>
            )}
          </section>
        </section>
        <section
          className="entity-drawers"
          data-motion-section="detail"
          aria-label="Selected entity details"
        >
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
                <div>
                  <dt>Decision</dt>
                  <dd>{selectedOrder.operational?.decision.status ?? "Unavailable"}</dd>
                </div>
                <div>
                  <dt>Ledger request</dt>
                  <dd>{selectedOrder.operational?.decision.requestId ?? "Unavailable"}</dd>
                </div>
                <div>
                  <dt>Strategy</dt>
                  <dd>
                    {selectedOrder.operational?.decision.strategy ?? "Unavailable"} · v
                    {selectedOrder.operational?.decision.strategyVersion ?? "-"}
                  </dd>
                </div>
                <div>
                  <dt>Route / travel</dt>
                  <dd>{selectedOrder.operational?.route.status ?? "Unavailable"}</dd>
                </div>
                <div>
                  <dt>Courier freshness</dt>
                  <dd>{selectedOrder.operational?.courier.freshness.status ?? "Unavailable"}</dd>
                </div>
                <div>
                  <dt>Order freshness</dt>
                  <dd>{selectedOrder.operational?.orderFreshness.status ?? "Unavailable"}</dd>
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
            {snapshot.couriers.find(
              (courier) => courier.id === snapshot.dispatch.selectedCourier,
            ) ? (
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
    </OperationsMotionCoordinator>
  );
}

function HeroMeter({
  label,
  value,
  tone,
}: {
  label: string;
  value: number;
  tone: "teal" | "amber" | "risk" | "slate";
}) {
  return (
    <div className="hero-meter">
      <div className="hero-meter-label">
        <span>{label}</span>
        <strong>{Math.round(value * 100)}%</strong>
      </div>
      <div className={`hero-meter-track hero-meter-${tone}`} aria-hidden="true">
        <span style={{ width: `${Math.round(value * 100)}%` }} />
      </div>
    </div>
  );
}

function OrderQueue({
  orders,
  selectedOrderId,
  onSelectOrder,
  availability,
  filtersActive,
  onClearFilters,
}: {
  orders: readonly Order[];
  selectedOrderId: string;
  onSelectOrder: (id: string) => void;
  availability: OperationsSnapshot["availability"];
  filtersActive: boolean;
  onClearFilters: () => void;
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
      <button
        className="text-button"
        type="button"
        disabled={!filtersActive}
        onClick={onClearFilters}
      >
        {filtersActive ? "Show all orders" : "All orders visible"} <ArrowUpRight size={14} />
      </button>
    </section>
  );
}

function formatFreshness(value: string): string {
  if (!value) return "freshness pending";
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? value
    : `updated ${date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`;
}
