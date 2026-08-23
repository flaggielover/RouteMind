import type { Courier, OperationsSnapshot } from "./model";

export type DecisionXrayAuthority = "durable-ledger" | "snapshot-projection";
export type DecisionXrayReplayStatus = "match" | "changed" | "not-captured";

export interface DecisionXrayCandidate {
  courierId: string;
  status: Courier["status"];
  zone: string;
  eligibility: "selected" | "eligible" | "rejected";
  rejectionReasons: readonly string[];
  travelSeconds: number | null;
}

export interface DecisionXrayProjection {
  authority: DecisionXrayAuthority;
  decisionId: string;
  sourceLabel: string;
  sourceDetail: string;
  generatedAt: string;
  provenance: {
    requestId: string;
    referenceDataId: string;
    clockDomain: OperationsSnapshot["clockDomain"];
    recordedAt: string;
  };
  candidates: readonly DecisionXrayCandidate[];
  travel: {
    status: "recorded" | "unavailable";
    summary: string;
    evidence: string;
  };
  objective: {
    label: string;
    value: number | null;
    unit: string;
    evidence: string;
  };
  risk: {
    level: "low" | "medium" | "high" | "unavailable";
    score: number | null;
    evidence: string;
  };
  selectedAction: {
    courierId: string;
    strategy: string;
    strategyVersion: string;
    rationale: string;
  };
  alternatives: readonly string[];
  verification: {
    status: "passed" | "warning" | "unavailable";
    checks: readonly string[];
    summary: string;
  };
  digests: {
    decision: string;
    input: string | null;
    output: string | null;
    inputSnapshot: string | null;
    outputSnapshot: string | null;
  };
  replay: {
    bounded: boolean;
    status: DecisionXrayReplayStatus;
    capturedDigest: string | null;
    replayedDigest: string | null;
    summary: string;
  };
  summary: string;
}

const SOURCE_LABELS: Record<OperationsSnapshot["source"], string> = {
  live: "LIVE source",
  demo: "DEMO source",
  replay: "REPLAY source",
  simulation: "SIMULATION source",
};

export function projectDecisionXray(
  snapshot: OperationsSnapshot,
  replayedSnapshot: OperationsSnapshot = snapshot,
): DecisionXrayProjection {
  const ledger = snapshot.decisionLedger;
  const candidates = snapshot.couriers
    .map((courier) => candidate(courier, snapshot.dispatch.selectedCourier))
    .sort((left, right) => left.courierId.localeCompare(right.courierId));
  const selected = candidates.find((item) => item.eligibility === "selected");
  const eligible = candidates.filter(
    (item) =>
      item.eligibility === "eligible" ||
      (item.eligibility === "selected" && item.rejectionReasons.length === 0),
  );
  const selectedCourier = snapshot.dispatch.selectedCourier;
  const priorityOrders = snapshot.orders.filter((order) => order.priority === "priority").length;
  const supplyGap = Math.max(0, priorityOrders - eligible.length);
  const riskScore = priorityOrders ? Math.min(1, supplyGap / priorityOrders) : null;
  const decisionPayload = decisionPayloadFor(snapshot);
  const replayComparison = compareDecisionXrayReplay(snapshot, replayedSnapshot);
  const verificationChecks = [
    ledger
      ? "Durable Java ledger record is attached"
      : "Using read-only snapshot projection; ledger record not attached",
    selectedCourier !== "-" && selectedCourier.length > 0
      ? "Selected courier identifier is present"
      : "Selected courier identifier is unavailable",
    selected
      ? "Selected courier is represented in the captured candidates"
      : "Selected courier is not represented in candidates",
    "Clock domain is explicit (" + snapshot.clockDomain + ")",
  ];
  const verificationStatus =
    selected && selected.rejectionReasons.length === 0 && snapshot.availability !== "unavailable"
      ? "passed"
      : "warning";
  const decisionId = ledger?.decisionId ?? "snapshot:" + decisionPayload.digest.slice(0, 16);
  const authority: DecisionXrayAuthority = ledger ? "durable-ledger" : "snapshot-projection";
  const travelRecorded = Boolean(ledger?.inputSnapshotJson?.includes("travel"));
  const riskLevel =
    riskScore === null
      ? "unavailable"
      : riskScore >= 0.66
        ? "high"
        : riskScore > 0
          ? "medium"
          : "low";
  const alternatives = candidates
    .filter((item) => item.courierId !== selectedCourier && item.eligibility !== "rejected")
    .slice(0, 3)
    .map((item) => item.courierId);
  const summary = selected
    ? snapshot.dispatch.strategy +
      " v" +
      snapshot.dispatch.version +
      " selected " +
      selectedCourier +
      "; " +
      eligible.length +
      " of " +
      candidates.length +
      " captured candidates remain eligible. " +
      (travelRecorded
        ? "Recorded travel evidence is attached."
        : "Travel time is unavailable from this snapshot.")
    : "No selected courier can be verified from this " +
      snapshot.source +
      " snapshot; the read-only projection is incomplete.";

  return {
    authority,
    decisionId,
    sourceLabel: SOURCE_LABELS[snapshot.source],
    sourceDetail: snapshot.sourceDetail,
    generatedAt: snapshot.generatedAt,
    provenance: {
      requestId: ledger?.requestId ?? "snapshot-request-unavailable",
      referenceDataId: ledger?.referenceDataId ?? "reference-data-unavailable",
      clockDomain: snapshot.clockDomain,
      recordedAt: ledger?.createdAt ?? snapshot.generatedAt,
    },
    candidates,
    travel: {
      status: travelRecorded ? "recorded" : "unavailable",
      summary: travelRecorded
        ? "Travel evidence is present in the captured ledger snapshot."
        : "No provider travel metric is present; no travel duration is inferred.",
      evidence: travelRecorded ? "ledger.inputSnapshotJson" : "snapshot.courier.position only",
    },
    objective: {
      label: "Priority coverage",
      value: priorityOrders
        ? Number(((priorityOrders - supplyGap) / priorityOrders).toFixed(2))
        : null,
      unit: "covered priority orders",
      evidence:
        priorityOrders +
        " priority orders / " +
        eligible.length +
        " eligible couriers in captured snapshot",
    },
    risk: {
      level: riskLevel,
      score: riskScore,
      evidence: priorityOrders
        ? "Supply gap proxy: " + supplyGap + " priority orders without an eligible courier."
        : "No priority-order denominator is present.",
    },
    selectedAction: {
      courierId: selectedCourier,
      strategy: ledger?.strategy ?? snapshot.dispatch.strategy,
      strategyVersion: ledger?.strategyVersion ?? snapshot.dispatch.version,
      rationale: snapshot.dispatch.rationale,
    },
    alternatives,
    verification: {
      status: verificationStatus,
      checks: verificationChecks,
      summary: selected
        ? "Selection is structurally verifiable from the captured records."
        : "Selection cannot be fully verified from the captured records.",
    },
    digests: {
      decision: ledger?.outputDigest ?? decisionPayload.digest,
      input: ledger?.inputDigest ?? null,
      output: ledger?.outputDigest ?? null,
      inputSnapshot: ledger?.inputSnapshotDigest ?? null,
      outputSnapshot: ledger?.outputSnapshotDigest ?? null,
    },
    replay: replayComparison,
    summary,
  };
}

