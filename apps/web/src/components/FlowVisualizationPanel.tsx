import { ArrowDownRight, ArrowUpRight, Info, Route, Waves } from "lucide-react";
import { useMemo, useState } from "react";
import type { OperationsSnapshot } from "../domain/model";
import {
  projectDataBackedFlows,
  type FlowArc,
  type FlowDirection,
} from "../domain/flowVisualization";

interface FlowVisualizationPanelProps {
  snapshot: OperationsSnapshot;
  now?: Date;
}

export function FlowVisualizationPanel({ snapshot, now }: FlowVisualizationPanelProps) {
  const projection = useMemo(() => projectDataBackedFlows(snapshot, now), [snapshot, now]);
  const [selectedFlowId, setSelectedFlowId] = useState<string | null>(null);
  const selectedFlow =
    projection.flows.find((flow) => flow.flowId === selectedFlowId) ?? projection.flows[0];
  const freshnessLabel =
    projection.freshness === "fresh"
      ? "Fresh snapshot"
      : projection.freshness === "stale"
        ? "Stale snapshot"
        : projection.freshness === "empty"
          ? "Empty source"
          : "Source unavailable";

  return (
    <section className="panel flow-panel" aria-labelledby="flow-title">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">
            {projection.sourceLabel} · {freshnessLabel}
          </p>
          <h2 id="flow-title">Data-backed flow visualization</h2>
        </div>
        <span className="panel-meta">Digest {projection.projectionDigest.slice(0, 10)}</span>
      </div>
      <div className="flow-summary" aria-label="Flow projection summary">
        <span>
          <strong>{projection.representedOrders}</strong>
          <small>orders represented</small>
        </span>
        <span>
          <strong>{projection.flows.length}</strong>
          <small>directional flows</small>
        </span>
        <span>
          <strong>{projection.routeBearingOrders}</strong>
          <small>route records</small>
        </span>
        <span>
          <strong>
            {projection.flows.length
              ? `${Math.round(averageConfidence(projection.flows) * 100)}%`
              : "-"}
          </strong>
          <small>mean confidence</small>
        </span>
      </div>
      {projection.flows.length ? (
        <>
          <div className="flow-visual-grid">
            <div
              className="flow-canvas-wrap"
              role="img"
              aria-label={`Order flows derived from ${projection.routeBearingOrders} route-bearing order records`}
            >
              <svg className="flow-canvas" viewBox="0 0 100 100" role="presentation">
                <title>Order flow arcs derived from route records</title>
                <defs>
                  <marker
                    id="flow-arrow"
                    markerWidth="7"
                    markerHeight="7"
                    refX="6"
                    refY="3.5"
                    orient="auto"
                  >
                    <path d="M0,0 L7,3.5 L0,7 z" fill="currentColor" />
                  </marker>
                </defs>
                <rect className="flow-map-background" x="0" y="0" width="100" height="100" rx="3" />
                {[20, 40, 60, 80].map((position) => (
                  <line
                    className="flow-map-gridline"
                    key={`vertical-${position}`}
                    x1={position}
                    y1="0"
                    x2={position}
                    y2="100"
                  />
                ))}
                {[20, 40, 60, 80].map((position) => (
                  <line
                    className="flow-map-gridline"
                    key={`horizontal-${position}`}
                    x1="0"
                    y1={position}
                    x2="100"
                    y2={position}
                  />
                ))}
                {projection.flows.map((flow) => {
                  const selected = selectedFlow?.flowId === flow.flowId;
                  const controlX = (flow.sourcePoint.x + flow.targetPoint.x) / 2;
                  const controlY = Math.max(8, (flow.sourcePoint.y + flow.targetPoint.y) / 2 - 16);
                  return (
                    <g key={flow.flowId} className={selected ? "flow-arc selected" : "flow-arc"}>
                      <path
                        d={`M ${flow.sourcePoint.x} ${flow.sourcePoint.y} Q ${controlX} ${controlY} ${flow.targetPoint.x} ${flow.targetPoint.y}`}
                        strokeWidth={1.5 + Math.min(4, flow.orderCount)}
                        markerEnd="url(#flow-arrow)"
                      />
                      <circle cx={flow.sourcePoint.x} cy={flow.sourcePoint.y} r="2.4" />
                      <circle cx={flow.targetPoint.x} cy={flow.targetPoint.y} r="2.4" />
                    </g>
                  );
                })}
              </svg>
              <div className="flow-map-labels" aria-hidden="true">
                <span>source area</span>
                <span>destination area</span>
              </div>
            </div>
            <div className="flow-list" aria-label="Analytical flow records">
              {projection.flows.map((flow) => (
                <button
                  className={`flow-item ${selectedFlow?.flowId === flow.flowId ? "selected" : ""}`}
                  key={flow.flowId}
                  type="button"
                  aria-pressed={selectedFlow?.flowId === flow.flowId}
                  onClick={() => setSelectedFlowId(flow.flowId)}
                >
                  <span className="flow-item-icon" aria-hidden="true">
                    {directionIcon(flow.direction)}
                  </span>
                  <span className="flow-item-copy">
                    <strong>
                      {flow.sourceZone} <span aria-hidden="true">→</span> {flow.targetZone}
                    </strong>
                    <small>
                      {flow.orderCount} orders · {directionLabel(flow.direction)}
                    </small>
                  </span>
                  <span className="flow-item-side">
                    <strong>{Math.round(flow.confidence * 100)}%</strong>
                    <small>confidence</small>
                  </span>
                </button>
              ))}
            </div>
          </div>
          {selectedFlow && <FlowEvidence flow={selectedFlow} />}
        </>
      ) : (
        <div className="flow-empty-state" role="status">
          <Waves size={18} aria-hidden="true" />
          <span>{projection.emptyReason ?? "No flow records are available from this source."}</span>
        </div>
      )}
      <div className="flow-footnote">
        <Info size={13} aria-hidden="true" />
        <span>
          Arcs are derived from {projection.derivedFrom.replaceAll("-", " ")}; volume is orders,
          recency is minutes since snapshot, and confidence is bounded 0-100%.
        </span>
      </div>
    </section>
  );
}

