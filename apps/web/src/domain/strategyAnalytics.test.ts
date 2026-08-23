import { describe, expect, it } from "vitest";
import type { WhatIfComparison } from "./model";
import { projectStrategyAnalytics } from "./strategyAnalytics";

const comparison: WhatIfComparison = {
  source: "what-if",
  claimLabel: "scenario comparison; not a causal production claim",
  recordedRunId: "run-1",
  comparisonDigest: "digest",
  scenarioId: "scenario-1",
  seed: 7,
  results: [
    {
      variantId: "baseline",
      label: "nearest baseline",
      strategy: "nearest",
      strategyVersion: "1.0.0",
      requestCount: 2,
      assignedCount: 2,
      assignmentRate: 1,
      simulatedEndTick: 2,
      simulatedDurationSeconds: 120,
      riskIndex: 1,
      replayDigest: "replay-a",
      manifestDigest: "manifest-a",
      outputDigest: "output-a",
      observedRuntimeMillis: 2,
    },
    {
      variantId: "candidate",
      label: "weighted candidate",
      strategy: "weighted-greedy",
      strategyVersion: "1.0.0",
      requestCount: 2,
      assignedCount: 2,
      assignmentRate: 1,
      simulatedEndTick: 1,
      simulatedDurationSeconds: 60,
      riskIndex: 0.5,
      replayDigest: "replay-b",
      manifestDigest: "manifest-b",
      outputDigest: "output-b",
      observedRuntimeMillis: 1,
    },
  ],
};

describe("strategy analytics projection", () => {
  it("computes a Pareto frontier from recorded metrics", () => {
    const projection = projectStrategyAnalytics(comparison);

    expect(projection.frontier).toEqual(["weighted-greedy"]);
    expect(projection.points[0]).toMatchObject({
      pareto: false,
      dominatedBy: ["weighted-greedy"],
    });
    expect(projection.metadata[1]).toMatchObject({
      name: "weighted-greedy",
      maturity: "BASELINE",
      fallback: { strategy: "nearest", available: true },
    });
    expect(projection.metadata[1].parameters[0]).toMatchObject({
      key: "distance_weight",
      constraint: ">= 0.000001",
    });
  });

  it("keeps unsupported metrics explicit", () => {
    expect(projectStrategyAnalytics(comparison).unavailableMetrics).toEqual(
      expect.arrayContaining(["Fairness", "Cost", "Per-result verification report"]),
    );
  });
});
