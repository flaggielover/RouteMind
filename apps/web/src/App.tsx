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
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
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
import { OperationsExperience } from "./components/OperationsExperience";
import { LocaleProvider, useLocale } from "./i18n";
import type { GeoWorldController } from "./visuals/geoWorldController";
import type { CityId } from "./visuals/cityGeo";
import { CourierView, CustomerView, MerchantView, StrategyView } from "./routes/RoleViews";
import type { Order, OperationsSnapshot } from "./domain/model";
import {
  interpolateUrbanWorldFrame,
  toOperationsChapterState,
} from "./visuals/operationsChapterState";
import "./styles.css";

interface AppProps {
  dataSource?: OperationsDataSource;
  healthProbe?: () => Promise<ServiceHealth[]>;
  sessionProvider?: TenantSessionProvider;
}

function dataSourceForMode(mode: DataSourceMode): OperationsDataSource {
  return mode === "live"
    ? liveDataSource
    : mode === "demo"
      ? demoDataSource
      : mode === "replay"
        ? replayDataSource
        : simulationDataSource;
}

function configuredDefaultDataSource(): OperationsDataSource {
  const configured = import.meta.env.VITE_DEFAULT_DATA_SOURCE;
  return configured === "demo" || configured === "replay" || configured === "simulation"
    ? dataSourceForMode(configured)
    : liveDataSource;
}

export default function App({
  dataSource,
  healthProbe = probeServices,
  sessionProvider = loadBrowserTenantSession,
}: AppProps) {
  const suppliedDataSource = dataSource;
  const [activeDataSource, setActiveDataSource] = useState<OperationsDataSource>(
    suppliedDataSource ?? configuredDefaultDataSource(),
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
      setActiveDataSource(dataSourceForMode(mode));
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
    <LocaleProvider>
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
            <RefreshingServiceHealthLabel />
          </span>
        )}
      </BrowserRouter>
    </LocaleProvider>
  );
}

