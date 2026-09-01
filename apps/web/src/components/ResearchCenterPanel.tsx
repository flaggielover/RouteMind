import { BookOpen, Database, FileCheck2, FlaskConical, GitBranch } from "lucide-react";
import { useMemo } from "react";
import type { WhatIfComparison, OperationsSnapshot } from "../domain/model";
import { projectResearchCenter } from "../domain/researchCenter";
import { useLocale } from "../i18n";

export function ResearchCenterPanel({
  snapshot,
  comparison,
}: {
  snapshot: OperationsSnapshot;
  comparison: WhatIfComparison | null;
}) {
  const projection = useMemo(
    () => projectResearchCenter(snapshot, comparison),
    [snapshot, comparison],
  );
  const { locale, t } = useLocale();
  const localize = (value: string): string => {
    if (locale !== "zh-CN") return value;
    const replacements: Record<string, string> = {
      "Engineering observations are inspectable. Scientific claims and deep research campaigns remain deferred.":
        "工程观测可检查。科学结论与深度研究计划仍待后续处理。",
      fixture: "演示固件",
      "DEMO research evidence": "演示研究证据",
      unavailable: "不可用",
      "Recorded experiment": "已记录实验",
      "empirical observation": "经验观测",
      "engineering observation": "工程观测",
      "No comparison manifest attached": "未附加对比清单",
      "Run provenance is unavailable; no result is inferred.": "运行溯源不可用，不推断任何结果。",
      "No recorded run is attached; lineage remains pending.": "未附加已记录运行，谱系仍待定。",
      "source -> manifest -> replay/output artifacts": "来源 -> 清单 -> 回放 / 输出产物",
    };
    return replacements[value] ?? value;
  };
  return (
    <section className="panel research-center-panel" aria-label={t("research.aria")}>
      <div className="panel-heading">
        <div>
          <p className="eyebrow">{t("research.eyebrow")}</p>
          <h2>{t("research.title")}</h2>
          <p className="panel-subtitle">{localize(projection.boundary)}</p>
        </div>
        <FlaskConical size={18} className="heading-icon" aria-hidden="true" />
      </div>
      <div className={`research-center-status ${projection.status}`} role="status">
        <BookOpen size={15} aria-hidden="true" />
        <strong>{localize(projection.status)}</strong>
        <span>{localize(projection.sourceLabel)}</span>
      </div>
      <div className="research-center-grid">
        <section className="research-center-block" aria-labelledby="research-manifest-title">
          <div className="decision-xray-block-heading">
            <h3 id="research-manifest-title">{t("research.manifest")}</h3>
            <FileCheck2 size={15} aria-hidden="true" />
          </div>
          <dl className="detail-list">
            <div>
              <dt>{t("research.manifest")}</dt>
              <dd>{projection.manifest.manifestId}</dd>
            </div>
            <div>
              <dt>{t("research.scenarioSeed")}</dt>
              <dd>
                {localize(projection.manifest.scenarioId)} /{" "}
                {projection.manifest.seed ?? localize("unavailable")}
              </dd>
            </div>
            <div>
              <dt>{t("research.codeVersion")}</dt>
              <dd>{projection.manifest.codeVersion}</dd>
            </div>
            <div>
              <dt>{t("research.referenceData")}</dt>
              <dd>{localize(projection.manifest.referenceDataId)}</dd>
            </div>
            <div>
              <dt>{t("research.strategies")}</dt>
              <dd>{projection.manifest.strategies.join(", ") || "unavailable"}</dd>
            </div>
          </dl>
        </section>
        <section className="research-center-block" aria-labelledby="research-observations-title">
          <div className="decision-xray-block-heading">
            <h3 id="research-observations-title">{t("research.observations")}</h3>
            <span>{projection.observations.length}</span>
          </div>
          <ul className="research-observations">
            {projection.observations.map((observation) => (
              <li key={observation.label}>
                <div>
                  <strong>{localize(observation.label)}</strong>
                  <span>{localize(observation.category)}</span>
                </div>
                <p>{localize(observation.value)}</p>
                <small>{localize(observation.evidence)}</small>
              </li>
            ))}
          </ul>
        </section>
      </div>
      <div className="research-center-grid">
        <section className="research-center-block" aria-labelledby="research-lineage-title">
          <div className="decision-xray-block-heading">
            <h3 id="research-lineage-title">{t("research.lineage")}</h3>
            <GitBranch size={15} aria-hidden="true" />
          </div>
          <ol className="research-lineage-list">
            {projection.lineage.map((item) => (
              <li key={item}>{localize(item)}</li>
            ))}
          </ol>
        </section>
        <section className="research-center-block" aria-labelledby="research-artifacts-title">
          <div className="decision-xray-block-heading">
            <h3 id="research-artifacts-title">{t("research.artifacts")}</h3>
            <Database size={15} aria-hidden="true" />
          </div>
          {projection.artifacts.length ? (
            <ul className="research-artifacts">
              {projection.artifacts.map((artifact) => (
                <li key={`${artifact.label}-${artifact.digest}`}>
                  <strong>{artifact.label}</strong>
                  <span>{artifact.role}</span>
                  <code>{artifact.digest.slice(0, 16)}</code>
                </li>
              ))}
            </ul>
          ) : (
            <p className="empty-state">{t("research.noArtifacts")}</p>
          )}
        </section>
      </div>
    </section>
  );
}
