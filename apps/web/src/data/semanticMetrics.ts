export type SemanticMetricConsumer = "web" | "report" | "agent";
export type SemanticMetricValueType = "count" | "ratio";

interface SemanticMetricDefinitionWire {
  name: string;
  display_name: string;
  description: string;
  unit: string;
  value_type: SemanticMetricValueType;
  source_view: string;
  source_fields: string[];
  aggregation: string;
  numerator: string;
  denominator: string | null;
  time_semantics: string;
  unavailable_when: string;
  consumers: SemanticMetricConsumer[];
  definition_digest: string;
}

export interface SemanticMetricDefinition {
  name: string;
  displayName: string;
  description: string;
  unit: string;
  valueType: SemanticMetricValueType;
  sourceView: string;
  sourceFields: readonly string[];
  aggregation: string;
  numerator: string;
  denominator: string | null;
  timeSemantics: string;
  unavailableWhen: string;
  consumers: readonly SemanticMetricConsumer[];
  definitionDigest: string;
}

const computeApi = import.meta.env.VITE_COMPUTE_API_URL ?? "http://localhost:18081";

function asDefinition(wire: SemanticMetricDefinitionWire): SemanticMetricDefinition {
  return {
    name: wire.name,
    displayName: wire.display_name,
    description: wire.description,
    unit: wire.unit,
    valueType: wire.value_type,
    sourceView: wire.source_view,
    sourceFields: wire.source_fields,
    aggregation: wire.aggregation,
    numerator: wire.numerator,
    denominator: wire.denominator,
    timeSemantics: wire.time_semantics,
    unavailableWhen: wire.unavailable_when,
    consumers: wire.consumers,
    definitionDigest: wire.definition_digest,
  };
}

export function createSemanticMetricCatalog(fetchImpl: typeof fetch = fetch) {
  return {
    list: async (): Promise<readonly SemanticMetricDefinition[]> => {
      const response = await fetchImpl(
        `${computeApi}/api/v1/analytics/metrics/catalog?consumer=web`,
        { headers: { Accept: "application/json" } },
      );
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const wire = (await response.json()) as SemanticMetricDefinitionWire[];
      return wire.map(asDefinition);
    },
  };
}

export const semanticMetricCatalog = createSemanticMetricCatalog();
