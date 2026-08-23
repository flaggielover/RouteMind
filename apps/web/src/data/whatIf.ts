import type { WhatIfComparison, WhatIfVariantInput } from "../domain/model";

interface WhatIfMetricWire {
  variant_id: string;
  label: string;
  strategy: string;
  strategy_version: string;
  request_count: number;
  assigned_count: number;
  assignment_rate: number;
  simulated_end_tick: number;
  simulated_duration_seconds: number;
  risk_index: number;
  replay_digest: string;
  manifest_digest: string;
  output_digest: string;
  observed_runtime_millis: number;
}

interface WhatIfResponseWire {
  source: "what-if";
  claim_label: "scenario comparison; not a causal production claim";
  recorded_run_id: string;
  comparison_digest: string;
  scenario_id: string;
  seed: number;
  results: WhatIfMetricWire[];
}

const computeApi = import.meta.env.VITE_COMPUTE_API_URL ?? "http://localhost:18081";
const timeoutMs = 4_000;

const recordedRunId = "replay-control-default-v1";

const basePayload = {
  recorded_run_id: recordedRunId,
  baseline_strategy: "nearest",
  manifest_id: "what-if-control-default-v1",
  code_version: "web-local-v1",
  scenario_id: "control-default",
  seed: 7,
  load_profile: "web-control-default",
  city_state: "local-fixture",
  dataset_provenance: `recorded-run:${recordedRunId}`,
  strategies: ["nearest", "weighted-greedy"],
  demands: [
    {
      request_id: "order-1",
      pickup: { latitude: 31.2304, longitude: 121.4737 },
      tick: 0,
      zone: "central",
      merchant_id: "merchant-1",
      order_profile: "standard",
    },
    {
      request_id: "order-2",
      pickup: { latitude: 31.2305, longitude: 121.4738 },
      tick: 1,
      zone: "central",
      merchant_id: "merchant-1",
      order_profile: "priority",
    },
  ],
  couriers: [
    {
      courier_id: "courier-1",
      location: { latitude: 31.22, longitude: 121.48 },
      available_tick: 0,
    },
    {
      courier_id: "courier-2",
      location: { latitude: 31.24, longitude: 121.46 },
      available_tick: 0,
    },
  ],
  delay_ticks: [0],
  traffic_multiplier: 1,
} as const;

async function fetchJson<T>(url: string, init: RequestInit, fetchImpl: typeof fetch): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetchImpl(url, { ...init, signal: controller.signal });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return (await response.json()) as T;
  } finally {
    clearTimeout(timeout);
  }
}

function asComparison(wire: WhatIfResponseWire): WhatIfComparison {
  return {
    source: wire.source,
    claimLabel: wire.claim_label,
    recordedRunId: wire.recorded_run_id,
    comparisonDigest: wire.comparison_digest,
    scenarioId: wire.scenario_id,
    seed: wire.seed,
    results: wire.results.map((result) => ({
      variantId: result.variant_id,
      label: result.label,
      strategy: result.strategy,
      strategyVersion: result.strategy_version,
      requestCount: result.request_count,
      assignedCount: result.assigned_count,
      assignmentRate: result.assignment_rate,
      simulatedEndTick: result.simulated_end_tick,
      simulatedDurationSeconds: result.simulated_duration_seconds,
      riskIndex: result.risk_index,
      replayDigest: result.replay_digest,
      manifestDigest: result.manifest_digest,
      outputDigest: result.output_digest,
      observedRuntimeMillis: result.observed_runtime_millis,
    })),
  };
}

export function createWhatIfDataSource(fetchImpl: typeof fetch = fetch) {
  return {
    run: async (variant: WhatIfVariantInput): Promise<WhatIfComparison> => {
      const wire = await fetchJson<WhatIfResponseWire>(
        `${computeApi}/api/v1/experiments/what-if`,
        {
          method: "POST",
          headers: { Accept: "application/json", "Content-Type": "application/json" },
          body: JSON.stringify({
            ...basePayload,
            variants: [
              {
                variant_id: variant.variantId,
                label: variant.label,
                demand_multiplier: variant.demandMultiplier,
                supply_delta: variant.supplyDelta,
                preparation_delay_ticks: variant.preparationDelayTicks,
                traffic_multiplier: variant.trafficMultiplier,
                strategy: variant.strategy,
                risk_multiplier: variant.riskMultiplier,
              },
            ],
          }),
        },
        fetchImpl,
      );
      return asComparison(wire);
    },
  };
}

export const whatIfDataSource = createWhatIfDataSource();
