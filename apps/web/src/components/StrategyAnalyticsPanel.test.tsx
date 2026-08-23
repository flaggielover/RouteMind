import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { StrategyAnalyticsPanel } from "./StrategyAnalyticsPanel";
import type { WhatIfComparison } from "../domain/model";

const comparison: WhatIfComparison = {
  source: "what-if",
  claimLabel: "scenario comparison; not a causal production claim",
  recordedRunId: "run-analytics",
  comparisonDigest: "digest",
  scenarioId: "control-default",
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

describe("Strategy analytics panel", () => {
  it("renders computed frontier, metadata, fallback, and unavailable inventory", () => {
    render(<StrategyAnalyticsPanel comparison={comparison} />);

    expect(
      screen.getByText("1 of 2 recorded results are on the computed Pareto frontier."),
    ).toBeInTheDocument();
    expect(screen.getByText("compute registry contract")).toBeInTheDocument();
    expect(screen.getByText("distance_weight=1.0")).toBeInTheDocument();
    expect(screen.getAllByText("nearest available").length).toBeGreaterThan(0);
    expect(screen.getByText("Fairness")).toBeInTheDocument();
    expect(screen.getByText("Pareto frontier")).toBeInTheDocument();
    expect(screen.getByText("Dominated by weighted-greedy")).toBeInTheDocument();
  });

  it("shows the empty state before a comparison is recorded", () => {
    render(<StrategyAnalyticsPanel comparison={null} />);
    expect(
      screen.getByText("Run a recorded comparison to compute strategy analytics."),
    ).toBeInTheDocument();
  });
});
