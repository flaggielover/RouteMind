import { describe, expect, it } from "vitest";
import { demoDataSource } from "../data/demoSnapshot";
import type { WhatIfComparison } from "./model";
import { projectResearchCenter } from "./researchCenter";

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

describe("research center projection", () => {
  it("keeps manifest, observation, lineage, and artifacts linked", () => {
    const projection = projectResearchCenter(demoDataSource.getSnapshot(), comparison);
    expect(projection.status).toBe("ready");
    expect(projection.manifest.manifestId).toBe("research:run-1");
    expect(projection.manifest.strategies).toEqual(["nearest v1.0.0"]);
    expect(projection.observations[0]?.category).toBe("engineering observation");
    expect(projection.artifacts).toHaveLength(4);
    expect(projection.lineage).toContain("source -> manifest -> replay/output artifacts");
    expect(projection.boundary).toContain("Scientific claims");
  });

  it("marks an unattached experiment as fixture or pending without inference", () => {
    const projection = projectResearchCenter(demoDataSource.getSnapshot(), null);
    expect(projection.status).toBe("fixture");
    expect(projection.manifest.status).toBe("fixture");
    expect(projection.artifacts).toEqual([]);
    expect(projection.observations[0]?.value).toContain("No comparison manifest");
  });
});
