import type { WhatIfComparison, WhatIfMetric } from "./model";

export interface WhatIfDelta {
  variantId: string;
  label: string;
  changed: boolean;
  objectiveDelta: number;
  assignmentRateDelta: number;
  durationDeltaSeconds: number;
  riskDelta: number;
  recordedRunId: string;
  baselineReplayDigest: string;
  variantReplayDigest: string;
  variantOutputDigest: string;
}

function delta(value: number, baseline: number): number {
  return Number((value - baseline).toFixed(6));
}

function coverageObjective(metric: WhatIfMetric): number {
  return metric.assignmentRate;
}

export function projectWhatIfDeltas(comparison: WhatIfComparison): readonly WhatIfDelta[] {
  const baseline = comparison.results.find((result) => result.variantId === "baseline");
  if (!baseline) return [];
  return comparison.results
    .filter((result) => result.variantId !== "baseline")
    .map((variant) => {
      const objectiveDelta = delta(coverageObjective(variant), coverageObjective(baseline));
      const assignmentRateDelta = delta(variant.assignmentRate, baseline.assignmentRate);
      const durationDeltaSeconds = delta(
        variant.simulatedDurationSeconds,
        baseline.simulatedDurationSeconds,
      );
      const riskDelta = delta(variant.riskIndex, baseline.riskIndex);
      return {
        variantId: variant.variantId,
        label: variant.label,
        changed: objectiveDelta !== 0 || durationDeltaSeconds !== 0 || riskDelta !== 0,
        objectiveDelta,
        assignmentRateDelta,
        durationDeltaSeconds,
        riskDelta,
        recordedRunId: comparison.recordedRunId,
        baselineReplayDigest: baseline.replayDigest,
        variantReplayDigest: variant.replayDigest,
        variantOutputDigest: variant.outputDigest,
      };
    });
}
