import { BarChart3, LoaderCircle, Play, RotateCcw, TriangleAlert } from "lucide-react";
import { useState } from "react";
import type { WhatIfComparison, WhatIfMetric, WhatIfVariantInput } from "../domain/model";
import { fallbackStrategyRegistry } from "../data/strategies";

interface StrategyComparisonPanelProps {
  onRun: (variants: readonly WhatIfVariantInput[]) => Promise<WhatIfComparison>;
  onComparisonChange?: (comparison: WhatIfComparison | null) => void;
  strategies?: readonly string[];
}

const unavailableMetrics = [
  "Completion",
  "Overtime",
  "Distance",
  "Utilization",
  "Fairness",
  "Cost",
];

function variantFor(strategy: string): WhatIfVariantInput {
  return {
    variantId: `strategy-${strategy}`,
    label: `${strategy} candidate`,
    demandMultiplier: 1,
    supplyDelta: 0,
    preparationDelayTicks: 0,
    trafficMultiplier: 1,
    strategy,
    riskMultiplier: 1,
  };
}

function metricValue(metric: WhatIfMetric, key: "assignment" | "duration" | "runtime" | "risk") {
  if (key === "assignment") return metric.assignmentRate;
  if (key === "duration") return metric.simulatedDurationSeconds;
  if (key === "runtime") return metric.observedRuntimeMillis;
  return metric.riskIndex;
}

function formatMetric(value: number, key: "assignment" | "duration" | "runtime" | "risk") {
  if (key === "assignment") return `${(value * 100).toFixed(1)}%`;
  if (key === "duration") return `${value.toFixed(0)} s`;
  if (key === "runtime") return `${value.toFixed(2)} ms`;
  return value.toFixed(2);
}

export function StrategyComparisonPanel({
  onRun,
  onComparisonChange,
  strategies = fallbackStrategyRegistry.map((descriptor) => descriptor.name),
}: StrategyComparisonPanelProps) {
  const [candidate, setCandidate] = useState("weighted-greedy");
  const [comparison, setComparison] = useState<WhatIfComparison | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = async () => {
    setRunning(true);
    setError(null);
    try {
      const result = await onRun([variantFor(candidate)]);
      setComparison(result);
      onComparisonChange?.(result);
    } catch (cause) {
      setComparison(null);
      setError(cause instanceof Error ? cause.message : "Strategy comparison unavailable");
    } finally {
      setRunning(false);
    }
  };

  const clear = () => {
    setComparison(null);
    setError(null);
    onComparisonChange?.(null);
  };

  const actualMetrics: readonly [string, "assignment" | "duration" | "runtime" | "risk"][] = [
    ["Assignment rate", "assignment"],
    ["Simulated duration", "duration"],
    ["Observed compute runtime", "runtime"],
    ["Scenario risk index", "risk"],
  ];

  return (
    <section
      className="panel strategy-comparison-panel"
      aria-label="Strategy comparison visualization"
    >
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Strategy lab / evidence view</p>
          <h2>See strategies on the same run.</h2>
          <p className="panel-subtitle">
            Recorded scenario comparison; no combined production score.
          </p>
        </div>
        <BarChart3 size={18} className="heading-icon" aria-hidden="true" />
      </div>
      <div className="strategy-comparison-controls">
        <label>
          Candidate strategy
          <select
            aria-label="Comparison candidate strategy"
            value={candidate}
            onChange={(event) => setCandidate(event.target.value)}
          >
            {strategies.map((strategy) => (
              <option key={strategy} value={strategy}>
                {strategy}
              </option>
            ))}
          </select>
        </label>
        <button
          className="button button-primary"
          type="button"
          disabled={running}
          onClick={() => void run()}
        >
          {running ? <LoaderCircle className="spin" size={15} /> : <Play size={15} />}
          {running ? "Comparing strategies" : "Compare strategies"}
        </button>
        <button
          className="icon-button"
          type="button"
          title="Clear strategy comparison"
          aria-label="Clear strategy comparison"
          onClick={clear}
        >
          <RotateCcw size={16} />
        </button>
        <span className="what-if-status" role="status" aria-live="polite">
          {running
            ? "Running the same recorded scenario"
            : comparison
              ? "Comparison ready"
              : "No comparison run"}
        </span>
      </div>
      {error && (
        <div className="projection-state projection-unavailable" role="alert">
          <TriangleAlert size={16} aria-hidden="true" />
          <span>{error}</span>
        </div>
      )}
      {comparison && (
        <div className="strategy-comparison-results" aria-label="Strategy comparison results">
          <div className="what-if-provenance">
            <span>Recorded run: {comparison.recordedRunId}</span>
            <code>comparison {comparison.comparisonDigest.slice(0, 12)}</code>
            <small>{comparison.claimLabel}</small>
          </div>
          <div
            className="strategy-visualization"
            role="group"
            aria-label="Recorded strategy metrics"
          >
            {actualMetrics.map(([label, key]) => {
              const values = comparison.results.map((result) => metricValue(result, key));
              const max = Math.max(...values, 0.0001);
              return (
                <div
                  className="strategy-metric-visual"
                  key={key}
                  role="group"
                  aria-label={`${label} comparison`}
                >
                  <div className="strategy-metric-heading">
                    <strong>{label}</strong>
                    <small>actual recorded metric</small>
                  </div>
                  {comparison.results.map((result) => {
                    const value = metricValue(result, key);
                    return (
                      <div
                        className="strategy-bar-row"
                        key={`${key}-${result.variantId}`}
                        role="group"
                        aria-label={`${result.label}: ${formatMetric(value, key)}`}
                      >
                        <span>{result.label}</span>
                        <div className="strategy-bar-track" aria-hidden="true">
                          <span style={{ width: `${Math.max(2, (value / max) * 100)}%` }} />
                        </div>
                        <strong>{formatMetric(value, key)}</strong>
                      </div>
                    );
                  })}
                </div>
              );
            })}
          </div>
          <div className="strategy-unavailable" aria-label="Unavailable strategy metrics">
            <div className="panel-heading compact-heading">
              <div>
                <p className="eyebrow">Metric inventory</p>
                <h3>Unavailable from recorded run</h3>
              </div>
            </div>
            <ul>
              {unavailableMetrics.map((metric) => (
                <li key={metric}>
                  <span>{metric}</span>
                  <small>Unavailable from recorded run</small>
                </li>
              ))}
            </ul>
          </div>
          <div className="strategy-comparison-provenance">
            {comparison.results.map((result) => (
              <span key={result.variantId}>
                {result.label}: replay {result.replayDigest.slice(0, 12)} · manifest{" "}
                {result.manifestDigest.slice(0, 12)} · output {result.outputDigest.slice(0, 12)}
              </span>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}
