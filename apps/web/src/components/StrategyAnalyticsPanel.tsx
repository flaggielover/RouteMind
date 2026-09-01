import { GitCompareArrows, ShieldCheck, Sparkles } from "lucide-react";
import { useMemo } from "react";
import type { WhatIfComparison } from "../domain/model";
import { projectStrategyAnalytics } from "../domain/strategyAnalytics";
import { useLocale } from "../i18n";

interface StrategyAnalyticsPanelProps {
  comparison: WhatIfComparison | null;
}

function percent(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

export function StrategyAnalyticsPanel({ comparison }: StrategyAnalyticsPanelProps) {
  const { t, locale } = useLocale();
  const localeText = (zh: string, en: string) => (locale === "zh-CN" ? zh : en);
  const localizeClaim = (value: string) =>
    locale === "zh-CN" && value === "scenario comparison; not a causal production claim"
      ? "场景对比；不是生产因果结论。"
      : value;
  const projection = useMemo(
    () => (comparison ? projectStrategyAnalytics(comparison) : null),
    [comparison],
  );

  return (
    <section className="panel strategy-analytics-panel" aria-label={t("analytics.strategySurface")}>
      <div className="panel-heading">
        <div>
          <p className="eyebrow">{t("analytics.strategySurface")} / frontier</p>
          <h2>{t("strategy.sameRunTitle")}</h2>
          <p className="panel-subtitle">{t("strategy.recordedComparisonHint")}</p>
        </div>
        <GitCompareArrows size={18} className="heading-icon" aria-hidden="true" />
      </div>
      {!projection ? (
        <p className="empty-state">
          {localeText(
            "运行已记录对比以计算策略分析。",
            "Run a recorded comparison to compute strategy analytics.",
          )}
        </p>
      ) : (
        <>
          <div className="strategy-analytics-summary">
            <strong>{projection.summary}</strong>
            <span>
              {projection.recordedRunId} · {projection.scenarioId} · seed {projection.seed}
            </span>
            <small>{localizeClaim(projection.claimLabel)}</small>
          </div>

          <section className="strategy-analytics-section" aria-labelledby="strategy-metadata-title">
            <div className="decision-xray-block-heading">
              <h3 id="strategy-metadata-title">
                {localeText("注册表元数据", "Registry metadata")}
              </h3>
              <span>{localeText("计算注册表契约", "compute registry contract")}</span>
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
                      <dt>{localeText("参数", "Parameters")}</dt>
                      <dd>
                        {metadata.parameters.length
                          ? metadata.parameters
                              .map((parameter) => `${parameter.key}=${parameter.defaultValue}`)
                              .join(", ")
                          : localeText("未发布", "None published")}
                      </dd>
                    </div>
                    <div>
                      <dt>{localeText("约束", "Constraints")}</dt>
                      <dd>{metadata.constraints.join("; ")}</dd>
                    </div>
                    <div>
                      <dt>{localeText("回退", "Fallback")}</dt>
                      <dd>
                        {metadata.fallback.available
                          ? `${metadata.fallback.strategy} ${localeText("可用", "available")}`
                          : t("role.unavailable")}
                      </dd>
                    </div>
                    <div>
                      <dt>{localeText("验证", "Verification")}</dt>
                      <dd>{metadata.verification.detail}</dd>
                    </div>
                  </dl>
                </article>
              ))}
            </div>
          </section>

          <section className="strategy-analytics-section" aria-labelledby="pareto-title">
            <div className="decision-xray-block-heading">
              <h3 id="pareto-title">
                {localeText("计算出的 Pareto 点", "Computed Pareto points")}
              </h3>
              <span>
                {projection.frontier.length} {localeText("前沿点", "frontier")}
              </span>
            </div>
            <p className="strategy-analytics-objective">
              <Sparkles size={14} aria-hidden="true" /> {localeText("目标", "Objective")}:{" "}
              {projection.objective}
            </p>
            <div
              className="strategy-pareto-table"
              role="table"
              aria-label={localeText("计算出的 Pareto 策略点", "Computed Pareto strategy points")}
            >
              <div className="strategy-pareto-row strategy-pareto-header" role="row">
                <span role="columnheader">{t("ops.strategy")}</span>
                <span role="columnheader">{localeText("分配率", "Assignment")}</span>
                <span role="columnheader">{localeText("时长", "Duration")}</span>
                <span role="columnheader">{t("analytics.riskIndex")}</span>
                <span role="columnheader">{t("ops.status")}</span>
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
                      ? localeText("Pareto 前沿", "Pareto frontier")
                      : `${localeText("被以下策略支配", "Dominated by")} ${point.dominatedBy.join(", ")}`}
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
              <h3 id="analytics-inventory-title">
                {localeText("指标与验证清单", "Metric and verification inventory")}
              </h3>
              <ShieldCheck size={15} aria-hidden="true" />
            </div>
            <ul className="strategy-analytics-unavailable">
              {projection.unavailableMetrics.map((metric) => (
                <li key={metric}>
                  <strong>{metric}</strong>
                  <span>{t("strategy.unavailableRecorded")}</span>
                </li>
              ))}
            </ul>
          </section>
        </>
      )}
    </section>
  );
}
