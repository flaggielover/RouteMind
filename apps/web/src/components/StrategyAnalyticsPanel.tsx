import { GitCompareArrows, ShieldCheck, Sparkles } from "lucide-react";
import { useMemo } from "react";
import type { WhatIfComparison } from "../domain/model";
import { projectStrategyAnalytics } from "../domain/strategyAnalytics";

interface StrategyAnalyticsPanelProps {
  comparison: WhatIfComparison | null;
}

function percent(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

export function StrategyAnalyticsPanel({ comparison }: StrategyAnalyticsPanelProps) {
  const projection = useMemo(
    () => (comparison ? projectStrategyAnalytics(comparison) : null),
    [comparison],
  );

  return (
    <section className="panel strategy-analytics-panel" aria-label="Strategy analytics">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Strategy analytics / computed frontier</p>
          <h2>Compare the evidence, then inspect the trade-offs.</h2>
          <p className="panel-subtitle">
            Pareto status is calculated from recorded metrics; it is not a production ranking.
          </p>
        </div>
        <GitCompareArrows size={18} className="heading-icon" aria-hidden="true" />
      </div>
      {!projection ? (
        <p className="empty-state">Run a recorded comparison to compute strategy analytics.</p>
      ) : (
        <>
          <div className="strategy-analytics-summary">
            <strong>{projection.summary}</strong>
            <span>
              {projection.recordedRunId} · {projection.scenarioId} · seed {projection.seed}
            </span>
            <small>{projection.claimLabel}</small>
          </div>

          <section className="strategy-analytics-section" aria-labelledby="strategy-metadata-title">
            <div className="decision-xray-block-heading">
              <h3 id="strategy-metadata-title">Registry metadata</h3>
              <span>compute registry contract</span>
            </div>
            <div className="strategy-metadata-grid">
              {projection.metadata.map((metadata) => (
                <article
                  className="strategy-metadata-item"
                  key={`${metadata.name}-${metadata.version}`}
                >
                  <div className="strategy-metadata-heading">
                    <strong>{metadata.name}</strong>
                    <span>{metadata.maturity}</span>
                  </div>
                  <small>
                    {metadata.version} · {metadata.capabilities.join(", ")}
                  </small>
                  <dl className="detail-list">
                    <div>
                      <dt>Parameters</dt>
                      <dd>
                        {metadata.parameters.length
                          ? metadata.parameters
                              .map((parameter) => `${parameter.key}=${parameter.defaultValue}`)
                              .join(", ")
                          : "None published"}
                      </dd>
                    </div>
                    <div>
                      <dt>Constraints</dt>
                      <dd>{metadata.constraints.join("; ")}</dd>
                    </div>
                    <div>
                      <dt>Fallback</dt>
                      <dd>
                        {metadata.fallback.available
                          ? `${metadata.fallback.strategy} available`
                          : "Unavailable"}
                      </dd>
                    </div>
                    <div>
                      <dt>Verification</dt>
                      <dd>{metadata.verification.detail}</dd>
                    </div>
                  </dl>
                </article>
              ))}
            </div>
          </section>

          <section className="strategy-analytics-section" aria-labelledby="pareto-title">
            <div className="decision-xray-block-heading">
              <h3 id="pareto-title">Computed Pareto points</h3>
              <span>{projection.frontier.length} frontier</span>
            </div>
            <p className="strategy-analytics-objective">
              <Sparkles size={14} aria-hidden="true" /> Objective: {projection.objective}
            </p>
            <div
              className="strategy-pareto-table"
              role="table"
              aria-label="Computed Pareto strategy points"
            >
              <div className="strategy-pareto-row strategy-pareto-header" role="row">
                <span role="columnheader">Strategy</span>
                <span role="columnheader">Assignment</span>
                <span role="columnheader">Duration</span>
                <span role="columnheader">Risk</span>
                <span role="columnheader">Status</span>
              </div>
              {projection.points.map((point) => (
                <div className="strategy-pareto-row" role="row" key={point.metric.variantId}>
                  <strong role="cell">{point.metric.strategy}</strong>
                  <span role="cell">{percent(point.metric.assignmentRate)}</span>
                  <span role="cell">{point.metric.simulatedDurationSeconds.toFixed(0)} s</span>
                  <span role="cell">{point.metric.riskIndex.toFixed(2)}</span>
                  <span
                    role="cell"
                    className={
                      point.pareto ? "strategy-pareto-status frontier" : "strategy-pareto-status"
                    }
                  >
                    {point.pareto
                      ? "Pareto frontier"
                      : `Dominated by ${point.dominatedBy.join(", ")}`}
                  </span>
                </div>
              ))}
            </div>
          </section>

          <section
            className="strategy-analytics-section"
            aria-labelledby="analytics-inventory-title"
          >
            <div className="decision-xray-block-heading">
              <h3 id="analytics-inventory-title">Metric and verification inventory</h3>
              <ShieldCheck size={15} aria-hidden="true" />
            </div>
            <ul className="strategy-analytics-unavailable">
              {projection.unavailableMetrics.map((metric) => (
                <li key={metric}>
                  <strong>{metric}</strong>
                  <span>Unavailable from this recorded comparison</span>
                </li>
              ))}
            </ul>
          </section>
        </>
      )}
    </section>
  );
}
