import type { WhatIfComparison, WhatIfMetric } from "./model";

export type StrategyMaturity =
  "BASELINE" | "ENGINEERING" | "PRODUCTION-CANDIDATE" | "RESEARCH" | "EXTERNAL-VALIDATED";

export interface StrategyParameterDescriptor {
  key: string;
  defaultValue: string;
  constraint: string;
}

export interface StrategyMetadata {
  name: string;
  version: string;
  maturity: StrategyMaturity;
  capabilities: readonly string[];
  parameters: readonly StrategyParameterDescriptor[];
  constraints: readonly string[];
  fallback: {
    strategy: string;
    available: boolean;
    detail: string;
  };
  verification: {
    status: "boundary-verified" | "unavailable";
    detail: string;
  };
}

export interface StrategyAnalyticsPoint {
  metric: WhatIfMetric;
  pareto: boolean;
  dominatedBy: readonly string[];
}

export interface StrategyAnalyticsProjection {
  source: "recorded-comparison";
  claimLabel: WhatIfComparison["claimLabel"];
  recordedRunId: string;
  scenarioId: string;
  seed: number;
  metadata: readonly StrategyMetadata[];
  points: readonly StrategyAnalyticsPoint[];
  frontier: readonly string[];
  objective: string;
  unavailableMetrics: readonly string[];
  summary: string;
}

const REGISTRY_METADATA: Readonly<Record<string, Omit<StrategyMetadata, "name" | "version">>> = {
  nearest: {
    maturity: "BASELINE",
    capabilities: ["dispatch"],
    parameters: [],
    constraints: ["eligible candidates only", "deterministic distance then courier-id tie break"],
    fallback: {
      strategy: "nearest",
      available: true,
      detail: "Default deterministic fallback at the compute boundary",
    },
    verification: {
      status: "boundary-verified",
      detail: "DispatchDecision is checked by the independent compute verifier",
    },
  },
  "weighted-greedy": {
    maturity: "BASELINE",
    capabilities: ["dispatch"],
    parameters: [{ key: "distance_weight", defaultValue: "1.0", constraint: ">= 0.000001" }],
    constraints: ["eligible candidates only", "distance weight must be finite and positive"],
    fallback: {
      strategy: "nearest",
      available: true,
      detail: "Nearest is available when a strategy execution fails",
    },
    verification: {
      status: "boundary-verified",
      detail: "DispatchDecision is checked by the independent compute verifier",
    },
  },
  hungarian: {
    maturity: "BASELINE",
    capabilities: ["dispatch", "batch-assignment"],
    parameters: [],
    constraints: ["bounded bipartite assignment", "eligible candidates only"],
    fallback: {
      strategy: "nearest",
      available: true,
      detail: "Nearest is available when a strategy execution fails",
    },
    verification: {
      status: "boundary-verified",
      detail: "DispatchDecision is checked by the independent compute verifier",
    },
  },
  "risk-aware": {
    maturity: "BASELINE",
    capabilities: ["dispatch", "risk-scoring"],
    parameters: [
      { key: "distance", defaultValue: "1.0", constraint: ">= 0" },
      { key: "readiness", defaultValue: "0.5", constraint: ">= 0" },
      { key: "overtime", defaultValue: "2.0", constraint: ">= 0" },
      { key: "service_risk", defaultValue: "2.0", constraint: ">= 0" },
      { key: "balance", defaultValue: "0.5", constraint: ">= 0" },
    ],
    constraints: ["eligible candidates only", "weights must be non-negative and not all zero"],
    fallback: {
      strategy: "nearest",
      available: true,
      detail: "Nearest is available when a strategy execution fails",
    },
    verification: {
      status: "boundary-verified",
      detail: "DispatchDecision is checked by the independent compute verifier",
    },
  },
  "minimum-cost-flow": {
    maturity: "ENGINEERING",
    capabilities: ["dispatch", "batch-assignment"],
    parameters: [],
    constraints: ["bounded flow graph", "non-negative candidate capacities"],
    fallback: {
      strategy: "nearest",
      available: true,
      detail: "Nearest is available when a strategy execution fails",
    },
    verification: {
      status: "boundary-verified",
      detail: "DispatchDecision is checked by the independent compute verifier",
    },
  },
  "partitioned-assignment": {
    maturity: "ENGINEERING",
    capabilities: ["dispatch", "partitioned-assignment"],
    parameters: [],
    constraints: ["bounded partitions", "each partition must retain eligible candidates"],
    fallback: {
      strategy: "nearest",
      available: true,
      detail: "Nearest is available when a strategy execution fails",
    },
    verification: {
      status: "boundary-verified",
      detail: "DispatchDecision is checked by the independent compute verifier",
    },
  },
  vrptw: {
    maturity: "BASELINE",
    capabilities: ["dispatch", "time-window"],
    parameters: [],
    constraints: ["bounded insertion heuristic", "time windows must be feasible"],
    fallback: {
      strategy: "nearest",
      available: true,
      detail: "Nearest is available when a strategy execution fails",
    },
    verification: {
      status: "boundary-verified",
      detail: "DispatchDecision is checked by the independent compute verifier",
    },
  },
};