function RefreshingServiceHealthLabel() {
  return <>{useLocale().t("a11y.refreshingServiceHealth")}</>;
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
  const { locale, t, formatNumber, formatDateTime } = useLocale();
  const [selectedOrderId, setSelectedOrderId] = useState(snapshot.orders[0]?.id ?? "");
  const [selectedCityId, setSelectedCityId] = useState<CityId>("shanghai");
  const [selectedTrajectoryId, setSelectedTrajectoryId] = useState<string | null>(null);
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
  const sceneControllerRef = useRef<GeoWorldController | null>(null);
  const chapterStates = useMemo(
    () => toOperationsChapterState(snapshot, selectedOrderId || null),
    [selectedOrderId, snapshot],
  );
  const [activeChapterIndex, setActiveChapterIndex] = useState(0);
  const lastChapterIndexRef = useRef(0);
  const activeWorldFrame = useMemo(
    () => chapterStates[activeChapterIndex]?.world ?? interpolateUrbanWorldFrame(chapterStates, 0),
    [activeChapterIndex, chapterStates],
  );
  const urbanFieldState = chapterStates[0]?.urbanField;
  const handleMotionFrame = useCallback(
    (frame: { progress: number; section: number; focus: number }) => {
      const chapterIndex = Math.min(chapterStates.length - 1, Math.max(0, frame.section));
      if (chapterIndex !== lastChapterIndexRef.current) {
        lastChapterIndexRef.current = chapterIndex;
        setActiveChapterIndex(chapterIndex);
      }
    },
    [chapterStates.length],
  );
  const sourceModeLabel =
    snapshot.source === "live"
      ? "LIVE"
      : t("ops.sourceMode", { mode: snapshot.source.toUpperCase() });
  const filtersActive =
    zoneFilter !== "all" || lifecycleFilter !== "all" || exceptionsOnly || freshOnly;
  const clearFilters = () => {
    setZoneFilter("all");
    setLifecycleFilter("all");
    setExceptionsOnly(false);
    setFreshOnly(false);
  };
  const handleCityChange = (cityId: CityId) => {
    setSelectedCityId(cityId);
    setSelectedTrajectoryId(null);
  };
  return (
    <OperationsMotionCoordinator
      sceneControllerRef={sceneControllerRef}
      onFrame={handleMotionFrame}
    >
      <OperationsExperience
        snapshot={snapshot}
        worldFrame={activeWorldFrame}
        cityId={selectedCityId}
        onCityChange={handleCityChange}
        selectedTrajectoryId={selectedTrajectoryId}
        onSelectTrajectory={setSelectedTrajectoryId}
        controllerRef={sceneControllerRef}
      >
        <section
          id="operations-chapter-overview"
          className="operations-chapter chapter-overview"
          data-motion-section="chapter-overview"
          data-chapter="overview"
          aria-labelledby="operations-overview-title"
        >
          <div className="chapter-overview-copy">
            <p className="eyebrow">01 / {t("chapter.overview")}</p>
            <h2 id="operations-overview-title">{t("chapter.overview.title")}</h2>
            <p className="chapter-lede">{t("chapter.overview.description")}</p>
            <div className="chapter-overview-actions">
              <span className="last-updated">
                <CircleDot size={13} />{" "}
                {t("ops.snapshot", {
                  value: snapshot.generatedAt
                    ? t("ops.updatedAt", {
                        value: formatFreshness(snapshot.generatedAt, formatDateTime),
                      })
                    : t("ops.snapshotFreshnessPending"),
                })}
              </span>
              <button
                className="button button-primary"
                type="button"
                aria-expanded={filtersOpen}
                onClick={() => setFiltersOpen((open) => !open)}
              >
                <ListFilter size={15} /> {t("ops.filterBoard")}
              </button>
            </div>
            {filtersOpen && (
              <section className="operations-filters" aria-label={t("ops.operationsFilters")}>
                <label>
                  {t("ops.zone")}
                  <select
                    value={zoneFilter}
                    onChange={(event) => setZoneFilter(event.target.value)}
                  >
                    <option value="all">{t("ops.allZones")}</option>
                    {[...new Set(snapshot.couriers.map((courier) => courier.zone))].map((zone) => (
                      <option key={zone} value={zone}>
                        {zone}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  {t("ops.lifecycle")}
                  <select
                    value={lifecycleFilter}
                    onChange={(event) => setLifecycleFilter(event.target.value)}
                  >
                    <option value="all">{t("ops.allLifecycle")}</option>
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
                  {t("ops.exceptionsOnly")}
                </label>
                <label className="filter-check">
                  <input
                    type="checkbox"
                    checked={freshOnly}
                    onChange={(event) => setFreshOnly(event.target.checked)}
                  />
                  {t("ops.hasFreshness")}
                </label>
                <span className="filter-result">
                  {t("ops.showing", {
                    shown: filteredOrders.length,
                    total: snapshot.orders.length,
                  })}
                </span>
              </section>
            )}
            {snapshot.availability !== "ready" && (
              <div className={`projection-state projection-${snapshot.availability}`} role="status">
                <strong>
                  {snapshot.availability === "loading"
                    ? t("ops.loadingProjections")
                    : snapshot.availability === "degraded"
                      ? t("ops.degradedProjections")
                      : t("ops.unavailableProjections")}
                </strong>
                <span>{snapshot.sourceDetail}</span>
              </div>
            )}
          </div>
          <div
            className="chapter-overview-orbit"
            data-pointer-target="hud"
            data-pointer-id="overview-readout"
          >
            <span className="orbit-label">{t("ops.networkSignal")}</span>
            <strong>{formatNumber(Math.round((urbanFieldState?.pressure ?? 0) * 100))}%</strong>
            <span>{t("ops.pressureIndex")}</span>
            <div className="overview-meter-stack">
              <HeroMeter
                label={t("ops.orderPressure")}
                value={urbanFieldState?.pressure ?? 0}
                tone="teal"
              />
              <HeroMeter
                label={t("ops.courierSupply")}
                value={urbanFieldState?.supply ?? 0}
                tone="amber"
              />
              <HeroMeter label={t("ops.slaRisk")} value={urbanFieldState?.risk ?? 0} tone="risk" />
              <HeroMeter
                label={t("ops.twinFidelity")}
                value={urbanFieldState?.twinFidelity ?? 0}
                tone="slate"
              />
            </div>
          </div>
          <div className="chapter-overview-stamp" aria-hidden="true">
            <span>ROUTEMIND</span>
            <strong>OP / 01</strong>
          </div>
        </section>
        <section
          id="operations-chapter-pressure"
          className="operations-chapter chapter-pressure"
          data-motion-section="chapter-pressure"
          data-chapter="pressure"
          aria-labelledby="pressure-title"
        >
          <div className="chapter-pressure-copy">
            <p className="eyebrow">02 / {t("chapter.pressure")}</p>
            <h2 id="pressure-title">{t("chapter.pressure.title")}</h2>
            <p>{t("chapter.pressure.description")}</p>
            <div className="pressure-facts">
              <span>
                <small>{t("ops.activeOrders")}</small>
                <strong>{formatNumber(snapshot.orders.length)}</strong>
              </span>
              <span>
                <small>{t("ops.availableCouriers")}</small>
                <strong>{formatNumber(availableCouriers)}</strong>
              </span>
              <span>
                <small>{t("ops.zonesInView")}</small>
                <strong>{formatNumber(zones)}</strong>
              </span>
            </div>
          </div>
          <div className="chapter-pressure-surface">
            <OperationsAnalyticalStrip snapshot={snapshot} focus="pressure" />
          </div>
        </section>
        <section
          id="operations-chapter-risk"
          className="operations-chapter chapter-risk"
          data-motion-section="chapter-risk"
          data-chapter="risk"
          aria-labelledby="risk-title"
        >
          <div className="chapter-risk-surface">
            <OperationsAnalyticalStrip snapshot={snapshot} focus="risk" />
          </div>
          <div className="chapter-risk-copy">
            <p className="eyebrow">03 / {t("chapter.risk")}</p>
            <h2 id="risk-title">{t("chapter.risk.title")}</h2>
            <p>{t("chapter.risk.description")}</p>
            <div className="risk-flag">
              <AlertTriangle size={16} />
              <span>
                <strong>{formatNumber(openExceptions)}</strong>{" "}
                {openExceptions === 1 ? t("ops.priorityException") : t("ops.priorityExceptions")}{" "}
                {t("ops.recorded")}
              </span>
            </div>
          </div>
        </section>
        <section
          id="operations-chapter-strategy"
          className="operations-chapter chapter-strategy"
          data-motion-section="chapter-strategy"
          data-chapter="strategy"
          aria-labelledby="strategy-title"
        >
          <div className="chapter-strategy-copy">
            <p className="eyebrow">04 / {t("chapter.strategy")}</p>
            <h2 id="strategy-title">{t("chapter.strategy.title")}</h2>
            <p>{snapshot.dispatch.rationale}</p>
            <div className="strategy-signal-line">
              <span>{t("ops.activeStrategy")}</span>
              <strong>{snapshot.dispatch.strategy}</strong>
              <small>
                v{snapshot.dispatch.version} · {snapshot.dispatch.latencyMs ?? "-"} ms
              </small>
            </div>
          </div>
          <div className="chapter-strategy-surface">
            <OperationsAnalyticalStrip snapshot={snapshot} focus="strategy" />
          </div>
        </section>
        <section
          id="operations-chapter-live"
          className="operations-chapter chapter-live"
          data-motion-section="chapter-live"
          data-chapter="live"
          aria-labelledby="live-title"
        >
          <div className="chapter-live-heading">
            <div>
              <p className="eyebrow">05 / {t("chapter.live")}</p>
              <h2 id="live-title">{t("chapter.live.title")}</h2>
            </div>
            <span className="chapter-live-status">
              <span className="live-dot" /> {sourceModeLabel}
            </span>
          </div>
          <div className="operations-legacy-stack">
            <section
              className="operations-health"
              data-motion-section="health"
              aria-label="Operations projection health"
            >
              <div>
                <p className="eyebrow">{t("ops.projectionHealth")}</p>
                <strong>
                  {health.length ? t("ops.serviceChecks") : t("ops.checkingServiceHealth")}
                </strong>
              </div>
              <div className="operations-health-items">
                {(health.length
                  ? health
                  : [
                      {
                        service: "business-api",
                        label: "Business API",
                        status: "checking" as const,
                      },
                    ]
                ).map((item) => (
                  <StatusPill key={item.service} status={item.status} label={item.label} />
                ))}
                <span className="health-freshness">
                  {snapshot.generatedAt
                    ? t("ops.snapshot", {
                        value: t("ops.updatedAt", {
                          value: formatFreshness(snapshot.generatedAt, formatDateTime),
                        }),
                      })
                    : t("ops.snapshotFreshnessPending")}
                </span>
              </div>
            </section>
            <section
              className="metric-grid"
              data-motion-section="metrics"
              aria-label="Operational metrics"
            >
              <MetricCell
                label={t("ops.activeOrders")}
                value={formatNumber(snapshot.orders.length)}
                detail={
                  openExceptions ? `${openExceptions} need attention` : "No recorded exceptions"
                }
                icon={PackageCheck}
                tone="accent"
              />
              <MetricCell
                label={t("ops.availableCouriers")}
                value={formatNumber(availableCouriers)}
                detail={
                  zones ? `Across ${zones} zone${zones === 1 ? "" : "s"}` : "Zone data pending"
                }
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
            <div className="live-geo-overview" data-motion-section="detail">
              <MultiCityGeoPanel />
            </div>
            <div className="live-zone-inspection" data-motion-section="detail">
              <CityZoneDrilldownPanel snapshot={snapshot} />
            </div>
            <div className="live-flow-inspection" data-motion-section="detail">
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
                <strong>
                  {t("ops.priorityExceptionNeedsAttention", { count: openExceptions })}
                </strong>
                <span>{t("ops.reviewSelectedOrder")}</span>
              </div>
            )}
            <section
              className="operations-alerts"
              data-motion-section="alerts"
              aria-label={
                locale === "en-US"
                  ? "Operations alerts and imbalance"
                  : `${t("ops.exceptionQueue")} / ${t("ops.supplyDemand")}`
              }
            >
              <section className="panel alert-panel">
                <div className="panel-heading">
                  <div>
                    <p className="eyebrow">{t("ops.exceptionQueue")}</p>
                    <h2>
                      {exceptionOrders.length} {t("ops.recorded")} {t("ops.priorityExceptions")}
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
                  <p className="empty-state">{t("ops.noRecordedExceptions")}</p>
                )}
              </section>
              <section className="panel alert-panel">
                <div className="panel-heading">
                  <div>
                    <p className="eyebrow">{t("ops.supplyDemand")}</p>
                    <h2>
                      {supplyGap > 0 ? t("ops.orderGap", { count: supplyGap }) : t("ops.covered")}
                    </h2>
                  </div>
                  <Gauge size={17} className="heading-icon" />
                </div>
                <dl className="detail-list">
                  <div>
                    <dt>{t("ops.ordersInSnapshot")}</dt>
                    <dd>{snapshot.orders.length}</dd>
                  </div>
                  <div>
                    <dt>{t("ops.availableCouriers")}</dt>
                    <dd>{availableCouriers}</dd>
                  </div>
                  <div>
                    <dt>{t("ops.overtimeRisk")}</dt>
                    <dd className="muted-label">{t("ops.unavailableFromSource")}</dd>
                  </div>
                </dl>
              </section>
            </section>
            <section className="primary-grid operations-queue-grid" data-motion-section="detail">
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
                    <p className="eyebrow">{t("ops.selectedOrderLabel")}</p>
                    <h2 id="lifecycle-title">{selectedOrder?.shortId ?? "No order"} lifecycle</h2>
                    <span className="entity-freshness">
                      {snapshot.source} source ·{" "}
                      {snapshot.generatedAt
                        ? t("ops.updatedAt", {
                            value: formatFreshness(snapshot.generatedAt, formatDateTime),
                          })
                        : t("ops.snapshotFreshnessPending")}
                    </span>
                  </div>
                  {selectedOrder ? (
                    <StatusPill
                      status={
                        statusTone(selectedOrder.status) === "success" ? "healthy" : "checking"
                      }
                      label={orderStatusLabel[selectedOrder.status]}
                    />
                  ) : (
                    <StatusPill status="checking" label={t("ops.noLiveOrders")} />
                  )}
                </div>
                {selectedOrder ? (
                  <LifecycleTimeline order={selectedOrder} />
                ) : (
                  <p className="empty-state">{t("ops.noOrders")}</p>
                )}
              </section>
              <section className="panel activity-panel" aria-labelledby="activity-title">
                <div className="panel-heading">
                  <div>
                    <p className="eyebrow">{t("ops.decisionTrace")}</p>
                    <h2 id="activity-title">{t("ops.dispatchActivity")}</h2>
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
                    <dt>{t("ops.selectedCourierLabel")}</dt>
                    <dd>{snapshot.dispatch.selectedCourier}</dd>
                  </div>
                  <div>
                    <dt>{t("ops.decisionLatency")}</dt>
                    <dd>
                      {snapshot.dispatch.latencyMs === null
                        ? t("ops.unavailable")
                        : `${snapshot.dispatch.latencyMs} ms`}
                    </dd>
                  </div>
                  <div>
                    <dt>{t("ops.trace")}</dt>
                    <dd>
                      {selectedOrder?.operational?.decision.requestId ??
                        snapshot.decisionLedger?.requestId ??
                        t("ops.unavailable")}
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
                  {decisionDetailsOpen
                    ? t("ops.hideDecisionDetails")
                    : t("ops.openDecisionDetails")}{" "}
                  <ArrowUpRight size={14} />
                </button>
                {decisionDetailsOpen && (
                  <div
                    className="decision-details"
                    id="decision-details"
                    role="region"
                    aria-label={t("ops.decisionDetails")}
                  >
                    <dl className="detail-list">
                      <div>
                        <dt>{t("ops.strategyVersion")}</dt>
                        <dd>{snapshot.dispatch.version}</dd>
                      </div>
                      <div>
                        <dt>{t("ops.decisionSource")}</dt>
                        <dd>
                          {snapshot.source} ·{" "}
                          {t("ops.updatedAt", {
                            value: formatFreshness(snapshot.generatedAt, formatDateTime),
                          })}
                        </dd>
                      </div>
                      <div>
                        <dt>{t("ops.rationale")}</dt>
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
                    <p className="eyebrow">{t("ops.orderDetail")}</p>
                    <h2>{selectedOrder?.shortId ?? t("ops.noOrderSelected")}</h2>
                  </div>
                  <PackageCheck size={17} className="heading-icon" />
                </div>
                {selectedOrder ? (
                  <dl className="detail-list">
                    <div>
                      <dt>{t("ops.routePoints")}</dt>
                      <dd>{selectedOrder.route.length || "Unavailable"}</dd>
                    </div>
                    <div>
                      <dt>Order version</dt>
                      <dd>{selectedOrder.version ?? t("ops.unavailable")}</dd>
                    </div>
                    <div>
                      <dt>{t("ops.source")}</dt>
                      <dd>
                        {snapshot.source} ·{" "}
                        {t("ops.updatedAt", {
                          value: formatFreshness(snapshot.generatedAt, formatDateTime),
                        })}
                      </dd>
                    </div>
                    <div>
                      <dt>{t("ops.decision")}</dt>
                      <dd>{selectedOrder.operational?.decision.status ?? "Unavailable"}</dd>
                    </div>
                    <div>
                      <dt>{t("ops.ledgerRequest")}</dt>
                      <dd>{selectedOrder.operational?.decision.requestId ?? "Unavailable"}</dd>
                    </div>
                    <div>
                      <dt>{t("ops.strategy")}</dt>
                      <dd>
                        {selectedOrder.operational?.decision.strategy ?? "Unavailable"} · v
                        {selectedOrder.operational?.decision.strategyVersion ?? "-"}
                      </dd>
                    </div>
                    <div>
                      <dt>{t("ops.routeTravel")}</dt>
                      <dd>{selectedOrder.operational?.route.status ?? "Unavailable"}</dd>
                    </div>
                    <div>
                      <dt>{t("ops.courierFreshness")}</dt>
                      <dd>
                        {selectedOrder.operational?.courier.freshness.status ?? "Unavailable"}
                      </dd>
                    </div>
                    <div>
                      <dt>{t("ops.orderFreshness")}</dt>
                      <dd>{selectedOrder.operational?.orderFreshness.status ?? "Unavailable"}</dd>
                    </div>
                  </dl>
                ) : (
                  <p className="empty-state">{t("ops.selectOrderToInspect")}</p>
                )}
              </section>
              <section className="panel entity-drawer">
                <div className="panel-heading">
                  <div>
                    <p className="eyebrow">{t("ops.courierDetail")}</p>
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
                            <dt>{t("ops.zone")}</dt>
                            <dd>{courier.zone}</dd>
                          </div>
                          <div>
                            <dt>{t("ops.status")}</dt>
                            <dd>{courier.status.replace("_", " ")}</dd>
                          </div>
                          <div>
                            <dt>{t("ops.position")}</dt>
                            <dd>
                              {courier.position.x}, {courier.position.y}
                            </dd>
                          </div>
                        </>
                      );
                    })()}
                  </dl>
                ) : (
                  <p className="empty-state">{t("ops.courierUnavailable")}</p>
                )}
              </section>
            </section>
          </div>
        </section>
        <section
          id="operations-chapter-replay"
          className="operations-chapter chapter-replay"
          data-motion-section="chapter-replay"
          data-chapter="replay"
          aria-labelledby="replay-title"
        >
          <div className="chapter-replay-copy">
            <p className="eyebrow">06 / {t("chapter.replay")}</p>
            <h2 id="replay-title">{t("chapter.replay.title")}</h2>
            <p>{t("chapter.replay.description")}</p>
            <div className="replay-clock" data-pointer-target="hud" data-pointer-id="replay-clock">
              <span>{t("ops.clockDomain")}</span>
              <strong>{snapshot.clockDomain}</strong>
              <small>
                {snapshot.replay?.verified
                  ? t("ops.digestVerified")
                  : snapshot.simulation
                    ? t("ops.tick", { value: snapshot.simulation.tick })
                    : t("ops.snapshotReady")}
              </small>
            </div>
          </div>
          <div className="chapter-replay-dock">
            {snapshot.source === "simulation" && snapshot.simulation && onSimulationControl ? (
              <SimulationControlPanel
                snapshot={snapshot.simulation}
                demandCount={snapshot.orders.length}
                supplyCount={snapshot.couriers.length}
                trafficLabel="seeded 1.0x"
                onControl={onSimulationControl}
              />
            ) : snapshot.source === "replay" && snapshot.replay && onReplayControl ? (
              <ReplayPlaybackPanel snapshot={snapshot.replay} onControl={onReplayControl} />
            ) : (
              <div className="replay-dock-empty">
                <span className="eyebrow">{t("ops.replayDock")}</span>
                <strong>{t("ops.chooseReplay")}</strong>
                <span>{t("ops.replayDisabled")}</span>
              </div>
            )}
            {(snapshot.source === "simulation" || snapshot.source === "replay") && (
              <TwinVisualizationPanel snapshot={snapshot} />
            )}
          </div>
        </section>
        <section
          id="operations-chapter-research"
          className="operations-chapter chapter-research"
          data-motion-section="chapter-research"
          data-chapter="research"
          aria-labelledby="research-title"
        >
          <div className="chapter-research-heading">
            <p className="eyebrow">07 / {t("chapter.research")}</p>
            <h2 id="research-title">{t("chapter.research.title")}</h2>
            <p>{t("chapter.research.description")}</p>
          </div>
          <div className="chapter-research-wall">
            <details className="evidence-module evidence-module-primary" open>
              <summary>{t("ops.spatialEvidenceLayers")}</summary>
              <GeoAnalyticalLayersPanel snapshot={snapshot} />
            </details>
            <details className="evidence-module">
              <summary>{t("ops.decisionLineage")}</summary>
              <DecisionXrayPanel snapshot={snapshot} />
            </details>
            <details className="evidence-module evidence-module-wide">
              <summary>{t("ops.reliabilityEvidence")}</summary>
              <ReliabilityCenterPanel snapshot={snapshot} health={health} realtime={realtime} />
            </details>
          </div>
        </section>
      </OperationsExperience>
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
  const { t } = useLocale();
  return (
    <section className="panel queue-panel" aria-labelledby="queue-title">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">{t("ops.demandQueue")}</p>
          <h2 id="queue-title">{t("ops.ordersInMotionTitle")}</h2>
        </div>
        <span className="count-badge">{orders.length}</span>
      </div>
      <div className="queue-list">
        {orders.length === 0 ? (
          <p className="empty-state queue-empty">
            {availability === "loading"
              ? t("ops.loadingLiveOrders")
              : availability === "unavailable"
                ? t("ops.ordersUnavailable")
                : t("ops.noOrders")}
          </p>
        ) : (
          orders.map((order) => (
            <button
              className={`queue-item ${order.id === selectedOrderId ? "selected" : ""}`}
              key={order.id}
              onClick={() => onSelectOrder(order.id)}
              type="button"
              aria-label={t("ops.selectOrder", { id: order.shortId })}
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
        {filtersActive ? t("ops.showAllOrders") : t("ops.allOrdersVisible")}{" "}
        <ArrowUpRight size={14} />
      </button>
    </section>
  );
}

function formatFreshness(
  value: string,
  formatDateTime: (value: Date | string | number, options?: Intl.DateTimeFormatOptions) => string,
): string {
  if (!value) return "";
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? value
    : formatDateTime(date, { hour: "2-digit", minute: "2-digit" });
}
