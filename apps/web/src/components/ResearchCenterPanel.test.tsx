import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { demoDataSource } from "../data/demoSnapshot";
import type { WhatIfComparison } from "../domain/model";
import { ResearchCenterPanel } from "./ResearchCenterPanel";

const comparison: WhatIfComparison = {
  source: "what-if",
  claimLabel: "scenario comparison; not a causal production claim",
  recordedRunId: "run-1",
  comparisonDigest: "comparison-digest",
  scenarioId: "scenario-1",
  seed: 7,
  results: [
    {
      variantId: "baseline",
      label: "Recorded baseline",
      strategy: "nearest",
      strategyVersion: "1.0.0",
      requestCount: 1,
      assignedCount: 1,
      assignmentRate: 1,
      simulatedEndTick: 1,
      simulatedDurationSeconds: 60,
      riskIndex: 0,
      replayDigest: "replay-digest",
      manifestDigest: "manifest-digest",
      outputDigest: "output-digest",
      observedRuntimeMillis: 1,
    },
  ],
};

describe("ResearchCenterPanel", () => {
  it("renders manifest, observations, lineage, artifacts, and claim boundary", () => {
    render(<ResearchCenterPanel snapshot={demoDataSource.getSnapshot()} comparison={comparison} />);
    expect(
      screen.getByRole("heading", { name: "Inspect manifests before making claims." }),
    ).toBeInTheDocument();
    expect(screen.getByText("research:run-1")).toBeInTheDocument();
    expect(screen.getByText("engineering observation")).toBeInTheDocument();
    expect(screen.getByText("source -> manifest -> replay/output artifacts")).toBeInTheDocument();
    expect(screen.getByText("Scientific claims", { exact: false })).toBeInTheDocument();
    expect(screen.getByText("Comparison")).toBeInTheDocument();
  });

  it("keeps missing experiment artifacts explicit", () => {
    render(<ResearchCenterPanel snapshot={demoDataSource.getSnapshot()} comparison={null} />);
    expect(screen.getByText("No artifact references are attached.")).toBeInTheDocument();
    expect(screen.getByText("No comparison manifest attached")).toBeInTheDocument();
  });
});
