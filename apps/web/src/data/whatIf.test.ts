import { describe, expect, it, vi } from "vitest";
import { createWhatIfDataSource } from "./whatIf";

function response(body: unknown): Response {
  return { ok: true, json: async () => body } as Response;
}

const result = {
  variant_id: "baseline",
  label: "Recorded baseline",
  strategy: "nearest",
  strategy_version: "1.0.0",
  request_count: 2,
  assigned_count: 2,
  assignment_rate: 1,
  simulated_end_tick: 1,
  simulated_duration_seconds: 60,
  risk_index: 0,
  replay_digest: "replay-digest",
  manifest_digest: "manifest-digest",
  output_digest: "output-digest",
  observed_runtime_millis: 1,
};

describe("what-if data source", () => {
  it("serializes a bounded variant and maps provenance results", async () => {
    const fetchImpl = vi.fn<typeof fetch>().mockResolvedValue(
      response({
        source: "what-if",
        claim_label: "scenario comparison; not a causal production claim",
        recorded_run_id: "replay-control-default-v1",
        comparison_digest: "comparison-digest",
        scenario_id: "control-default",
        seed: 7,
        results: [result],
      }),
    );
    const source = createWhatIfDataSource(fetchImpl);
    const comparison = await source.run({
      variantId: "stress",
      label: "Traffic stress",
      demandMultiplier: 1.2,
      supplyDelta: -1,
      preparationDelayTicks: 2,
      trafficMultiplier: 1.4,
      strategy: "weighted-greedy",
      riskMultiplier: 1.5,
    });

    expect(comparison.claimLabel).toContain("not a causal");
    expect(comparison.results[0].manifestDigest).toBe("manifest-digest");
    const request = fetchImpl.mock.calls[0][1] as RequestInit;
    const body = JSON.parse(String(request.body)) as {
      recorded_run_id: string;
      variants: [{ strategy: string; supply_delta: number }];
    };
    expect(body.recorded_run_id).toBe("replay-control-default-v1");
    expect(body.variants[0].strategy).toBe("weighted-greedy");
    expect(body.variants[0].supply_delta).toBe(-1);
  });

  it("surfaces API failures", async () => {
    const source = createWhatIfDataSource(
      vi.fn<typeof fetch>().mockResolvedValue({ ok: false, status: 422 } as Response),
    );
    await expect(
      source.run({
        variantId: "stress",
        label: "Stress",
        demandMultiplier: 1,
        supplyDelta: 0,
        preparationDelayTicks: 0,
        trafficMultiplier: 1,
        strategy: "nearest",
        riskMultiplier: 1,
      }),
    ).rejects.toThrow("HTTP 422");
  });
});
