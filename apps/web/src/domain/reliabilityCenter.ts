import type { OperationsSnapshot, ServiceHealth } from "./model";
import type { RealtimeConnectionState } from "../data/realtime";

export type ReliabilityStatus = "healthy" | "degraded" | "unavailable" | "fixture";
export type ReliabilityCheckStatus = "passed" | "failed" | "unavailable" | "fixture";

export interface ReliabilityTimelineEvent {
  at: string;
  label: string;
  status: ReliabilityCheckStatus;
  detail: string;
  traceId: string | null;
}

export interface ReliabilityInvariant {
  name: string;
  status: ReliabilityCheckStatus;
  inspected: number | null;
  evidence: string;
  traceId: string | null;
}

export interface ReliabilityDependency {
  label: string;
  status: ReliabilityCheckStatus;
  detail: string;
  endpoint: string;
  checkedAt: string;
}

export interface ReliabilityRecoveryEvidence {
  label: string;
  status: ReliabilityCheckStatus;
  detail: string;
  traceId: string | null;
}

export interface ReliabilityCenterProjection {
  status: ReliabilityStatus;
  sourceLabel: string;
  statusDetail: string;
  generatedAt: string;
  timeline: readonly ReliabilityTimelineEvent[];
  invariants: readonly ReliabilityInvariant[];
  dependencies: readonly ReliabilityDependency[];
  recovery: readonly ReliabilityRecoveryEvidence[];
  traceId: string | null;
}

export function projectReliabilityCenter(
  snapshot: OperationsSnapshot,
  health: readonly ServiceHealth[],
  realtime: RealtimeConnectionState,
): ReliabilityCenterProjection {
  const traceId = snapshot.decisionLedger?.requestId ?? null;
  const dependencyChecks = health.length
    ? health.map((item) => ({
        label: item.label,
        status: dependencyStatus(snapshot.source, item.status),
        detail: item.detail,
        endpoint: item.endpoint,
        checkedAt: item.checkedAt,
      }))
    : [
        {
          label: "Service health",
          status: snapshot.source === "demo" ? ("fixture" as const) : ("unavailable" as const),
          detail:
            snapshot.source === "demo"
              ? "Health telemetry is not recorded for the demo fixture."
              : "No service health response is attached to this snapshot.",
          endpoint: "unavailable",
          checkedAt: "",
        },
      ];
  const staleCouriers = snapshot.couriers.filter((courier) => courier.stale).length;
  const snapshotStatus: ReliabilityCheckStatus =
    snapshot.source === "demo" || snapshot.source === "replay"
      ? "fixture"
      : snapshot.availability === "ready"
        ? "passed"
        : snapshot.availability === "degraded"
          ? "failed"
          : "unavailable";
  const invariants: ReliabilityInvariant[] = [
    {
      name: "Durable operations snapshot",
      status: snapshotStatus,
      inspected: snapshot.orders.length + snapshot.couriers.length,
      evidence:
        snapshot.source === "live"
          ? `${snapshot.orders.length} orders and ${snapshot.couriers.length} couriers attached`
          : "Source is a labeled fixture; durable truth is not asserted",
      traceId,
    },
    {
      name: "Dispatch decision linkage",
      status:
        snapshot.dispatch.selectedCourier !== "-" && snapshot.dispatch.strategy !== "unavailable"
          ? snapshot.source === "demo" || snapshot.source === "replay"
            ? "fixture"
            : "passed"
          : "unavailable",
      inspected: snapshot.dispatch.selectedCourier === "-" ? null : 1,
      evidence: snapshot.decisionLedger
        ? `Ledger request ${snapshot.decisionLedger.requestId} links the decision`
        : "No durable decision trace is attached to this snapshot",
      traceId,
    },
    {
      name: "Courier freshness",
      status:
        snapshot.couriers.length === 0
          ? "unavailable"
          : staleCouriers > 0
            ? "failed"
            : snapshot.source === "demo" || snapshot.source === "replay"
              ? "fixture"
              : "passed",
      inspected: snapshot.couriers.length,
      evidence:
        staleCouriers > 0
          ? `${staleCouriers} courier${staleCouriers === 1 ? "" : "s"} marked stale`
          : snapshot.couriers.length
            ? "No stale courier flag is present in the captured source"
            : "Courier telemetry unavailable",
      traceId: null,
    },
    {
      name: "Continuous reconciliation",
      status: "unavailable",
      inspected: null,
      evidence: "Latest Java detect-only reconciliation report is not attached to this projection",
      traceId: null,
    },
  ];
  const status = overallStatus(snapshot, health, realtime);
  const timeline: ReliabilityTimelineEvent[] = [
    {
      at: snapshot.generatedAt,
      label: "Operational snapshot",
      status: snapshotStatus,
      detail: timelineSnapshotDetail(snapshot),
      traceId,
    },
    {
      at: latestCheckedAt(health) || snapshot.generatedAt,
      label: "Dependency checks",
      status: dependencyChecks.some((item) => item.status === "failed")
        ? "failed"
        : dependencyChecks.some((item) => item.status === "unavailable")
          ? "unavailable"
          : dependencyChecks.some((item) => item.status === "fixture")
            ? "fixture"
            : "passed",
      detail: `${dependencyChecks.length} dependency record${dependencyChecks.length === 1 ? "" : "s"} inspected`,
      traceId: null,
    },
    {
      at: snapshot.generatedAt,
      label: "Realtime stream",
      status: realtimeStatus(snapshot.source, realtime.status),
      detail: timelineRealtimeDetail(snapshot.source, realtime),
      traceId: null,
    },
  ];
  const recovery: ReliabilityRecoveryEvidence[] = [
    {
      label: "Refresh boundary",
      status: health.length ? "passed" : snapshot.source === "demo" ? "fixture" : "unavailable",
      detail: health.length
        ? "Health refresh is available through the bounded operator action"
        : "No refresh response is recorded for this source",
      traceId: null,
    },
    {
      label: "Stream recovery",
      status: realtimeStatus(snapshot.source, realtime.status),
      detail:
        realtime.status === "connected"
          ? `${realtime.appliedEvents} event${realtime.appliedEvents === 1 ? "" : "s"} applied since connect`
          : "Stream recovery state is recorded above; inspect the cursor boundary before resuming operations.",
      traceId: null,
    },
    {
      label: "Autonomous remediation",
      status: "unavailable",
      detail: "Not permitted by the read-only Reliability Center boundary",
      traceId: null,
    },
  ];
  return {
    status,
    sourceLabel:
      snapshot.source === "live"
        ? "LIVE reliability"
        : `${snapshot.source.toUpperCase()} fixture reliability`,
    statusDetail: statusDetail(status),
    generatedAt: snapshot.generatedAt,
    timeline,
    invariants,
    dependencies: dependencyChecks,
    recovery,
    traceId,
  };
}

