import { AlertCircle, Check, Layers3, ShieldCheck } from "lucide-react";
import { useMemo, useState } from "react";
import type { OperationsSnapshot } from "../domain/model";
import {
  projectGeoAnalyticalLayers,
  type GeoLayerDefinition,
  type GeoLayerId,
  type GeoLayerValue,
} from "../domain/geoAnalyticalLayers";

interface GeoAnalyticalLayersPanelProps {
  snapshot: OperationsSnapshot;
  now?: Date;
}

const defaultLayers: readonly GeoLayerId[] = [
  "orders",
  "courier-supply",
  "supply-gap",
  "sla-risk",
  "utilization",
  "flow",
];

export function GeoAnalyticalLayersPanel({ snapshot, now }: GeoAnalyticalLayersPanelProps) {
  const projection = useMemo(() => projectGeoAnalyticalLayers(snapshot, now), [snapshot, now]);
  const [enabled, setEnabled] = useState<GeoLayerId[]>([...defaultLayers]);
  const freshnessLabel =
    projection.freshness === "fresh"
      ? "Fresh snapshot"
      : projection.freshness === "stale"
        ? "Stale snapshot"
        : projection.freshness === "empty"
          ? "Empty source"
          : "Source unavailable";
  const visibleDefinitions = projection.definitions.filter(
    (definition) => definition.availability === "available" && enabled.includes(definition.id),
  );

  const toggleLayer = (definition: GeoLayerDefinition) => {
    if (definition.availability === "unavailable") return;
    setEnabled((current) =>
      current.includes(definition.id)
        ? current.filter((id) => id !== definition.id)
        : [...current, definition.id],
    );
  };

  return (
    <section className="panel geo-layers-panel" aria-labelledby="geo-layers-title">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">
            {projection.sourceLabel} · {freshnessLabel}
          </p>
          <h2 id="geo-layers-title">Geo analytical layers</h2>
        </div>
        <span className="panel-meta">
          <Layers3 size={14} aria-hidden="true" /> {visibleDefinitions.length} active
        </span>
      </div>
      <div className="geo-layers-toolbar">
        <span className="geo-layers-toolbar-label">Toggle evidence-backed layers</span>
        <span className="geo-layers-toolbar-note">
          Each scale is local to the selected snapshot.
        </span>
      </div>
      <div className="geo-layer-toggles" role="group" aria-label="Geo analytical layer toggles">
        {projection.definitions.map((definition) => {
          const available = definition.availability === "available";
          const checked = enabled.includes(definition.id);
          return (
            <label
              className={`geo-layer-toggle ${available ? "" : "unavailable"}`}
              key={definition.id}
            >
              <input
                type="checkbox"
                checked={checked}
                disabled={!available}
                onChange={() => toggleLayer(definition)}
              />
              <span className="geo-layer-toggle-mark" aria-hidden="true">
                {checked && available ? <Check size={12} /> : <span />}
              </span>
              <span className="geo-layer-toggle-copy">
                <strong>{definition.label}</strong>
                <small>{available ? definition.unit : "Unavailable from source"}</small>
              </span>
            </label>
          );
        })}
      </div>
      {projection.freshness !== "fresh" && (
        <div className="geo-layer-state" role="status">
          <AlertCircle size={14} aria-hidden="true" />
          <span>
            {projection.freshness === "stale"
              ? "Snapshot is stale; enabled layers remain visible for inspection."
              : projection.freshness === "empty"
                ? "No source records are available for analytical layers."
                : "Analytical layers are unavailable from this source."}
          </span>
        </div>
      )}
      <div className="geo-layer-stack">
        {visibleDefinitions.length ? (
          visibleDefinitions.map((definition) => (
            <GeoLayerBlock
              key={definition.id}
              definition={definition}
              values={projection.values[definition.id]}
            />
          ))
        ) : (
          <p className="empty-state">Select an available layer to inspect its evidence.</p>
        )}
      </div>
      <p className="geo-layers-footnote">
        <ShieldCheck size={13} aria-hidden="true" />
        <span>
          Disabled layers are not inferred: congestion and travel degradation need provider travel
          metrics; integrity needs courier sequence or freshness metadata.
        </span>
      </p>
    </section>
  );
}

function GeoLayerBlock({
  definition,
  values,
}: {
  definition: GeoLayerDefinition;
  values: readonly GeoLayerValue[];
}) {
  const max = Math.max(1, ...values.map((item) => item.value ?? 0));
  return (
    <section className="geo-layer-block" aria-labelledby={`geo-layer-${definition.id}`}>
      <div className="geo-layer-block-heading">
        <div>
          <p className="eyebrow">{definition.unit}</p>
          <h3 id={`geo-layer-${definition.id}`}>{definition.label}</h3>
        </div>
        <span className="geo-layer-scale">{definition.scale}</span>
      </div>
      <p className="geo-layer-detail">{definition.detail}</p>
      {values.length ? (
        <div className="geo-layer-values">
          {values.map((item) => (
            <div className="geo-layer-value" key={item.key}>
              <div className="geo-layer-value-heading">
                <span>{item.label}</span>
                <strong>
                  {item.displayValue} <small>{definition.unit.split(" /")[0]}</small>
                </strong>
              </div>
              <progress
                max={max}
                value={item.value ?? 0}
                aria-label={`${definition.label} at ${item.label}`}
              />
              <small className="geo-layer-evidence">{item.evidenceCount} source records</small>
            </div>
          ))}
        </div>
      ) : (
        <p className="empty-state">No source records are available for this layer.</p>
      )}
    </section>
  );
}
