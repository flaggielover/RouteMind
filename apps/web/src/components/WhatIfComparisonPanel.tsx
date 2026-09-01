import { AlertTriangle, GitCompareArrows, LoaderCircle, Play, RotateCcw } from "lucide-react";
import { useState } from "react";
import type { WhatIfComparison, WhatIfVariantInput } from "../domain/model";
import { fallbackStrategyRegistry } from "../data/strategies";
import { projectWhatIfDeltas } from "../domain/whatIfDelta";
import { useLocale } from "../i18n";

interface WhatIfComparisonPanelProps {
  onRun: (variant: WhatIfVariantInput) => Promise<WhatIfComparison>;
  strategies?: readonly string[];
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

export function WhatIfComparisonPanel({
  onRun,
  strategies = fallbackStrategyRegistry.map((descriptor) => descriptor.name),
}: WhatIfComparisonPanelProps) {
  const { t, locale } = useLocale();
  const [variant, setVariant] = useState(() => ({
    ...initialVariant,
    label: locale === "zh-CN" ? "交通压力" : initialVariant.label,
  }));
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
      setError(cause instanceof Error ? cause.message : t("role.unavailable"));
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
    <section className="panel what-if-panel" aria-label={t("strategy.whatIfAria")}>
      <div className="panel-heading">
        <div>
          <p className="eyebrow">{t("strategy.whatIfEyebrow")}</p>
          <h2>{t("strategy.whatIfTitle")}</h2>
          <p className="panel-subtitle">{t("strategy.whatIfHint")}</p>
        </div>
        <GitCompareArrows size={18} className="heading-icon" aria-hidden="true" />
      </div>
      <div className="what-if-controls">
        <label>
          {t("strategy.variantLabel")}
          <input
            aria-label={t("strategy.variantLabel")}
            value={variant.label}
            onChange={(event) => update("label", event.target.value)}
          />
        </label>
        <label>
          {t("ops.strategy")}
          <select
            aria-label={t("ops.strategy")}
            value={variant.strategy}
            onChange={(event) => update("strategy", event.target.value)}
          >
            {strategies.map((strategy) => (
              <option key={strategy} value={strategy}>
                {strategy}
              </option>
            ))}
          </select>
        </label>
        <label>
          {t("strategy.demandMultiplier")}
          <input
            aria-label={t("strategy.demandMultiplier")}
            type="number"
            min="0.5"
            max="2"
            step="0.1"
            value={variant.demandMultiplier}
            onChange={(event) => update("demandMultiplier", Number(event.target.value))}
          />
        </label>
        <label>
          {t("strategy.supplyDelta")}
          <input
            aria-label={t("strategy.supplyDelta")}
            type="number"
            min="-32"
            max="32"
            step="1"
            value={variant.supplyDelta}
            onChange={(event) => update("supplyDelta", Number(event.target.value))}
          />
        </label>
        <label>
          {t("strategy.prepDelay")}
          <input
            aria-label={t("strategy.prepDelay")}
            type="number"
            min="0"
            max="60"
            step="1"
            value={variant.preparationDelayTicks}
            onChange={(event) => update("preparationDelayTicks", Number(event.target.value))}
          />
        </label>
        <label>
          {t("strategy.trafficMultiplier")}
          <input
            aria-label={t("strategy.trafficMultiplier")}
            type="number"
            min="0.5"
            max="3"
            step="0.1"
            value={variant.trafficMultiplier}
            onChange={(event) => update("trafficMultiplier", Number(event.target.value))}
          />
        </label>
        <label>
          {t("strategy.riskMultiplier")}
          <input
            aria-label={t("strategy.riskMultiplier")}
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
          {running ? t("strategy.runningComparison") : t("strategy.runComparison")}
        </button>
        <button
          className="icon-button"
          type="button"
          title={t("strategy.clearComparison")}
          aria-label={t("strategy.clearComparison")}
          onClick={clear}
        >
          <RotateCcw size={16} />
        </button>
        <span className="what-if-status" role="status" aria-live="polite">
          {running
            ? t("strategy.computingVariants")
            : comparison
              ? t("strategy.comparisonReady")
              : t("strategy.noComparison")}
        </span>
      </div>
      {error && (
        <div className="projection-state projection-unavailable" role="alert">
          <AlertTriangle size={16} aria-hidden="true" />
          <span>{error}</span>
        </div>
      )}
      {comparison && (
        <div className="what-if-results" aria-label={t("strategy.whatIfResults")}>
          <div className="what-if-provenance">
            <span>
              {t("strategy.recordedBaseline")}: {comparison.recordedRunId}
            </span>
            <code>comparison {formatDigest(comparison.comparisonDigest)}</code>
            <small>{comparison.claimLabel}</small>
          </div>
          <div className="what-if-result-list">
            {comparison.results.map((result) => (
              <article className="what-if-result" key={result.variantId}>
                <div className="what-if-result-heading">
                  <div>
                    <p className="eyebrow">
                      {result.variantId === "baseline"
                        ? t("strategy.recordedBaseline")
                        : t("strategy.scenarioVariant")}
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
                    <dt>{t("strategy.assigned")}</dt>
                    <dd>
                      {result.assignedCount} / {result.requestCount} (
                      {formatPercent(result.assignmentRate)})
                    </dd>
                  </div>
                  <div>
                    <dt>{t("strategy.simulatedDuration")}</dt>
                    <dd>{result.simulatedDurationSeconds.toFixed(0)} s</dd>
                  </div>
                  <div>
                    <dt>{t("strategy.scenarioRisk")}</dt>
                    <dd>{result.riskIndex.toFixed(2)}</dd>
                  </div>
                  <div>
                    <dt>{t("strategy.replayDigest")}</dt>
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
            <section className="what-if-delta-section" aria-label={t("strategy.boundedDelta")}>
              <div className="decision-xray-block-heading">
                <div>
                  <p className="eyebrow">{t("strategy.boundedDelta")}</p>
                  <h3>{t("strategy.variantImpact")}</h3>
                </div>
                <span>{t("strategy.notCausal")}</span>
              </div>
              <div className="what-if-delta-list">
                {deltas.map((delta) => (
                  <article className="what-if-delta" key={delta.variantId}>
                    <div className="what-if-delta-heading">
                      <strong>{delta.label}</strong>
                      <span className={delta.changed ? "delta-changed" : "delta-unchanged"}>
                        {delta.changed ? t("strategy.changed") : t("strategy.unchanged")}
                      </span>
                    </div>
                    <dl>
                      <div>
                        <dt>{t("strategy.coverageDelta")}</dt>
                        <dd>{formatDelta(delta.objectiveDelta, " pts")}</dd>
                      </div>
                      <div>
                        <dt>{t("strategy.durationDelta")}</dt>
                        <dd>{formatDelta(delta.durationDeltaSeconds, " s")}</dd>
                      </div>
                      <div>
                        <dt>{t("strategy.riskDelta")}</dt>
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