export function compareDecisionXrayReplay(
  captured: OperationsSnapshot,
  replayed: OperationsSnapshot,
): DecisionXrayProjection["replay"] {
  const capturedDigest = decisionPayloadFor(captured).digest;
  const replayedDigest = decisionPayloadFor(replayed).digest;
  const capturedRun = Boolean(captured.replay?.replayDigest || captured.simulation?.replayDigest);
  if (!capturedRun) {
    return {
      bounded: true,
      status: "not-captured",
      capturedDigest,
      replayedDigest: null,
      summary: "No replay or simulation artifact is attached to this snapshot.",
    };
  }
  return {
    bounded: true,
    status: capturedDigest === replayedDigest ? "match" : "changed",
    capturedDigest,
    replayedDigest,
    summary:
      capturedDigest === replayedDigest
        ? "Bounded replay reproduced the captured decision digest."
        : "Bounded replay changed the decision digest; inspect captured inputs before relying on the result.",
  };
}

function candidate(courier: Courier, selectedCourier: string): DecisionXrayCandidate {
  const rejectionReasons: string[] = [];
  if (courier.status === "offline" || courier.online === false)
    rejectionReasons.push("courier is offline");
  if (courier.status === "on_route") rejectionReasons.push("courier is already on route");
  if (courier.stale === true) rejectionReasons.push("courier location is stale");
  const rejected = rejectionReasons.length > 0;
  return {
    courierId: courier.id,
    status: courier.status,
    zone: courier.zone,
    eligibility: courier.id === selectedCourier ? "selected" : rejected ? "rejected" : "eligible",
    rejectionReasons,
    travelSeconds: null,
  };
}

function decisionPayloadFor(snapshot: OperationsSnapshot): { digest: string } {
  return {
    digest: stableDigest({
      source: snapshot.source,
      clockDomain: snapshot.clockDomain,
      dispatch: snapshot.dispatch,
      orders: snapshot.orders.map((order) => ({
        id: order.id,
        priority: order.priority,
        status: order.status,
      })),
      couriers: snapshot.couriers.map((courier) => ({
        id: courier.id,
        status: courier.status,
        zone: courier.zone,
        stale: courier.stale,
        online: courier.online,
      })),
    }),
  };
}

function stableDigest(value: unknown): string {
  const encoded = canonicalJson(value);
  let hash = 2166136261;
  for (const character of encoded) hash = Math.imul(hash ^ character.charCodeAt(0), 16777619);
  return (hash >>> 0).toString(16).padStart(8, "0").repeat(8);
}

function canonicalJson(value: unknown): string {
  if (Array.isArray(value)) return "[" + value.map(canonicalJson).join(",") + "]";
  if (value && typeof value === "object") {
    return (
      "{" +
      Object.entries(value as Record<string, unknown>)
        .sort(([left], [right]) => left.localeCompare(right))
        .map(([key, item]) => JSON.stringify(key) + ":" + canonicalJson(item))
        .join(",") +
      "}"
    );
  }
  return JSON.stringify(value);
}
