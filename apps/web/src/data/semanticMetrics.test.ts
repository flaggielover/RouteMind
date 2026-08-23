import { describe, expect, it, vi } from "vitest";
import { createSemanticMetricCatalog } from "./semanticMetrics";

describe("semantic metric catalog", () => {
  it("requests the shared web catalog and maps definition lineage", async () => {
    const fetchImpl = vi.fn<typeof fetch>().mockResolvedValue({
      ok: true,
      json: async () => [
        {
          name: "dispatch_assignment_rate",
          display_name: "Dispatch assignment rate",
          description: "Assigned decisions divided by all decisions.",
          unit: "ratio",
          value_type: "ratio",
          source_view: "fact_decision",
          source_fields: ["event_time", "payload.selected_courier"],
          aggregation: "assigned divided by all decisions",
          numerator: "assigned decisions",
          denominator: "all decisions",
          time_semantics: "UTC half-open event-time window",
          unavailable_when: "no decisions exist",
          consumers: ["web", "report", "agent"],
          definition_digest: "a".repeat(64),
        },
      ],
    } as Response);

    const definitions = await createSemanticMetricCatalog(fetchImpl).list();

    expect(fetchImpl).toHaveBeenCalledWith(
      expect.stringContaining("/analytics/metrics/catalog?consumer=web"),
      { headers: { Accept: "application/json" } },
    );
    expect(definitions[0]).toMatchObject({
      name: "dispatch_assignment_rate",
      sourceView: "fact_decision",
      definitionDigest: "a".repeat(64),
      consumers: ["web", "report", "agent"],
    });
  });

  it("surfaces catalog failures", async () => {
    const fetchImpl = vi
      .fn<typeof fetch>()
      .mockResolvedValue({ ok: false, status: 503 } as Response);

    await expect(createSemanticMetricCatalog(fetchImpl).list()).rejects.toThrow("HTTP 503");
  });
});
