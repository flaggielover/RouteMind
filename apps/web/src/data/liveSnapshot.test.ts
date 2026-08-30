import { describe, expect, it } from "vitest";
import { loadLiveSnapshot, replayDataSource } from "./liveSnapshot";
import type { TenantSession } from "./session";

const session: TenantSession = {
  tenantId: "10000000-0000-4000-8000-000000000001",
  subject: "operator-1",
  roles: ["operations"],
  accessToken: "access-token",
  expiresAt: "2099-08-25T10:00:00Z",
};

function response(body: unknown, ok = true): Response {
  return new Response(JSON.stringify(body), {
    status: ok ? 200 : 503,
    headers: { "Content-Type": "application/json" },
  });
}

describe("live product data boundary", () => {
  it("composes the Java order-centric read model without a synthetic dispatch request", async () => {
    const requests: RequestInit[] = [];
    const snapshot = await loadLiveSnapshot(session, async (input, init) => {
      requests.push(init ?? {});
      const url = String(input);
      if (url.includes("operations")) {
        return response({
          source: "live",
          generatedAt: "2026-08-22T10:00:00Z",
          orders: [
            {
              id: "order-1",
              status: "ASSIGNED",
              version: 2,
              createdAt: "2026-08-22T09:55:00Z",
              updatedAt: "2026-08-22T10:00:00Z",
              operational: {
                decision: {
                  status: "RECORDED",
                  decisionId: "decision-1",
                  requestId: "request-1",
                  courierId: "courier-1",
                  strategy: "nearest",
                  strategyVersion: "1.0.0",
                  referenceDataId: "dispatch-api:v1",
                  decidedAt: "2026-08-22T09:59:50Z",
                  fallbackState: "NONE",
                  decisionReason: "lowest distance",
                  policySelectionMode: "WALL",
                  provenanceReference: "prov-1",
                },
                route: {
                  status: "NO_ROUTE_ESTIMATE",
                  provider: null,
                  fallbackUsed: null,
                  fallbackReason: null,
                  travelSeconds: null,
                  distanceKilometres: null,
                  observedAt: null,
                  freshness: { status: "UNAVAILABLE", observedAt: null, evaluatedAt: null },
                },
                courier: {
                  status: "CURRENT",
                  courierId: "courier-1",
                  lifecycleStatus: "ONLINE",
                  sequence: 7,
                  observedAt: "2026-08-22T10:00:00Z",
                  ingestedAt: "2026-08-22T10:00:01Z",
                  freshness: {
                    status: "CURRENT",
                    observedAt: "2026-08-22T10:00:01Z",
                    evaluatedAt: "2026-08-22T10:00:01Z",
                  },
                },
                parties: {
                  linkageStatus: "UNAVAILABLE",
                  customerStatus: null,
                  merchantStatus: null,
                },
                orderFreshness: {
                  status: "CURRENT",
                  observedAt: "2026-08-22T10:00:00Z",
                  evaluatedAt: "2026-08-22T10:00:01Z",
                },
              },
            },
          ],
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
      throw new Error(`unexpected request to ${url}`);
    });

    expect(snapshot.source).toBe("live");
    expect(snapshot.identityScope).toBe(
      "10000000-0000-4000-8000-000000000001:operator-1:operations",
    );
    expect(snapshot.availability).toBe("ready");
    expect(snapshot.merchants[0]?.name).toBe("Local Merchant");
    expect(snapshot.dispatch.selectedCourier).toBe("courier-1");
    expect(snapshot.dispatch.strategy).toBe("nearest");
    expect(snapshot.dispatch.latencyMs).toBeNull();
    expect(snapshot.orders[0]?.operational?.route.status).toBe("NO_ROUTE_ESTIMATE");
    expect(snapshot.orders[0]?.customerName).toBe("Unavailable");
    expect(requests).toHaveLength(1);
    expect(snapshot.couriers[0]).toMatchObject({ sequence: 7, online: true, stale: false });
    expect(new Headers(requests[0].headers).get("Authorization")).toBe("Bearer access-token");
    expect(new Headers(requests[0].headers).get("X-Actor")).toBe("operator");
    expect(snapshot.orders[0]?.operational?.decision.requestId).toBe("request-1");
  });

  it("keeps service failure explicit instead of falling back to demo", async () => {
    const snapshot = await loadLiveSnapshot(session, async () =>
      response({ error: "unavailable" }, false),
    );

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
