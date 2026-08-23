import { describe, expect, it } from "vitest";
import { projectWhatIfDeltas } from "./whatIfDelta";
import type { WhatIfComparison } from "./model";

const comparison: WhatIfComparison = {
  source: "what-if",
  claimLabel: "scenario comparison; not a causal production claim",
  recordedRunId: "run-1",
  comparisonDigest: "comparison-1",
  scenarioId: "scenario-1",
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
      riskIndex: 1,
      replayDigest: "baseline-replay",
      manifestDigest: "baseline-manifest",
      outputDigest: "baseline-output",
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

describe("what-if delta projection", () => {
  it("computes changed objective, duration, risk, and provenance deltas", () => {
    const [delta] = projectWhatIfDeltas(comparison);
    expect(delta).toMatchObject({
      variantId: "stress",
      changed: true,
      objectiveDelta: -0.333333,
      durationDeltaSeconds: 120,
      riskDelta: 11.5,
      recordedRunId: "run-1",
      baselineReplayDigest: "baseline-replay",
      variantReplayDigest: "stress-replay",
    });
  });

  it("returns no deltas when the baseline is absent", () => {
    expect(projectWhatIfDeltas({ ...comparison, results: comparison.results.slice(1) })).toEqual(
      [],
    );
  });

  it("labels an identical variant unchanged", () => {
    const identical = { ...comparison.results[0]!, variantId: "same", label: "Same" };
    expect(
      projectWhatIfDeltas({ ...comparison, results: [comparison.results[0]!, identical] })[0]
        ?.changed,
    ).toBe(false);
  });
});
