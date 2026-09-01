import {
  ArrowUpRight,
  Bike,
  CheckCircle2,
  CircleDot,
  Clock3,
  Gauge,
  PackageCheck,
  RefreshCw,
  Route,
  ShieldCheck,
  Store,
  UserRound,
} from "lucide-react";
import { useEffect, useState } from "react";
import {
  fallbackStrategyRegistry,
  loadStrategyRegistry,
  type StrategyDescriptor,
} from "../data/strategies";
import { whatIfDataSource } from "../data/whatIf";
import {
  createCustomerOrder,
  createIdempotencyKey,
  recordCourierLocation,
  transitionCourierOrder,
  transitionCourierShift,
  transitionMerchantOrder,
  type CourierCommandResult,
  type CustomerOrderCommandResult,
} from "../data/orderCommands";
import type { RealtimeConnectionState } from "../data/realtime";
import type { TenantSession } from "../data/session";
import type { OperationsSnapshot } from "../domain/model";
import { orderStatusLabel } from "../domain/selectors";
import { LifecycleTimeline } from "../components/LifecycleTimeline";
import { WhatIfComparisonPanel } from "../components/WhatIfComparisonPanel";
import { StrategyComparisonPanel } from "../components/StrategyComparisonPanel";
import { StrategyAnalyticsPanel } from "../components/StrategyAnalyticsPanel";
import { ResearchCenterPanel } from "../components/ResearchCenterPanel";
import { StatusPill } from "../components/StatusPill";
import { useLocale } from "../i18n";

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

const orderStatusLabelZh: Record<keyof typeof orderStatusLabel, string> = {
  CREATED: "已创建",
  CONFIRMED: "已确认",
  PREPARING: "备餐中",
  READY_FOR_PICKUP: "待取货",
  ASSIGNED: "已分配",
  ACCEPTED: "已接受分配",
  ARRIVED: "已到达商户",
  PICKED_UP: "已取货",
  OUT_FOR_DELIVERY: "配送中",
  DELIVERED: "已送达",
  ASSIGNMENT_TIMED_OUT: "分配超时",
  ASSIGNMENT_REJECTED: "拒绝分配",
  REASSIGNMENT_PENDING: "等待重新分配",
  COMPENSATING: "补偿处理中",
  COMPENSATED: "已补偿",
  CANCELLED: "已取消",
};

function displayOrderStatus(status: keyof typeof orderStatusLabel, locale: string): string {
  return locale === "zh-CN" ? orderStatusLabelZh[status] : orderStatusLabel[status];
}

function displayCourierStatus(status: string, locale: string): string {
  if (locale !== "zh-CN") return status.replace("_", " ");
  return (
    {
      on_route: "路线中",
      available: "可用",
      offline: "离线",
      busy: "繁忙",
    }[status] ?? status.replace("_", " ")
  );
}

function displayStrategyDescriptor(value: string, locale: string): string {
  if (locale !== "zh-CN") return value;
  return (
    {
      baseline: "基线",
      engineering: "工程",
      production: "生产候选",
      research: "研究",
      dispatch: "调度",
      "batch-assignment": "批量分配",
      "risk-scoring": "风险评分",
      "partitioned-assignment": "分区分配",
      "local-search": "局部搜索",
      vrp: "车辆路径",
      vrptw: "时间窗路径",
    }[value] ?? value
  );
}

