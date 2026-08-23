import userEvent from "@testing-library/user-event";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { WhatIfComparisonPanel } from "./WhatIfComparisonPanel";
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
      replayDigest: "replay-digest",
      manifestDigest: "manifest-digest",
      outputDigest: "output-digest",
      observedRuntimeMillis: 1,
    },
    {
      variantId: "stress",
      label: "Traffic stress",
      strategy: "weighted-greedy",
      strategyVersion: "1.0.0",
      requestCount: 3,
      assignedCount: 2,
      assignmentRate: 2 / 3,
      simulatedEndTick: 3,
      simulatedDurationSeconds: 180,
      riskIndex: 12.5,
      replayDigest: "stress-replay",
      manifestDigest: "stress-manifest",
      outputDigest: "stress-output",
      observedRuntimeMillis: 1,
    },
  ],
};

describe("What-if comparison panel", () => {
  it("runs a variant and renders explicit comparison provenance", async () => {
    const user = userEvent.setup();
    const onRun = vi.fn().mockResolvedValue(comparison);
    render(<WhatIfComparisonPanel onRun={onRun} />);

    expect(
      screen.getByRole("heading", { name: "Compare a scenario variant." }),
    ).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Run comparison" }));

    expect(await screen.findByText("Comparison ready")).toBeInTheDocument();
    expect(screen.getAllByText("Recorded baseline").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Traffic stress").length).toBeGreaterThan(0);
    expect(screen.getByText("Bounded counterfactual delta")).toBeInTheDocument();
    expect(screen.getByText("Coverage objective delta")).toBeInTheDocument();
    expect(screen.getByText("changed")).toBeInTheDocument();
    expect(screen.getAllByText(/not a causal production claim/).length).toBeGreaterThan(0);
    expect(onRun).toHaveBeenCalledWith(
      expect.objectContaining({
        variantId: "traffic-stress",
        demandMultiplier: 1.2,
        preparationDelayTicks: 2,
      }),
    );

    await user.click(screen.getByRole("button", { name: "Clear comparison" }));
    expect(screen.queryByText("Traffic stress")).not.toBeInTheDocument();
  });

  it("keeps compute failures visible", async () => {
    const user = userEvent.setup();
    render(
      <WhatIfComparisonPanel onRun={vi.fn().mockRejectedValue(new Error("compute unavailable"))} />,
    );

    await user.click(screen.getByRole("button", { name: "Run comparison" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("compute unavailable");
  });
});