const UNAVAILABLE_METRICS = [
  "Fairness",
  "Cost",
  "Completion",
  "Overtime",
  "Distance",
  "Per-result verification report",
] as const;

export function projectStrategyAnalytics(
  comparison: WhatIfComparison,
): StrategyAnalyticsProjection {
  const points = comparison.results.map((metric) => ({ metric, pareto: false, dominatedBy: [] }));
  const computed = points.map((point, index) => {
    const dominators = points
      .filter((_, candidateIndex) => candidateIndex !== index)
      .filter((candidate) => dominates(candidate.metric, point.metric))
      .map((candidate) => candidate.metric.strategy);
    return { ...point, pareto: dominators.length === 0, dominatedBy: dominators };
  });
  const metadata = comparison.results.map((result) => metadataFor(result));
  const frontier = computed.filter((point) => point.pareto).map((point) => point.metric.strategy);
  const distinctFrontier = [...new Set(frontier)];
  return {
    source: "recorded-comparison",
    claimLabel: comparison.claimLabel,
    recordedRunId: comparison.recordedRunId,
    scenarioId: comparison.scenarioId,
    seed: comparison.seed,
    metadata,
    points: computed,
    frontier: distinctFrontier,
    objective: "Coverage maximize; simulated duration, runtime, and risk minimize",
    unavailableMetrics: UNAVAILABLE_METRICS,
    summary:
      computed.length === 0
        ? "No recorded strategy results are available for Pareto computation."
        : `${distinctFrontier.length} of ${computed.length} recorded results are on the computed Pareto frontier.`,
  };
}

function metadataFor(metric: WhatIfMetric): StrategyMetadata {
  const known = REGISTRY_METADATA[metric.strategy] ?? REGISTRY_METADATA.nearest;
  return {
    name: metric.strategy,
    version: metric.strategyVersion,
    ...known,
  };
}

function dominates(candidate: WhatIfMetric, other: WhatIfMetric): boolean {
  const noWorse =
    candidate.assignmentRate >= other.assignmentRate &&
    candidate.simulatedDurationSeconds <= other.simulatedDurationSeconds &&
    candidate.observedRuntimeMillis <= other.observedRuntimeMillis &&
    candidate.riskIndex <= other.riskIndex;
  const strictlyBetter =
    candidate.assignmentRate > other.assignmentRate ||
    candidate.simulatedDurationSeconds < other.simulatedDurationSeconds ||
    candidate.observedRuntimeMillis < other.observedRuntimeMillis ||
    candidate.riskIndex < other.riskIndex;
  return noWorse && strictlyBetter;
}