function FlowEvidence({ flow }: { flow: FlowArc }) {
  return (
    <section className="flow-evidence" aria-labelledby="flow-evidence-title">
      <div>
        <p className="eyebrow">Selected flow evidence</p>
        <h3 id="flow-evidence-title">
          Selected flow evidence: {flow.sourceZone} <span aria-hidden="true">→</span>{" "}
          {flow.targetZone}
        </h3>
      </div>
      <dl className="flow-evidence-grid">
        <div>
          <dt>Volume</dt>
          <dd>{flow.orderCount} orders</dd>
        </div>
        <div>
          <dt>Direction</dt>
          <dd>{directionLabel(flow.direction)}</dd>
        </div>
        <div>
          <dt>Recency</dt>
          <dd>{flow.recencyMinutes === null ? "Unavailable" : `${flow.recencyMinutes} min`}</dd>
        </div>
        <div>
          <dt>Evidence</dt>
          <dd>{flow.evidenceOrderIds.length} order records</dd>
        </div>
      </dl>
      <p className="flow-evidence-note">
        {flow.evidenceOrderIds.join(", ")} · coordinates averaged from each route endpoint
      </p>
    </section>
  );
}

function averageConfidence(flows: readonly FlowArc[]): number {
  return flows.reduce((sum, flow) => sum + flow.confidence, 0) / flows.length;
}

function directionLabel(direction: FlowDirection): string {
  return direction.replace("bound", "bound");
}

function directionIcon(direction: FlowDirection) {
  return direction === "northbound" || direction === "eastbound" ? (
    <ArrowUpRight size={15} />
  ) : direction === "southbound" || direction === "westbound" ? (
    <ArrowDownRight size={15} />
  ) : (
    <Route size={15} />
  );
}
