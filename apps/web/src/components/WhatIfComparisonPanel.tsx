import { AlertTriangle, GitCompareArrows, LoaderCircle, Play, RotateCcw } from "lucide-react";
import { useState } from "react";
import type { WhatIfComparison, WhatIfVariantInput } from "../domain/model";
import { projectWhatIfDeltas } from "../domain/whatIfDelta";

interface WhatIfComparisonPanelProps {
  onRun: (variant: WhatIfVariantInput) => Promise<WhatIfComparison>;
}

const initialVariant: WhatIfVariantInput = {
  variantId: "traffic-stress",
  label: "Traffic stress",
  demandMultiplier: 1.2,
  supplyDelta: 0,
  preparationDelayTicks: 2,
  trafficMultiplier: 1.4,
  strategy: "weighted-greedy",
  riskMultiplier: 1.5,
};

function formatPercent(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

function formatDigest(value: string): string {
  return value.slice(0, 12);
}

function formatDelta(value: number, suffix = ""): string {
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(2)}${suffix}`;
}

export function WhatIfComparisonPanel({ onRun }: WhatIfComparisonPanelProps) {
  const [variant, setVariant] = useState(initialVariant);
  const [comparison, setComparison] = useState<WhatIfComparison | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const update = <K extends keyof WhatIfVariantInput>(key: K, value: WhatIfVariantInput[K]) =>
    setVariant((current) => ({ ...current, [key]: value }));

  const run = async () => {
    setRunning(true);
    setError(null);
    try {
      setComparison(await onRun(variant));
    } catch (cause) {
      setComparison(null);
      setError(cause instanceof Error ? cause.message : "What-if comparison unavailable");
    } finally {
      setRunning(false);
    }
  };

  const clear = () => {
    setComparison(null);
    setError(null);
  };
  const deltas = comparison ? projectWhatIfDeltas(comparison) : [];

  return (
    <section className="panel what-if-panel" aria-label="What-if scenario comparison">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Strategy lab / what-if</p>
          <h2>Compare a scenario variant.</h2>
          <p className="panel-subtitle">Scenario comparison; not a causal production claim.</p>
        </div>
        <GitCompareArrows size={18} className="heading-icon" aria-hidden="true" />
      </div>
      <div className="what-if-controls">
        <label>
          Variant label
          <input
            aria-label="What-if variant label"
            value={variant.label}
            onChange={(event) => update("label", event.target.value)}
          />
        </label>
        <label>
          Strategy
          <select
            aria-label="What-if strategy"
            value={variant.strategy}
            onChange={(event) => update("strategy", event.target.value)}
          >
            <option value="nearest">nearest</option>
            <option value="weighted-greedy">weighted-greedy</option>
          </select>
        </label>
        <label>
          Demand x
          <input
            aria-label="What-if demand multiplier"
            type="number"
            min="0.5"
            max="2"
            step="0.1"
            value={variant.demandMultiplier}
            onChange={(event) => update("demandMultiplier", Number(event.target.value))}
          />
        </label>
        <label>
          Supply delta
          <input
            aria-label="What-if supply delta"
            type="number"
            min="-32"
            max="32"
            step="1"
            value={variant.supplyDelta}
            onChange={(event) => update("supplyDelta", Number(event.target.value))}
          />
        </label>
        <label>
          Prep delay ticks
          <input
            aria-label="What-if preparation delay"
            type="number"
            min="0"
            max="60"
            step="1"
            value={variant.preparationDelayTicks}
            onChange={(event) => update("preparationDelayTicks", Number(event.target.value))}
          />
        </label>
        <label>
          Traffic x
          <input
            aria-label="What-if traffic multiplier"
            type="number"
            min="0.5"
            max="3"
            step="0.1"
            value={variant.trafficMultiplier}
            onChange={(event) => update("trafficMultiplier", Number(event.target.value))}
          />
        </label>
        <label>
          Risk x
          <input
            aria-label="What-if risk multiplier"
            type="number"
            min="0.1"
            max="5"
            step="0.1"
            value={variant.riskMultiplier}
            onChange={(event) => update("riskMultiplier", Number(event.target.value))}
          />
        </label>
      </div>
      <div className="what-if-actions">
        <button
          className="button button-primary"
          type="button"
          disabled={running}
          onClick={() => void run()}
        >
          {running ? <LoaderCircle className="spin" size={15} /> : <Play size={15} />}
          {running ? "Running comparison" : "Run comparison"}
        </button>
        <button
          className="icon-button"
          type="button"
          title="Clear comparison"
          aria-label="Clear comparison"
          onClick={clear}
        >
          <RotateCcw size={16} />
        </button>
        <span className="what-if-status" role="status" aria-live="polite">
          {running
            ? "Computing recorded scenario variants"
            : comparison
              ? "Comparison ready"
              : "No comparison run"}
        </span>
      </div>
      {error && (
        <div className="projection-state projection-unavailable" role="alert">
          <AlertTriangle size={16} aria-hidden="true" />
          <span>{error}</span>
        </div>
      )}
      {comparison && (
        <div className="what-if-results" aria-label="What-if comparison results">
          <div className="what-if-provenance">
            <span>Recorded run: {comparison.recordedRunId}</span>
            <code>comparison {formatDigest(comparison.comparisonDigest)}</code>
            <small>{comparison.claimLabel}</small>
          </div>
          <div className="what-if-result-list">
            {comparison.results.map((result) => (
              <article className="what-if-result" key={result.variantId}>
                <div className="what-if-result-heading">
                  <div>
                    <p className="eyebrow">
                      {result.variantId === "baseline" ? "Recorded baseline" : "Scenario variant"}
                    </p>
                    <h3>{result.label}</h3>
                  </div>
                  <span className="status-pill status-healthy">
                    <span>
                      {result.strategy} v{result.strategyVersion}
                    </span>
                  </span>
                </div>
                <dl className="what-if-metrics">
                  <div>
                    <dt>Assigned</dt>
                    <dd>
                      {result.assignedCount} / {result.requestCount} (
                      {formatPercent(result.assignmentRate)})
                    </dd>
                  </div>
                  <div>
                    <dt>Simulated duration</dt>
                    <dd>{result.simulatedDurationSeconds.toFixed(0)} s</dd>
                  </div>
                  <div>
                    <dt>Scenario risk index</dt>
                    <dd>{result.riskIndex.toFixed(2)}</dd>
                  </div>
                  <div>
                    <dt>Replay digest</dt>
                    <dd>
                      <code>{formatDigest(result.replayDigest)}</code>
                    </dd>
                  </div>
                </dl>
                <small className="what-if-result-provenance">
                  manifest {formatDigest(result.manifestDigest)} · output{" "}
                  {formatDigest(result.outputDigest)}
                </small>
              </article>
            ))}
          </div>
          {deltas.length > 0 && (
            <section className="what-if-delta-section" aria-label="What-if deltas">
              <div className="decision-xray-block-heading">
                <div>
                  <p className="eyebrow">Bounded counterfactual delta</p>
                  <h3>Variant impact against the recorded baseline.</h3>
                </div>
                <span>not causal</span>
              </div>
              <div className="what-if-delta-list">
                {deltas.map((delta) => (
                  <article className="what-if-delta" key={delta.variantId}>
                    <div className="what-if-delta-heading">
                      <strong>{delta.label}</strong>
                      <span className={delta.changed ? "delta-changed" : "delta-unchanged"}>
                        {delta.changed ? "changed" : "unchanged"}
                      </span>
                    </div>
                    <dl>
                      <div>
                        <dt>Coverage objective delta</dt>
                        <dd>{formatDelta(delta.objectiveDelta, " pts")}</dd>
                      </div>
                      <div>
                        <dt>Duration delta</dt>
                        <dd>{formatDelta(delta.durationDeltaSeconds, " s")}</dd>
                      </div>
                      <div>
                        <dt>Risk delta</dt>
                        <dd>{formatDelta(delta.riskDelta)}</dd>
                      </div>
                    </dl>
                    <small>
                      recorded run {delta.recordedRunId} · source{" "}
                      {formatDigest(delta.baselineReplayDigest)} -&gt;{" "}
                      {formatDigest(delta.variantReplayDigest)} · output{" "}
                      {formatDigest(delta.variantOutputDigest)}
                    </small>
                  </article>
                ))}
              </div>
            </section>
          )}
        </div>
      )}
    </section>
  );
}
