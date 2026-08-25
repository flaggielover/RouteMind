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
import { useState } from "react";
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

export function StrategyView({ snapshot }: { snapshot: OperationsSnapshot }) {
  const [registryOpen, setRegistryOpen] = useState(false);
  const [comparison, setComparison] = useState<Awaited<
    ReturnType<typeof whatIfDataSource.run>
  > | null>(null);
  const strategyAvailable =
    snapshot.availability === "ready" && snapshot.dispatch.strategy !== "unavailable";
  const activeStrategy = snapshot.dispatch.strategy;
  const assignedOrders = snapshot.orders.filter((candidate) =>
    ["ASSIGNED", "ACCEPTED", "ARRIVED", "PICKED_UP", "OUT_FOR_DELIVERY", "DELIVERED"].includes(
      candidate.status,
    ),
  ).length;
  const assignmentSignal =
    snapshot.orders.length > 0
      ? `${assignedOrders}/${snapshot.orders.length} assigned`
      : "Not recorded";
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
              <h2>{activeStrategy}</h2>
            </div>
            <StatusPill
              status={strategyAvailable ? "healthy" : "unavailable"}
              label={strategyAvailable ? "Registered" : "Unavailable"}
            />
          </div>
          <div className="strategy-score">
            <span>Recorded assignment signal</span>
            <strong>{assignmentSignal}</strong>
            <small>Quality and baseline deltas require a recorded comparison run.</small>
          </div>
          <dl className="detail-list">
            <div>
              <dt>Version</dt>
              <dd>{snapshot.dispatch.version}</dd>
            </div>
            <div>
              <dt>Last decision</dt>
              <dd>{strategyAvailable ? `${snapshot.dispatch.latencyMs} ms` : "Unavailable"}</dd>
            </div>
            <div>
              <dt>Shadow mode</dt>
              <dd>Not recorded</dd>
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
              <strong>{activeStrategy}</strong>
              <small>{snapshot.dispatch.version} · active policy</small>
            </span>
            <span className="muted-label">
              {strategyAvailable ? "Current policy" : "No active policy"}
            </span>
            <StatusPill
              status={strategyAvailable ? "healthy" : "unavailable"}
              label={strategyAvailable ? "Registered" : "Not available"}
            />
          </div>
          <div className="strategy-row">
            <span>
              <strong>nearest</strong>
              <small>v1.0.0 · baseline</small>
            </span>
            <span className="muted-label">No recorded run</span>
            <StatusPill status="checking" label="Reference only" />
          </div>
          <button
            className="text-button"
            type="button"
            aria-expanded={registryOpen}
            aria-controls="strategy-registry"
            onClick={() => setRegistryOpen((open) => !open)}
          >
            {registryOpen ? "Hide strategy registry" : "Open strategy registry"}{" "}
            <ArrowUpRight size={14} />
          </button>
          {registryOpen && (
            <div
              className="strategy-registry"
              id="strategy-registry"
              role="region"
              aria-label="Strategy registry"
            >
              <p className="panel-subtitle">Registered locally for this control surface.</p>
              <ul>
                <li>
                  <strong>weighted-greedy</strong>
                  <span>v1.0.0 · active</span>
                </li>
                <li>
                  <strong>nearest</strong>
                  <span>v1.0.0 · baseline</span>
                </li>
              </ul>
            </div>
          )}
        </section>
      </section>
      <WhatIfComparisonPanel onRun={(variant) => whatIfDataSource.run(variant)} />
      <StrategyComparisonPanel
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
  const order = snapshot.orders[0];
  const courier = snapshot.couriers[0];
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
      ? "Live tracking"
      : realtime.status === "disabled"
        ? "Tracking paused"
        : "Tracking degraded";

  const submitOrder = async () => {
    if (!commandAvailable || !session || command?.kind === "pending") return;
    setCommand({ kind: "pending", idempotencyKey });
    const result = await createCustomerOrder({ session, idempotencyKey });
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
          {!courier ? (
            <p className="empty-state">No courier is available in the selected source.</p>
          ) : (
            <>
              <div className="panel-heading">
                <div>
                  <p className="eyebrow">Courier</p>
                  <h2>{courier.name}</h2>
                </div>
                <Bike size={18} className="heading-icon" />
              </div>
              <div className="courier-card">
                <div className="avatar">{courier.name.slice(0, 2).toUpperCase()}</div>
                <div>
                  <strong>{order ? orderStatusLabel[order.status] : "No active order"}</strong>
                  <p>
                    {courier.zone} · {courier.status.replace("_", " ")}
                  </p>
                </div>
              </div>
            </>
          )}
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
                  ? !session
                    ? "A verified customer identity is required for commands."
                    : snapshot.availability === "degraded"
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

export function MerchantView({
  snapshot,
  session,
}: {
  snapshot: OperationsSnapshot;
  session?: TenantSession | null;
}) {
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
            <StatusPill
              status={queueStatus}
              label={
                queueStatus === "unavailable"
                  ? "Unavailable"
                  : queueStatus === "busy"
                    ? "Busy"
                    : "Ready"
              }
            />
          </div>
          <div className="merchant-stats">
            <div>
              <strong>{ordersInPrep ?? "Unavailable"}</strong>
              <span>orders in prep</span>
            </div>
            <div>
              <strong>{prepMinutes > 0 ? `${prepMinutes}m` : "Unavailable"}</strong>
              <span>avg prep time</span>
            </div>
            <div>
              <strong>{handoffsNext ?? "Unavailable"}</strong>
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
              <h2>{order?.shortId ?? "No active handoff"}</h2>
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
                ? !session
                  ? "A verified merchant identity is required for commands."
                  : snapshot.availability === "degraded"
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

export function CourierView({
  snapshot,
  session,
}: {
  snapshot: OperationsSnapshot;
  session?: TenantSession | null;
}) {
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
                ? !session
                  ? "A verified courier identity is required for commands."
                  : snapshot.availability === "degraded"
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
