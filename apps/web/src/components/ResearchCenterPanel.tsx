import { BookOpen, Database, FileCheck2, FlaskConical, GitBranch } from "lucide-react";
import { useMemo } from "react";
import type { WhatIfComparison, OperationsSnapshot } from "../domain/model";
import { projectResearchCenter } from "../domain/researchCenter";

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
  return (
    <section className="panel research-center-panel" aria-label="Research Center">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Research Center / lineage-first evidence</p>
          <h2>Inspect manifests before making claims.</h2>
          <p className="panel-subtitle">{projection.boundary}</p>
        </div>
        <FlaskConical size={18} className="heading-icon" aria-hidden="true" />
      </div>
      <div className={`research-center-status ${projection.status}`} role="status">
        <BookOpen size={15} aria-hidden="true" />
        <strong>{projection.status}</strong>
        <span>{projection.sourceLabel}</span>
      </div>
      <div className="research-center-grid">
        <section className="research-center-block" aria-labelledby="research-manifest-title">
          <div className="decision-xray-block-heading">
            <h3 id="research-manifest-title">Experiment manifest</h3>
            <FileCheck2 size={15} aria-hidden="true" />
          </div>
          <dl className="detail-list">
            <div>
              <dt>Manifest</dt>
              <dd>{projection.manifest.manifestId}</dd>
            </div>
            <div>
              <dt>Scenario / seed</dt>
              <dd>
                {projection.manifest.scenarioId} / {projection.manifest.seed ?? "unavailable"}
              </dd>
            </div>
            <div>
              <dt>Code version</dt>
              <dd>{projection.manifest.codeVersion}</dd>
            </div>
            <div>
              <dt>Reference data</dt>
              <dd>{projection.manifest.referenceDataId}</dd>
            </div>
            <div>
              <dt>Strategies</dt>
              <dd>{projection.manifest.strategies.join(", ") || "unavailable"}</dd>
            </div>
          </dl>
        </section>
        <section className="research-center-block" aria-labelledby="research-observations-title">
          <div className="decision-xray-block-heading">
            <h3 id="research-observations-title">Observations</h3>
            <span>{projection.observations.length}</span>
          </div>
          <ul className="research-observations">
            {projection.observations.map((observation) => (
              <li key={observation.label}>
                <div>
                  <strong>{observation.label}</strong>
                  <span>{observation.category}</span>
                </div>
                <p>{observation.value}</p>
                <small>{observation.evidence}</small>
              </li>
            ))}
          </ul>
        </section>
      </div>
      <div className="research-center-grid">
        <section className="research-center-block" aria-labelledby="research-lineage-title">
          <div className="decision-xray-block-heading">
            <h3 id="research-lineage-title">Lineage</h3>
            <GitBranch size={15} aria-hidden="true" />
          </div>
          <ol className="research-lineage-list">
            {projection.lineage.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ol>
        </section>
        <section className="research-center-block" aria-labelledby="research-artifacts-title">
          <div className="decision-xray-block-heading">
            <h3 id="research-artifacts-title">Artifact references</h3>
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
            <p className="empty-state">No artifact references are attached.</p>
          )}
        </section>
      </div>
    </section>
  );
}
