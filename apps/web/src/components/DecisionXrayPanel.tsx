import { AlertCircle, CheckCircle2, GitBranch, ShieldCheck, Waypoints } from "lucide-react";
import { useMemo } from "react";
import type { OperationsSnapshot } from "../domain/model";
import { projectDecisionXray } from "../domain/decisionXray";

interface DecisionXrayPanelProps {
  snapshot: OperationsSnapshot;
  replayedSnapshot?: OperationsSnapshot;
}

function digest(value: string | null): string {
  return value ? value.slice(0, 16) : "unavailable";
}

export function DecisionXrayPanel({ snapshot, replayedSnapshot }: DecisionXrayPanelProps) {
  const projection = useMemo(
    () => projectDecisionXray(snapshot, replayedSnapshot),
    [snapshot, replayedSnapshot],
  );
  const verificationIcon =
    projection.verification.status === "passed" ? (
      <CheckCircle2 size={15} aria-hidden="true" />
    ) : (
      <AlertCircle size={15} aria-hidden="true" />
    );

  return (
    <section className="panel decision-xray-panel" aria-labelledby="decision-xray-title">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">
            {projection.sourceLabel} ·{" "}
            {projection.authority === "durable-ledger"
              ? "Java durable ledger"
              : "read-only snapshot projection"}
          </p>
          <h2 id="decision-xray-title">Decision X-Ray</h2>
          <p className="panel-subtitle">
            Inspectable provenance, candidate constraints, and bounded replay evidence.
          </p>
        </div>
        <Waypoints size={18} className="heading-icon" aria-hidden="true" />
      </div>

      <div className="decision-xray-summary">
        <strong>{projection.summary}</strong>
        <span>
          {snapshot.availability === "ready"
            ? projection.sourceDetail
            : "Degraded or unavailable source; inspect projection health for the current detail."}
        </span>
      </div>

      <dl className="decision-xray-meta" aria-label="Decision provenance">
        <div>
          <dt>Decision ID</dt>
          <dd>
            <code>{projection.decisionId}</code>
          </dd>
        </div>
        <div>
          <dt>Request / clock</dt>
          <dd>
            {projection.provenance.requestId} · {projection.provenance.clockDomain}
          </dd>
        </div>
        <div>
          <dt>Reference data</dt>
          <dd>{projection.provenance.referenceDataId}</dd>
        </div>
        <div>
          <dt>Recorded at</dt>
          <dd>{projection.provenance.recordedAt || "unavailable"}</dd>
        </div>
      </dl>

      <div className="decision-xray-grid">
        <section className="decision-xray-block" aria-labelledby="decision-xray-action">
          <div className="decision-xray-block-heading">
            <h3 id="decision-xray-action">Selected action</h3>
            <span className="status-pill status-healthy">
              <span>{projection.selectedAction.strategy}</span>
            </span>
          </div>
          <dl className="detail-list">
            <div>
              <dt>Courier</dt>
              <dd>{projection.selectedAction.courierId}</dd>
            </div>
            <div>
              <dt>Strategy version</dt>
              <dd>{projection.selectedAction.strategyVersion}</dd>
            </div>
            <div>
              <dt>Rationale</dt>
              <dd>{projection.selectedAction.rationale}</dd>
            </div>
          </dl>
        </section>

        <section className="decision-xray-block" aria-labelledby="decision-xray-objective">
          <div className="decision-xray-block-heading">
            <h3 id="decision-xray-objective">Objective / risk</h3>
            <ShieldCheck size={15} aria-hidden="true" />
          </div>
          <dl className="detail-list">
            <div>
              <dt>{projection.objective.label}</dt>
              <dd>
                {projection.objective.value === null
                  ? "unavailable"
                  : Math.round(projection.objective.value * 100) + "%"}
              </dd>
            </div>
            <div>
              <dt>Risk</dt>
              <dd>{projection.risk.score === null ? "unavailable" : projection.risk.level}</dd>
            </div>
            <div>
              <dt>Evidence</dt>
              <dd>{projection.risk.evidence}</dd>
            </div>
          </dl>
        </section>
      </div>

      <section className="decision-xray-section" aria-labelledby="decision-xray-candidates">
        <div className="decision-xray-block-heading">
          <h3 id="decision-xray-candidates">Candidates and rejection reasons</h3>
          <span>{projection.candidates.length} captured</span>
        </div>
        {projection.candidates.length ? (
          <div className="decision-xray-candidates">
            {projection.candidates.map((item) => (
              <article className="decision-xray-candidate" key={item.courierId}>
                <div>
                  <strong>{item.courierId}</strong>
                  <small>
                    {item.zone} · {item.status.replace("_", " ")}
                  </small>
                </div>
                <span className={"decision-xray-candidate-status " + item.eligibility}>
                  {item.eligibility}
                </span>
                <p>
                  {item.rejectionReasons.length
                    ? item.rejectionReasons.join("; ")
                    : item.eligibility === "selected"
                      ? "Selected action"
                      : "No captured rejection reason"}
                </p>
              </article>
            ))}
          </div>
        ) : (
          <p className="empty-state">No courier candidates are present in this source.</p>
        )}
      </section>

      <div className="decision-xray-grid">
        <section className="decision-xray-block" aria-labelledby="decision-xray-travel">
          <div className="decision-xray-block-heading">
            <h3 id="decision-xray-travel">Travel evidence</h3>
            <span className={"decision-xray-state " + projection.travel.status}>
              {projection.travel.status}
            </span>
          </div>
          <p className="decision-xray-copy">{projection.travel.summary}</p>
          <small>Evidence: {projection.travel.evidence}</small>
        </section>
        <section className="decision-xray-block" aria-labelledby="decision-xray-verification">
          <div className="decision-xray-block-heading">
            <h3 id="decision-xray-verification">Verification</h3>
            <span className={"decision-xray-state " + projection.verification.status}>
              {verificationIcon}
              {projection.verification.status}
            </span>
          </div>
          <p className="decision-xray-copy">{projection.verification.summary}</p>
          <ul className="decision-xray-checks">
            {projection.verification.checks.map((check) => (
              <li key={check}>{check}</li>
            ))}
          </ul>
        </section>
      </div>

      <section className="decision-xray-section" aria-labelledby="decision-xray-digests">
        <div className="decision-xray-block-heading">
          <h3 id="decision-xray-digests">Digests and bounded replay</h3>
          <GitBranch size={15} aria-hidden="true" />
        </div>
        <div className="decision-xray-digests">
          <span>
            decision <code>{digest(projection.digests.decision)}</code>
          </span>
          <span>
            input <code>{digest(projection.digests.input)}</code>
          </span>
          <span>
            output <code>{digest(projection.digests.output)}</code>
          </span>
          <span>
            replay <strong>{projection.replay.status}</strong>
          </span>
        </div>
        <p className="decision-xray-copy">{projection.replay.summary}</p>
        <small>
          {projection.replay.bounded
            ? "Replay is bounded to the captured snapshot and does not mutate durable state."
            : "Replay bound is unavailable."}
        </small>
        {projection.alternatives.length ? (
          <p className="decision-xray-alternatives">
            Alternatives captured: {projection.alternatives.join(", ")}
          </p>
        ) : (
          <p className="decision-xray-alternatives">No eligible alternatives captured.</p>
        )}
      </section>
    </section>
  );
}
