import type { WhatIfComparison } from "./model";
import type { OperationsSnapshot } from "./model";

export type ResearchEvidenceStatus = "ready" | "pending" | "fixture" | "unavailable";

export interface ResearchManifestProjection {
  manifestId: string;
  scenarioId: string;
  seed: number | null;
  codeVersion: string;
  referenceDataId: string;
  strategies: readonly string[];
  status: ResearchEvidenceStatus;
}

export interface ResearchObservation {
  label: string;
  category: "engineering observation" | "empirical observation" | "scientific claim";
  value: string;
  evidence: string;
}

export interface ResearchArtifactReference {
  label: string;
  digest: string;
  role: "replay" | "manifest" | "output" | "comparison";
}

export interface ResearchCenterProjection {
  status: ResearchEvidenceStatus;
  sourceLabel: string;
  manifest: ResearchManifestProjection;
  observations: readonly ResearchObservation[];
  artifacts: readonly ResearchArtifactReference[];
  lineage: readonly string[];
  boundary: string;
}

export function projectResearchCenter(
  snapshot: OperationsSnapshot,
  comparison: WhatIfComparison | null,
): ResearchCenterProjection {
  const hasComparison = Boolean(comparison);
  const strategies = comparison
    ? [
        ...new Set(
          comparison.results.map((result) => `${result.strategy} v${result.strategyVersion}`),
        ),
      ]
    : snapshot.dispatch.strategy !== "unavailable"
      ? [`${snapshot.dispatch.strategy} v${snapshot.dispatch.version}`]
      : [];
  const referenceDataId = snapshot.decisionLedger?.referenceDataId ?? "unavailable";
  const manifest: ResearchManifestProjection = {
    manifestId: comparison ? `research:${comparison.recordedRunId}` : "research:pending",
    scenarioId: comparison?.scenarioId ?? "unavailable",
    seed: comparison?.seed ?? snapshot.simulation?.seed ?? snapshot.replay?.seed ?? null,
    codeVersion: "web-readonly-research-v1",
    referenceDataId,
    strategies,
    status: hasComparison ? "ready" : snapshot.source === "demo" ? "fixture" : "pending",
  };
  const observations: ResearchObservation[] =
    hasComparison && comparison
      ? comparison.results.map((result) => ({
          label: result.label,
          category: "engineering observation",
          value: `${(result.assignmentRate * 100).toFixed(1)}% assigned · ${result.simulatedDurationSeconds.toFixed(0)}s · risk ${result.riskIndex.toFixed(2)}`,
          evidence: `Replay ${result.replayDigest.slice(0, 12)} · output ${result.outputDigest.slice(0, 12)}`,
        }))
      : [
          {
            label: "Recorded experiment",
            category:
              snapshot.source === "demo" ? "empirical observation" : "engineering observation",
            value: "No comparison manifest attached",
            evidence: "Run provenance is unavailable; no result is inferred.",
          },
        ];
  const artifacts: ResearchArtifactReference[] = comparison
    ? [
        { label: "Comparison", digest: comparison.comparisonDigest, role: "comparison" },
        ...comparison.results.flatMap((result) => [
          { label: `${result.label} replay`, digest: result.replayDigest, role: "replay" as const },
          {
            label: `${result.label} manifest`,
            digest: result.manifestDigest,
            role: "manifest" as const,
          },
          { label: `${result.label} output`, digest: result.outputDigest, role: "output" as const },
        ]),
      ]
    : [];
  return {
    status: hasComparison ? "ready" : snapshot.source === "demo" ? "fixture" : "pending",
    sourceLabel: `${snapshot.source.toUpperCase()} research evidence`,
    manifest,
    observations,
    artifacts,
    lineage: comparison
      ? [
          `recorded run: ${comparison.recordedRunId}`,
          `scenario: ${comparison.scenarioId} / seed ${comparison.seed}`,
          `reference data: ${referenceDataId}`,
          "source -> manifest -> replay/output artifacts",
        ]
      : ["No recorded run is attached; lineage remains pending."],
    boundary:
      "Engineering observations are inspectable. Scientific claims and deep research campaigns remain deferred.",
  };
}
