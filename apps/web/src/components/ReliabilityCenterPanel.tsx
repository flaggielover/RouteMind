import { Activity, AlertTriangle, CheckCircle2, ShieldAlert } from "lucide-react";
import { useMemo } from "react";
import type { RealtimeConnectionState } from "../data/realtime";
import type { OperationsSnapshot, ServiceHealth } from "../domain/model";
import { projectReliabilityCenter } from "../domain/reliabilityCenter";

export function ReliabilityCenterPanel({
  snapshot,
  health,
  realtime,
}: {
  snapshot: OperationsSnapshot;
  health: readonly ServiceHealth[];
  realtime: RealtimeConnectionState;
}) {
  const projection = useMemo(
    () => projectReliabilityCenter(snapshot, health, realtime),
    [snapshot, health, realtime],
  );
  const icon =
    projection.status === "healthy" ? (
      <CheckCircle2 size={16} aria-hidden="true" />
    ) : (
      <AlertTriangle size={16} aria-hidden="true" />
    );
  return (
    <section className="panel reliability-center-panel" aria-label="Reliability Center">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Reliability Center / read-only evidence</p>
          <h2>See what is healthy, degraded, or unverified.</h2>
          <p className="panel-subtitle">
            Trace, reconciliation, and recovery evidence stay bounded to the captured source.
          </p>
        </div>
        <Activity size={18} className="heading-icon" aria-hidden="true" />
      </div>
      <div className={`reliability-center-status ${projection.status}`} role="status">
        {icon}
        <strong>{projection.status.toUpperCase()}</strong>
        <span>{projection.statusDetail}</span>
      </div>
      <div className="reliability-center-meta">
        <span>{projection.sourceLabel}</span>
        <span>Checked {projection.generatedAt || "unavailable"}</span>
        <span>Trace {projection.traceId ?? "unavailable"}</span>
      </div>
      <div className="reliability-center-grid">
        <section className="reliability-center-block" aria-labelledby="reliability-timeline-title">
          <div className="decision-xray-block-heading">
            <h3 id="reliability-timeline-title">Reliability timeline</h3>
            <span>{projection.timeline.length} events</span>
          </div>
          <ol className="reliability-timeline">
            {projection.timeline.map((event) => (
              <li key={`${event.label}-${event.at}`}>
                <span className={`reliability-state ${event.status}`}>{event.status}</span>
                <div>
                  <strong>{event.label}</strong>
                  <small>{event.at || "time unavailable"}</small>
                  <p>{event.detail}</p>
                  <code>trace {event.traceId ?? "unavailable"}</code>
                </div>
              </li>
            ))}
          </ol>
        </section>
        <section
          className="reliability-center-block"
          aria-labelledby="reliability-invariants-title"
        >
          <div className="decision-xray-block-heading">
            <h3 id="reliability-invariants-title">Invariant matrix</h3>
            <ShieldAlert size={15} aria-hidden="true" />
          </div>
          <div className="reliability-invariants">
            {projection.invariants.map((check) => (
              <article key={check.name}>
                <div>
                  <strong>{check.name}</strong>
                  <span className={`reliability-state ${check.status}`}>{check.status}</span>
                </div>
                <small>
                  {check.inspected === null
                    ? "Inspected count unavailable"
                    : `${check.inspected} inspected`}
                </small>
                <p>{check.evidence}</p>
              </article>
            ))}
          </div>
        </section>
      </div>
      <div className="reliability-center-grid">
        <section
          className="reliability-center-block"
          aria-labelledby="reliability-dependencies-title"
        >
          <div className="decision-xray-block-heading">
            <h3 id="reliability-dependencies-title">Dependencies and trace links</h3>
            <span>{projection.dependencies.length} records</span>
          </div>
          <ul className="reliability-dependencies">
            {projection.dependencies.map((dependency) => (
              <li key={dependency.label}>
                <div>
                  <strong>{dependency.label}</strong>
                  <span className={`reliability-state ${dependency.status}`}>
                    {dependency.status}
                  </span>
                </div>
                <small>
                  {dependency.endpoint} · {dependency.checkedAt || "checked at unavailable"}
                </small>
                <p>{dependency.detail}</p>
              </li>
            ))}
          </ul>
        </section>
        <section className="reliability-center-block" aria-labelledby="reliability-recovery-title">
          <div className="decision-xray-block-heading">
            <h3 id="reliability-recovery-title">Recovery evidence</h3>
            <span>bounded actions</span>
          </div>
          <ul className="reliability-dependencies">
            {projection.recovery.map((item) => (
              <li key={item.label}>
                <div>
                  <strong>{item.label}</strong>
                  <span className={`reliability-state ${item.status}`}>{item.status}</span>
                </div>
                <p>{item.detail}</p>
                <code>trace {item.traceId ?? "unavailable"}</code>
              </li>
            ))}
          </ul>
        </section>
      </div>
    </section>
  );
}
