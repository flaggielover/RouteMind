import { describe, expect, it } from "vitest";
import { loadLiveSnapshot, replayDataSource } from "./liveSnapshot";

function response(body: unknown, ok = true): Response {
  return new Response(JSON.stringify(body), {
    status: ok ? 200 : 503,
    headers: { "Content-Type": "application/json" },
  });
}

describe("live product data boundary", () => {
  it("composes Java durable state and Python dispatch as live data", async () => {
    const snapshot = await loadLiveSnapshot(async (input) => {
      const url = String(input);
      if (url.includes("operations")) {
        return response({
          source: "live",
          generatedAt: "2026-08-22T10:00:00Z",
          orders: [],
          parties: [
            { id: "merchant-1", type: "MERCHANT", displayName: "Local Merchant", status: "ACTIVE" },
          ],
          courierLocations: [
            {
              courierId: "courier-1",
              latitude: 31.2,
              longitude: 121.4,
              observedAt: "2026-08-22T10:00:00Z",
              ingestedAt: "2026-08-22T10:00:01Z",
              sequence: 7,
              online: true,
            },
          ],
        });
      }
      return response({
        source: "live",
        strategy: "nearest",
        strategy_version: "1.0.0",
        selected_courier: "courier-1",
        score: 1.2,
        rationale: ["lowest distance"],
        latency_millis: 2,
        trace_id: "trace-1",
      });
    });

    expect(snapshot.source).toBe("live");
    expect(snapshot.availability).toBe("ready");
    expect(snapshot.merchants[0]?.name).toBe("Local Merchant");
    expect(snapshot.dispatch.selectedCourier).toBe("courier-1");
    expect(snapshot.couriers[0]).toMatchObject({ sequence: 7, online: true, stale: false });
  });

  it("keeps service failure explicit instead of falling back to demo", async () => {
    const snapshot = await loadLiveSnapshot(async () => response({ error: "unavailable" }, false));

    expect(snapshot.source).toBe("live");
    expect(snapshot.availability).toBe("unavailable");
    expect(snapshot.orders).toHaveLength(0);
    expect(snapshot.sourceDetail).toContain("Live unavailable");
  });

  it("exposes replay as a distinct empty mode until an artifact is verified", () => {
    const snapshot = replayDataSource.getSnapshot();

    expect(snapshot.source).toBe("replay");
    expect(snapshot.availability).toBe("unavailable");
    expect(snapshot.sourceDetail).toContain("verified replay");
  });
});
