import userEvent from "@testing-library/user-event";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { StrategyComparisonPanel } from "./StrategyComparisonPanel";
import type { WhatIfComparison } from "../domain/model";

const comparison: WhatIfComparison = {
  source: "what-if",
  claimLabel: "scenario comparison; not a causal production claim",
  recordedRunId: "replay-control-default-v1",
  comparisonDigest: "comparison-digest",
  scenarioId: "control-default",
  seed: 7,
  results: [
    {
      variantId: "baseline",
      label: "Recorded baseline",
      strategy: "nearest",
      strategyVersion: "1.0.0",
      requestCount: 2,
      assignedCount: 2,
      assignmentRate: 1,
      simulatedEndTick: 1,
      simulatedDurationSeconds: 60,
      riskIndex: 0,
      replayDigest: "baseline-replay",
      manifestDigest: "baseline-manifest",
      outputDigest: "baseline-output",
      observedRuntimeMillis: 1.2,
    },
    {
      variantId: "strategy-weighted-greedy",
      label: "weighted-greedy candidate",
      strategy: "weighted-greedy",
      strategyVersion: "1.0.0",
      requestCount: 2,
      assignedCount: 2,
      assignmentRate: 1,
      simulatedEndTick: 2,
      simulatedDurationSeconds: 120,
      riskIndex: 1.5,
      replayDigest: "candidate-replay",
      manifestDigest: "candidate-manifest",
      outputDigest: "candidate-output",
      observedRuntimeMillis: 1.8,
    },
  ],
};

describe("Strategy comparison panel", () => {
  it("renders actual bars, unavailable metrics, and provenance", async () => {
    const user = userEvent.setup();
    const onRun = vi.fn().mockResolvedValue(comparison);
    render(<StrategyComparisonPanel onRun={onRun} />);

    await user.click(screen.getByRole("button", { name: "Compare strategies" }));
    expect(await screen.findByText("Comparison ready")).toBeInTheDocument();
    expect(screen.getByText("Assignment rate")).toBeInTheDocument();
    expect(screen.getAllByText("100.0%").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Unavailable from recorded run").length).toBeGreaterThan(3);
    expect(screen.getByText("Recorded run: replay-control-default-v1")).toBeInTheDocument();
    expect(onRun).toHaveBeenCalledWith([
      expect.objectContaining({
        strategy: "weighted-greedy",
        variantId: "strategy-weighted-greedy",
      }),
    ]);

    await user.click(screen.getByRole("button", { name: "Clear strategy comparison" }));
    expect(screen.queryByText("Assignment rate")).not.toBeInTheDocument();
  });

  it("keeps comparison failures visible", async () => {
    const user = userEvent.setup();
    render(
      <StrategyComparisonPanel onRun={vi.fn().mockRejectedValue(new Error("lab unavailable"))} />,
    );

    await user.click(screen.getByRole("button", { name: "Compare strategies" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("lab unavailable");
  });
});