function dependencyStatus(
  source: OperationsSnapshot["source"],
  status: ServiceHealth["status"],
): ReliabilityCheckStatus {
  if (source === "demo" || source === "replay") return "fixture";
  return status === "healthy" ? "passed" : status === "unavailable" ? "unavailable" : "unavailable";
}

function realtimeStatus(
  source: OperationsSnapshot["source"],
  status: RealtimeConnectionState["status"],
): ReliabilityCheckStatus {
  if (source !== "live") return "fixture";
  if (status === "connected") return "passed";
  if (status === "degraded" || status === "stale") return "failed";
  return "unavailable";
}

function overallStatus(
  snapshot: OperationsSnapshot,
  health: readonly ServiceHealth[],
  realtime: RealtimeConnectionState,
): ReliabilityStatus {
  if (snapshot.source === "demo" || snapshot.source === "replay") return "fixture";
  if (
    snapshot.availability === "unavailable" ||
    health.some((item) => item.status === "unavailable")
  ) {
    return "unavailable";
  }
  if (
    snapshot.availability === "degraded" ||
    health.some((item) => item.status !== "healthy") ||
    realtime.status === "degraded" ||
    realtime.status === "stale"
  ) {
    return "degraded";
  }
  return "healthy";
}

function latestCheckedAt(health: readonly ServiceHealth[]): string {
  return (
    [...health].sort((left, right) => right.checkedAt.localeCompare(left.checkedAt))[0]
      ?.checkedAt ?? ""
  );
}

function statusDetail(status: ReliabilityStatus): string {
  if (status === "fixture") return "Fixture evidence is inspectable; live health is not claimed.";
  if (status === "unavailable")
    return "Source unavailable; inspect dependency records for the current detail.";
  if (status === "degraded")
    return "Source degraded; inspect courier freshness and stream records for the current detail.";
  return "All attached live dependency checks and stream state are healthy.";
}

function timelineSnapshotDetail(snapshot: OperationsSnapshot): string {
  if (snapshot.availability === "unavailable") {
    return "Snapshot unavailable; source detail is retained in the operational status above.";
  }
  if (snapshot.availability === "degraded") {
    return "Snapshot degraded; inspect the freshness and stream entries below for bounded evidence.";
  }
  return snapshot.source === "demo" || snapshot.source === "replay"
    ? "Fixture snapshot captured; live durability is not asserted."
    : "Operational snapshot captured from the attached live source.";
}

function timelineRealtimeDetail(
  source: OperationsSnapshot["source"],
  realtime: RealtimeConnectionState,
): string {
  if (source !== "live") return "Realtime is intentionally disabled for this labeled source.";
  if (realtime.status === "connected") {
    return `${realtime.appliedEvents} event${realtime.appliedEvents === 1 ? "" : "s"} applied since connect.`;
  }
  return "Stream state is degraded or unavailable; inspect the bounded cursor evidence above.";
}
