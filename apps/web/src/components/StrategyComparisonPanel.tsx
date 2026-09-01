import { BarChart3, LoaderCircle, Play, RotateCcw, TriangleAlert } from "lucide-react";
import { useState } from "react";
import type { WhatIfComparison, WhatIfMetric, WhatIfVariantInput } from "../domain/model";
import { fallbackStrategyRegistry } from "../data/strategies";
import { useLocale } from "../i18n";

interface StrategyComparisonPanelProps {
  onRun: (variants: readonly WhatIfVariantInput[]) => Promise<WhatIfComparison>;
  onComparisonChange?: (comparison: WhatIfComparison | null) => void;
  strategies?: readonly string[];
}

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
  const { locale, t } = useLocale();
  const localize = (value: string): string => {
    if (locale !== "zh-CN") return value;
    return value === "scenario comparison; not a causal production claim"
      ? "场景对比；不是生产因果结论。"
      : value;
  };
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
      setError(cause instanceof Error ? cause.message : t("role.unavailable"));
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
    [t("strategy.assignmentRate"), "assignment"],
    [t("strategy.simulatedDuration"), "duration"],
    [t("strategy.observedRuntime"), "runtime"],
    [t("strategy.scenarioRisk"), "risk"],
  ];
  const unavailableMetrics =
    locale === "zh-CN"
      ? ["完成率", "超时", "距离", "利用率", "公平性", "成本"]
      : ["Completion", "Overtime", "Distance", "Utilization", "Fairness", "Cost"];

  return (
    <section className="panel strategy-comparison-panel" aria-label={t("strategy.comparisonAria")}>
      <div className="panel-heading">
        <div>
          <p className="eyebrow">{t("strategy.evidenceEyebrow")}</p>
          <h2>{t("strategy.sameRunTitle")}</h2>
          <p className="panel-subtitle">{t("strategy.recordedComparisonHint")}</p>
        </div>
        <BarChart3 size={18} className="heading-icon" aria-hidden="true" />
      </div>
      <div className="strategy-comparison-controls">
        <label>
          {t("strategy.candidate")}
          <select
            aria-label={t("strategy.candidate")}
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
          {running ? t("strategy.comparing") : t("strategy.compare")}
        </button>
        <button
          className="icon-button"
          type="button"
          title={t("strategy.clear")}
          aria-label={t("strategy.clear")}
          onClick={clear}
        >
          <RotateCcw size={16} />
        </button>
        <span className="what-if-status" role="status" aria-live="polite">
          {running
            ? t("strategy.runningRecorded")
            : comparison
              ? t("strategy.comparisonReady")
              : t("strategy.noComparison")}
        </span>
      </div>
      {error && (
        <div className="projection-state projection-unavailable" role="alert">
          <TriangleAlert size={16} aria-hidden="true" />
          <span>{error}</span>
        </div>
      )}
      {comparison && (
        <div className="strategy-comparison-results" aria-label={t("strategy.comparisonResults")}>
          <div className="what-if-provenance">
            <span>
              {t("strategy.recordedRun")}: {comparison.recordedRunId}
            </span>
            <code>comparison {comparison.comparisonDigest.slice(0, 12)}</code>
            <small>{localize(comparison.claimLabel)}</small>
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
                    <small>{t("strategy.actualRecordedMetric")}</small>
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
                <p className="eyebrow">{t("strategy.metricInventory")}</p>
                <h3>{t("strategy.unavailableRecorded")}</h3>
              </div>
            </div>
            <ul>
              {unavailableMetrics.map((metric) => (
                <li key={metric}>
                  <span>{metric}</span>
                  <small>{t("strategy.unavailableRecorded")}</small>
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