export function StrategyView({ snapshot }: { snapshot: OperationsSnapshot }) {
  const { t, locale } = useLocale();
  const [registryOpen, setRegistryOpen] = useState(false);
  const [registry, setRegistry] = useState<readonly StrategyDescriptor[]>(fallbackStrategyRegistry);
  const [comparison, setComparison] = useState<Awaited<
    ReturnType<typeof whatIfDataSource.run>
  > | null>(null);
  const strategyAvailable =
    snapshot.availability === "ready" && snapshot.dispatch.strategy !== "unavailable";
  const activeStrategy = snapshot.dispatch.strategy;
  useEffect(() => {
    let mounted = true;
    void loadStrategyRegistry().then((descriptors) => {
      if (mounted) setRegistry(descriptors);
    });
    return () => {
      mounted = false;
    };
  }, []);
  const strategyNames = registry.map((descriptor) => descriptor.name);
  const assignedOrders = snapshot.orders.filter((candidate) =>
    ["ASSIGNED", "ACCEPTED", "ARRIVED", "PICKED_UP", "OUT_FOR_DELIVERY", "DELIVERED"].includes(
      candidate.status,
    ),
  ).length;
  const assignmentSignal =
    snapshot.orders.length > 0
      ? locale === "zh-CN"
        ? `${assignedOrders}/${snapshot.orders.length} 已分配`
        : `${assignedOrders}/${snapshot.orders.length} assigned`
      : t("role.notRecorded");
  return (
    <RolePage
      eyebrow={t("role.strategyEyebrow")}
      title={t("role.strategyTitle")}
      lede={t("role.strategyLede")}
      icon={Gauge}
    >
      <section className="content-grid-two">
        <section className="panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">{t("role.activePolicy")}</p>
              <h2>{activeStrategy}</h2>
            </div>
            <StatusPill
              status={strategyAvailable ? "healthy" : "unavailable"}
              label={strategyAvailable ? t("role.registered") : t("role.unavailable")}
            />
          </div>
          <div className="strategy-score">
            <span>{t("role.recordedAssignmentSignal")}</span>
            <strong>{assignmentSignal}</strong>
            <small>{t("role.assignmentRecordedHint")}</small>
          </div>
          <dl className="detail-list">
            <div>
              <dt>{t("role.version")}</dt>
              <dd>{snapshot.dispatch.version}</dd>
            </div>
            <div>
              <dt>{t("role.lastDecision")}</dt>
              <dd>
                {strategyAvailable && snapshot.dispatch.latencyMs !== null
                  ? `${snapshot.dispatch.latencyMs} ms`
                  : t("role.unavailable")}
              </dd>
            </div>
            <div>
              <dt>{t("role.shadowMode")}</dt>
              <dd>
                {snapshot.source === "simulation"
                  ? t("role.unavailableSimulation")
                  : t("role.notRecorded")}
              </dd>
            </div>
            <div>
              <dt>{t("role.replayArtifact")}</dt>
              <dd>
                {snapshot.replay
                  ? snapshot.replay.verified
                    ? `${t("role.verified")} · ${snapshot.replay.artifactId}`
                    : `${t("role.unavailable")} · ${snapshot.replay.verificationError ?? t("role.verificationPending")}`
                  : t("role.unavailableSource")}
              </dd>
            </div>
          </dl>
        </section>
        <section className="panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">{t("role.baselineComparison")}</p>
              <h2>{t("role.registeredStrategies")}</h2>
            </div>
            <ShieldCheck size={17} className="heading-icon" />
          </div>
          {registry.map((descriptor) => {
            const active = descriptor.name === activeStrategy;
            return (
              <div className={`strategy-row${active ? " active" : ""}`} key={descriptor.name}>
                <span>
                  <strong>{descriptor.name}</strong>
                  <small>
                    v{descriptor.version} ·{" "}
                    {displayStrategyDescriptor(descriptor.maturity.toLowerCase(), locale)}
                  </small>
                </span>
                <span className="muted-label">
                  {active
                    ? t("role.currentPolicy")
                    : descriptor.capabilities
                        .map((capability) => displayStrategyDescriptor(capability, locale))
                        .join(" · ")}
                </span>
                <StatusPill
                  status={active && strategyAvailable ? "healthy" : "checking"}
                  label={active && strategyAvailable ? t("role.registered") : t("role.available")}
                />
              </div>
            );
          })}
          <button
            className="text-button"
            type="button"
            aria-expanded={registryOpen}
            aria-controls="strategy-registry"
            onClick={() => setRegistryOpen((open) => !open)}
          >
            {registryOpen ? t("role.hideRegistry") : t("role.openRegistry")}{" "}
            <ArrowUpRight size={14} />
          </button>
          {registryOpen && (
            <div
              className="strategy-registry"
              id="strategy-registry"
              role="region"
              aria-label={t("role.strategyRegistry")}
            >
              <p className="panel-subtitle">{t("role.registryDescription")}</p>
              <ul>
                {registry.map((descriptor) => (
                  <li key={descriptor.name}>
                    <strong>{descriptor.name}</strong>
                    <span>
                      v{descriptor.version} ·{" "}
                      {displayStrategyDescriptor(descriptor.maturity.toLowerCase(), locale)} ·{" "}
                      {descriptor.parameters.length
                        ? descriptor.parameters
                            .map((parameter) => `${parameter.key}=${parameter.default}`)
                            .join(", ")
                        : t("role.noConfigurableParameters")}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </section>
      </section>
      <WhatIfComparisonPanel
        strategies={strategyNames}
        onRun={(variant) => whatIfDataSource.run(variant)}
      />
      <StrategyComparisonPanel
        strategies={strategyNames}
        onRun={(variants) => whatIfDataSource.runMany(variants)}
        onComparisonChange={setComparison}
      />
      <StrategyAnalyticsPanel comparison={comparison} />
      <ResearchCenterPanel snapshot={snapshot} comparison={comparison} />
    </RolePage>
  );
}

type CustomerCommandState =
  { kind: "pending"; idempotencyKey: string } | CustomerOrderCommandResult | null;

type CourierCommandState =
  { kind: "pending"; idempotencyKey: string } | CourierCommandResult | null;

export function CustomerView({
  snapshot,
  realtime,
  session,
}: {
  snapshot: OperationsSnapshot;
  realtime: RealtimeConnectionState;
  session?: TenantSession | null;
}) {
  const { t, locale } = useLocale();
  const order = snapshot.orders[0];
  const courier = snapshot.couriers[0];
  const sourceDetail =
    locale === "zh-CN" &&
    snapshot.sourceDetail === "Deterministic fixture for offline demonstration"
      ? "用于离线演示的确定性固件"
      : snapshot.sourceDetail;
  const [command, setCommand] = useState<CustomerCommandState>(null);
  const [idempotencyKey, setIdempotencyKey] = useState(createIdempotencyKey);
  const commandAvailable =
    snapshot.source === "live" &&
    snapshot.availability === "ready" &&
    Boolean(session?.roles.includes("customer"));
  const trackingStatus =
    realtime.status === "connected"
      ? "healthy"
      : realtime.status === "disabled"
        ? "checking"
        : "unavailable";
  const trackingLabel =
    realtime.status === "connected"
      ? t("role.liveTracking")
      : realtime.status === "disabled"
        ? t("role.trackingPaused")
        : t("role.trackingDegraded");

  const submitOrder = async () => {
    if (!commandAvailable || !session || command?.kind === "pending") return;
    setCommand({ kind: "pending", idempotencyKey });
    const result = await createCustomerOrder({ session, idempotencyKey });
    setCommand(result);
    if (result.kind === "success") setIdempotencyKey(createIdempotencyKey());
  };

  return (
    <RolePage
      eyebrow={t("role.customerEyebrow")}
      title={t("role.customerTitle")}
      lede={t("role.customerLede")}
      icon={UserRound}
    >
      <section className="content-grid-two">
        <section className="panel customer-order">
          {!order ? (
            <p className="empty-state">{t("role.noOrderSource")}</p>
          ) : (
            <>
              <div className="panel-heading">
                <div>
                  <p className="eyebrow">
                    {t("role.orderPrefix")} {order.shortId}
                  </p>
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
                  label={displayOrderStatus(order.status, locale)}
                />
              </div>
              <div className="customer-destination">
                <MapPinIcon />
                <div>
                  <span>{t("role.deliveredTo")}</span>
                  <strong>{order.destination}</strong>
                </div>
              </div>
              <LifecycleTimeline order={order} />
              <div className="customer-tracking-meta">
                <StatusPill status={trackingStatus} label={trackingLabel} />
                <span>
                  {t("role.orderVersion")} {order.version ?? t("role.unknown")} · {sourceDetail}
                </span>
              </div>
            </>
          )}
        </section>
        <section className="panel">
          {!courier ? (
            <p className="empty-state">{t("role.noCourierSource")}</p>
          ) : (
            <>
              <div className="panel-heading">
                <div>
                  <p className="eyebrow">{t("role.courier")}</p>
                  <h2>{courier.name}</h2>
                </div>
                <Bike size={18} className="heading-icon" />
              </div>
              <div className="courier-card">
                <div className="avatar">{courier.name.slice(0, 2).toUpperCase()}</div>
                <div>
                  <strong>
                    {order ? displayOrderStatus(order.status, locale) : t("role.noActiveOrder")}
                  </strong>
                  <p>
                    {courier.zone} · {displayCourierStatus(courier.status, locale)}
                  </p>
                </div>
              </div>
            </>
          )}
          <div className="customer-command" aria-label={t("role.customerCommand")}>
            <div className="panel-heading">
              <div>
                <p className="eyebrow">{t("role.javaCommand")}</p>
                <h2>{t("role.startNewOrder")}</h2>
              </div>
              <RefreshCw size={18} className="heading-icon" />
            </div>
            <p className="panel-copy">{t("role.createOrderDescription")}</p>
            <button
              className="button button-primary"
              type="button"
              disabled={!commandAvailable || command?.kind === "pending"}
              onClick={() => void submitOrder()}
            >
              <RefreshCw size={15} className={command?.kind === "pending" ? "spin" : undefined} />
              {command?.kind === "pending" ? t("role.submitting") : t("role.createOrder")}
            </button>
            {!commandAvailable && (
              <p className="command-note" role="status">
                {snapshot.source === "live"
                  ? !session
                    ? t("role.identityRequired", { role: locale === "zh-CN" ? "客户" : "customer" })
                    : snapshot.availability === "degraded"
                      ? t("role.liveDegradedCommands")
                      : t("role.waitingLiveSnapshot")
                  : t("role.writingDisabled")}
              </p>
            )}
            {command?.kind === "success" && (
              <div className="command-result" role="status">
                <strong>
                  {command.replayed ? t("role.replayAcknowledged") : t("role.orderCreated")}
                </strong>
                <span>
                  {command.orderId} · {command.status} · version {command.version}
                </span>
                <small>
                  {t("role.trace")} {command.traceId ?? t("role.notReturned")} · {t("role.key")}{" "}
                  {command.idempotencyKey}
                </small>
              </div>
            )}
            {command?.kind === "error" && (
              <div className="command-result command-error" role="alert">
                <strong>{t("role.commandNotAccepted", { code: command.code })}</strong>
                <span>
                  {command.failureState === "unavailable" || command.failureState === "timeout"
                    ? t("role.retryIdempotency")
                    : command.failureState === "conflict"
                      ? t("role.refreshStaleOrder")
                      : t("role.resolveValidation")}
                </span>
                <small>
                  {t("role.trace")} {command.traceId ?? t("role.notReturned")} · {t("role.key")}{" "}
                  {command.idempotencyKey}
                </small>
              </div>
            )}
          </div>
        </section>
      </section>
    </RolePage>
  );
}

export function MerchantView({
  snapshot,
  session,
}: {
  snapshot: OperationsSnapshot;
  session?: TenantSession | null;
}) {
  const { t, locale } = useLocale();
  const [command, setCommand] = useState<CustomerCommandState>(null);
  const order =
    snapshot.orders.find((candidate) =>
      ["CREATED", "CONFIRMED", "PREPARING"].includes(candidate.status),
    ) ?? snapshot.orders[0];
  const nextCommand = order
    ? order.status === "CREATED"
      ? { target: "CONFIRMED" as const, label: t("role.acceptOrder") }
      : order.status === "CONFIRMED"
        ? { target: "PREPARING" as const, label: t("role.startPreparation") }
        : order.status === "PREPARING"
          ? { target: "READY_FOR_PICKUP" as const, label: t("role.markReady") }
          : null
    : null;
  const commandAvailable =
    snapshot.source === "live" &&
    snapshot.availability === "ready" &&
    Boolean(session?.roles.includes("merchant"));
  const ordersInPrep =
    snapshot.availability === "ready"
      ? snapshot.orders.filter((candidate) => candidate.status === "PREPARING").length
      : null;
  const handoffsNext =
    snapshot.availability === "ready"
      ? snapshot.orders.filter((candidate) => candidate.status === "READY_FOR_PICKUP").length
      : null;
  const prepMinutes = snapshot.merchants[0]?.prepMinutes ?? 0;
  const queueStatus =
    snapshot.availability !== "ready"
      ? "unavailable"
      : ordersInPrep !== null && ordersInPrep > 0
        ? "busy"
        : "open";
  const readyEvent = order?.events.find((event) => event.status === "READY_FOR_PICKUP");
  const submitTransition = async () => {
    if (!order || !nextCommand || !commandAvailable || !session || command?.kind === "pending")
      return;
    const idempotencyKey = `merchant-${nextCommand.target.toLowerCase()}-${order.id}-${order.version ?? 0}`;
    setCommand({ kind: "pending", idempotencyKey });
    const result = await transitionMerchantOrder({
      session,
      orderId: order.id,
      target: nextCommand.target,
      expectedVersion: order.version ?? 0,
      idempotencyKey,
    });
    setCommand(result);
  };
  return (
    <RolePage
      eyebrow={t("role.merchantEyebrow")}
      title={t("role.merchantTitle")}
      lede={t("role.merchantLede")}
      icon={Store}
    >
      <section className="content-grid-two">
        <section className="panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">{t("role.kitchenQueue")}</p>
              <h2>{t("role.todayAtGlance")}</h2>
            </div>
            <StatusPill
              status={queueStatus}
              label={
                queueStatus === "unavailable"
                  ? t("role.unavailable")
                  : queueStatus === "busy"
                    ? t("role.busy")
                    : t("role.ready")
              }
            />
          </div>
          <div className="merchant-stats">
            <div>
              <strong>{ordersInPrep ?? "Unavailable"}</strong>
              <span>{t("role.ordersInPrep")}</span>
            </div>
            <div>
              <strong>{prepMinutes > 0 ? `${prepMinutes}m` : t("role.unavailable")}</strong>
              <span>{t("role.avgPrepTime")}</span>
            </div>
            <div>
              <strong>{handoffsNext ?? t("role.unavailable")}</strong>
              <span>{t("role.handoffsNext")}</span>
            </div>
          </div>
          {snapshot.merchants.map((merchant) => (
            <div className="merchant-row" key={merchant.id}>
              <span>
                <strong>{merchant.name}</strong>
                <small>
                  {merchant.queue} {t("role.ordersQueued")} · {merchant.prepMinutes}m
                </small>
              </span>
              <StatusPill status={merchant.status} />
            </div>
          ))}
        </section>
        <section className="panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">{t("role.nextHandoff")}</p>
              <h2>{order?.shortId ?? t("role.noActiveHandoff")}</h2>
            </div>
            <PackageCheck size={18} className="heading-icon" />
          </div>
          <div className="handoff-state">
            <div className="handoff-icon">
              <Clock3 size={19} />
            </div>
            <div>
              <strong>
                {order ? displayOrderStatus(order.status, locale) : t("role.noOrderAvailable")}
              </strong>
              <p>
                {order
                  ? `${order.merchantName} · ${order.shortId} · ${t("role.orderVersion")} ${order.version ?? t("role.unknown")}`
                  : t("role.selectLiveOrder")}
              </p>
            </div>
          </div>
          <div className="readiness-details" aria-label={t("role.readinessTiming")}>
            <span>
              {t("role.expectedReady")} <strong>{order?.eta ?? t("role.unavailable")}</strong>
            </span>
            <span>
              {t("role.actualReady")} <strong>{readyEvent?.at ?? t("role.noRecorded")}</strong>
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
              {command?.kind === "pending" ? t("role.submitting") : nextCommand.label}
            </button>
          )}
          {!commandAvailable && (
            <p className="command-note" role="status">
              {snapshot.source === "live"
                ? !session
                  ? t("role.identityRequired", { role: locale === "zh-CN" ? "商户" : "merchant" })
                  : snapshot.availability === "degraded"
                    ? t("role.liveDegradedCommands")
                    : t("role.waitingLiveSnapshot")
                : t("role.writingDisabled")}
            </p>
          )}
          {command?.kind === "success" && (
            <div className="command-result" role="status">
              <strong>
                {command.replayed ? t("role.replayAcknowledged") : t("role.merchantAccepted")}
              </strong>
              <span>
                {command.orderId} · {command.status} · version {command.version}
              </span>
              <small>
                {t("role.trace")} {command.traceId ?? t("role.notReturned")} · {t("role.key")}{" "}
                {command.idempotencyKey}
              </small>
            </div>
          )}
          {command?.kind === "error" && (
            <div className="command-result command-error" role="alert">
              <strong>{t("role.commandNotAccepted", { code: command.code })}</strong>
              <span>
                {command.failureState === "unavailable" || command.failureState === "timeout"
                  ? t("role.retryIdempotency")
                  : command.failureState === "conflict"
                    ? t("role.refreshStaleOrder")
                    : t("role.resolveValidation")}
              </span>
              <small>
                {t("role.trace")} {command.traceId ?? t("role.notReturned")} · {t("role.key")}{" "}
                {command.idempotencyKey}
              </small>
            </div>
          )}
        </section>
      </section>
    </RolePage>
  );
}

export function CourierView({
  snapshot,
  session,
}: {
  snapshot: OperationsSnapshot;
  session?: TenantSession | null;
}) {
  const { t, locale } = useLocale();
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
      ? { target: "ACCEPTED" as const, label: t("role.acceptTask") }
      : order.status === "ACCEPTED"
        ? { target: "ARRIVED" as const, label: t("role.arriveMerchant") }
        : order.status === "ARRIVED"
          ? { target: "PICKED_UP" as const, label: t("role.confirmPickup") }
          : order.status === "PICKED_UP" || order.status === "OUT_FOR_DELIVERY"
            ? { target: "DELIVERED" as const, label: t("role.completeDelivery") }
            : null
    : null;
  const commandAvailable =
    snapshot.source === "live" &&
    snapshot.availability === "ready" &&
    Boolean(courier) &&
    Boolean(session?.roles.includes("courier"));
  const online = localShift ?? (courier?.status === "offline" ? "OFFLINE" : "ONLINE");
  const submitOrderTransition = async () => {
    if (
      !courier ||
      !order ||
      !nextCommand ||
      !commandAvailable ||
      !session ||
      command?.kind === "pending"
    )
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
        session,
        orderId: order.id,
        target: nextCommand.target,
        expectedVersion,
        idempotencyKey,
      }),
    );
  };
  const submitShift = async (target: "ONLINE" | "OFFLINE") => {
    if (!courier || !commandAvailable || !session || shiftCommand?.kind === "pending") return;
    const idempotencyKey = `courier-shift-${target.toLowerCase()}-${courier.id}-${shiftVersion}`;
    setShiftCommand({ kind: "pending", idempotencyKey });
    const result = await transitionCourierShift({
      session,
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
    if (!courier || !commandAvailable || !session || locationCommand?.kind === "pending") return;
    const observedAt = new Date().toISOString();
    const sequence = (courier.sequence ?? 0) + 1;
    const idempotencyKey = `courier-location-${courier.id}-${observedAt}`;
    setLocationCommand({ kind: "pending", idempotencyKey });
    setLocationCommand(
      await recordCourierLocation({
        session,
        courierId: courier.id,
        latitude: courier.position.y,
        longitude: courier.position.x,
        observedAt,
        sequence,
        online: courier.online ?? courier.status === "available",
        idempotencyKey,
      }),
    );
  };
  return (
    <RolePage
      eyebrow={t("role.courierEyebrow")}
      title={t("role.courierTitle")}
      lede={t("role.courierLede")}
      icon={Bike}
    >
      <section className="content-grid-two">
        <section className="panel">
          {!courier ? (
            <p className="empty-state">{t("role.noCourierSource")}</p>
          ) : (
            <>
              <div className="panel-heading">
                <div>
                  <p className="eyebrow">{t("role.shiftStatus")}</p>
                  <h2>{courier.name}</h2>
                </div>
                <StatusPill
                  status={online === "ONLINE" ? "available" : "offline"}
                  label={online === "ONLINE" ? t("role.online") : t("role.offline")}
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
                      ? `${order.shortId} · ${displayOrderStatus(order.status, locale)}`
                      : t("role.noAssignedTask")}
                  </p>
                </div>
              </div>
              <div className="courier-metrics">
                <div>
                  <span>{t("role.shift")}</span>
                  <strong>{snapshot.source === "live" ? t("role.live") : t("role.fixture")}</strong>
                </div>
                <div>
                  <span>{t("role.distance")}</span>
                  <strong>
                    {snapshot.source === "live" ? t("role.projection") : t("role.fixture")}
                  </strong>
                </div>
                <div>
                  <span>{t("role.location")}</span>
                  <strong>
                    {snapshot.availability === "ready" ? t("role.fresh") : t("role.degraded")}
                  </strong>
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
                  <Bike size={15} /> {t("role.goOnline")}
                </button>
                <button
                  className="button button-secondary"
                  type="button"
                  disabled={
                    !commandAvailable || shiftCommand?.kind === "pending" || online === "OFFLINE"
                  }
                  onClick={() => void submitShift("OFFLINE")}
                >
                  <CircleDot size={15} /> {t("role.goOffline")}
                </button>
                <button
                  className="button button-secondary"
                  type="button"
                  disabled={!commandAvailable || locationCommand?.kind === "pending"}
                  onClick={() => void submitLocation()}
                >
                  <NavigationIcon /> {t("role.sendLocation")}
                </button>
              </div>
            </>
          )}
          {!commandAvailable && (
            <p className="command-note" role="status">
              {snapshot.source === "live"
                ? !session
                  ? t("role.identityRequired", { role: locale === "zh-CN" ? "骑手" : "courier" })
                  : snapshot.availability === "degraded"
                    ? t("role.liveDegradedCommands")
                    : t("role.waitingLiveSnapshot")
                : t("role.writingDisabled")}
            </p>
          )}
          {shiftCommand?.kind === "error" && (
            <div className="command-result command-error" role="alert">
              <strong>{t("role.commandNotAccepted", { code: shiftCommand.code })}</strong>
              <small>
                {t("role.trace")} {shiftCommand.traceId ?? t("role.notReturned")} · {t("role.key")}{" "}
                {shiftCommand.idempotencyKey}
              </small>
            </div>
          )}
          {locationCommand?.kind === "success" && (
            <div className="command-result" role="status">
              <strong>{t("role.locationRecorded", { status: locationCommand.status })}</strong>
              <small>
                {t("role.trace")} {locationCommand.traceId ?? t("role.notReturned")} ·{" "}
                {t("role.key")} {locationCommand.idempotencyKey}
              </small>
            </div>
          )}
        </section>
        <section className="panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">{t("role.nextStop")}</p>
              <h2>{order?.shortId ?? t("role.noActiveRoute")}</h2>
            </div>
            <Route size={18} className="heading-icon" />
          </div>
          {!order ? (
            <p className="empty-state">{t("role.noActiveRouteSource")}</p>
          ) : (
            <div className="next-stop">
              <div className="stop-icon">
                <NavigationIcon />
              </div>
              <div>
                <strong>{order.destination}</strong>
                <p>
                  {order.customerName} · {t("ops.eta")} {order.eta}
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
              {command?.kind === "pending" ? t("role.submitting") : nextCommand.label}
            </button>
          )}
          {command?.kind === "success" && (
            <div className="command-result" role="status">
              <strong>
                {command.replayed ? t("role.replayAcknowledged") : t("role.courierAccepted")}
              </strong>
              <span>
                {command.orderId} · {command.status} · version {command.version}
              </span>
              <small>
                {t("role.trace")} {command.traceId ?? t("role.notReturned")} · {t("role.key")}{" "}
                {command.idempotencyKey}
              </small>
            </div>
          )}
          {command?.kind === "error" && (
            <div className="command-result command-error" role="alert">
              <strong>{t("role.commandNotAccepted", { code: command.code })}</strong>
              <small>
                {t("role.trace")} {command.traceId ?? t("role.notReturned")} · {t("role.key")}{" "}
                {command.idempotencyKey}
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
