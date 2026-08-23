import { Activity, BarChart3, Clock3, Database, Radio } from "lucide-react";
import { useMemo } from "react";
import type { OperationsSnapshot } from "../domain/model";
import { projectTwinVisualization } from "../domain/twinVisualization";

export function TwinVisualizationPanel({ snapshot }: { snapshot: OperationsSnapshot }) {
  const projection = useMemo(() => projectTwinVisualization(snapshot), [snapshot]);
  return (
    <section
      className="panel twin-visualization-panel"
      aria-label="Digital Twin visualization center"
    >
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Digital Twin / bounded visualization</p>
          <h2>Compare clock, state, and replay provenance.</h2>
          <p className="panel-subtitle">{projection.detail}</p>
        </div>
        <Activity size={18} className="heading-icon" aria-hidden="true" />
      </div>
      <div className="twin-mode-strip" aria-label="Twin execution modes">
        {projection.modes.map((mode) => (
          <div className={`twin-mode ${mode.status}`} key={mode.mode}>
            <strong>{mode.mode}</strong>
            <span>{mode.status}</span>
            <small>{mode.detail}</small>
          </div>
        ))}
      </div>
      <div className="twin-visualization-meta">
        <span>
          <Radio size={14} aria-hidden="true" /> {projection.sourceLabel}
        </span>
        <span>
          <Clock3 size={14} aria-hidden="true" /> {projection.clockDomain}
        </span>
        <span>
          <Database size={14} aria-hidden="true" /> {projection.scenarioId}
        </span>
        <span>Seed {projection.seed}</span>
        <span>Speed {projection.speed.toFixed(1)}x</span>
        <code>
          {projection.replayDigest ? projection.replayDigest.slice(0, 16) : "digest unavailable"}
        </code>
      </div>
      <div className="twin-visualization-grid">
        <section className="twin-state-chart" aria-labelledby="twin-state-title">
          <div className="decision-xray-block-heading">
            <h3 id="twin-state-title">State progression</h3>
            <BarChart3 size={15} aria-hidden="true" />
          </div>
          {projection.stateBars.map((bar) => (
            <div className="twin-state-bar" key={bar.label}>
              <div>
                <strong>{bar.label}</strong>
                <span>{bar.detail}</span>
              </div>
              <div className="twin-state-track">
                <span style={{ width: `${bar.value}%` }} />
              </div>
            </div>
          ))}
          <small className="twin-event-count">
            {projection.eventCount} recorded events · bounded display shows{" "}
            {projection.timeline.length}
          </small>
        </section>
        <section className="twin-timeline" aria-labelledby="twin-timeline-title">
          <div className="decision-xray-block-heading">
            <h3 id="twin-timeline-title">Event timeline</h3>
            <span>{projection.timeline.length} latest</span>
          </div>
          {projection.timeline.length ? (
            <ol>
              {projection.timeline.map((event) => (
                <li key={event.eventId}>
                  <span>timeline · {event.eventType.replaceAll(".", " / ")}</span>
                  <small>
                    t+{event.seconds.toFixed(0)}s · {event.detail}
                  </small>
                </li>
              ))}
            </ol>
          ) : (
            <p className="empty-state">No simulation or replay events are attached.</p>
          )}
        </section>
      </div>
    </section>
  );
}
