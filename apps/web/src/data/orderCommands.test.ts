import { describe, expect, it } from "vitest";
import {
  createCustomerOrder,
  createIdempotencyKey,
  recordCourierLocation,
  transitionCourierOrder,
  transitionCourierShift,
  transitionMerchantOrder,
} from "./orderCommands";
import type { TenantSession } from "./session";

const customerSession: TenantSession = {
  tenantId: "10000000-0000-4000-8000-000000000001",
  subject: "customer-1",
  roles: ["customer"],
  accessToken: "customer-token",
  expiresAt: "2099-08-25T10:00:00Z",
};
const merchantSession: TenantSession = {
  ...customerSession,
  subject: "merchant-1",
  roles: ["merchant"],
  accessToken: "merchant-token",
};
const courierSession: TenantSession = {
  ...customerSession,
  subject: "courier-1",
  roles: ["courier"],
  accessToken: "courier-token",
};

function response(body: unknown, status: number, traceId = "trace-command-1"): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json", "X-Trace-Id": traceId },
  });
}

describe("customer order command boundary", () => {
  it("sends the Java customer command with an idempotency key and exposes trace metadata", async () => {
    let request: RequestInit | undefined;
    const result = await createCustomerOrder({
      session: customerSession,
      idempotencyKey: "customer-create-fixed",
      correlationId: "correlation-fixed",
      fetchImpl: async (_url, init) => {
        request = init;
        return response(
          { orderId: "order-new", status: "CREATED", version: 0, replayed: false },
          201,
        );
      },
    });

    expect(result).toEqual({
      kind: "success",
      orderId: "order-new",
      status: "CREATED",
      version: 0,
      replayed: false,
      traceId: "trace-command-1",
      idempotencyKey: "customer-create-fixed",
    });
    expect(request?.method).toBe("POST");
    expect(new Headers(request?.headers).get("X-Actor")).toBe("customer");
    expect(new Headers(request?.headers).get("Authorization")).toBe("Bearer customer-token");
    expect(new Headers(request?.headers).get("Idempotency-Key")).toBe("customer-create-fixed");
    expect(new Headers(request?.headers).get("X-Correlation-Id")).toBe("correlation-fixed");
  });

  it("keeps validation and conflict responses explicit and retryable only when safe", async () => {
    const result = await createCustomerOrder({
      session: customerSession,
      idempotencyKey: "customer-create-conflict",
      fetchImpl: async () =>
        response(
          { code: "idempotency_key_reused", traceId: "trace-conflict" },
          409,
          "trace-conflict",
        ),
    });

    expect(result).toEqual({
      kind: "error",
      failureState: "conflict",
      code: "idempotency_key_reused",
      status: 409,
      traceId: "trace-conflict",
      retryable: false,
      idempotencyKey: "customer-create-conflict",
    });
  });

  it("creates a stable scoped key for a command attempt", () => {
    expect(createIdempotencyKey(() => "uuid-1")).toBe("customer-create-uuid-1");
  });

  it("sends merchant lifecycle transitions with the expected version", async () => {
    let request: RequestInit | undefined;
    const result = await transitionMerchantOrder({
      session: merchantSession,
      orderId: "order-1",
      target: "READY_FOR_PICKUP",
      expectedVersion: 2,
      fetchImpl: async (_url, init) => {
        request = init;
        return response(
          { orderId: "order-1", status: "READY_FOR_PICKUP", version: 3, replayed: false },
          200,
        );
      },
    });

    expect(result.kind).toBe("success");
    expect(request?.method).toBe("POST");
    expect(new Headers(request?.headers).get("X-Actor")).toBe("merchant");
    expect(request?.body).toBe(JSON.stringify({ target: "READY_FOR_PICKUP", expectedVersion: 2 }));
  });

  it("sends courier lifecycle and shift commands with stable actor boundaries", async () => {
    const requests: RequestInit[] = [];
    const fetchImpl = async (url: string | URL | Request, init?: RequestInit) => {
      requests.push(init ?? {});
      return String(url).includes("/orders/")
        ? response({ orderId: "order-1", status: "ACCEPTED", version: 3, replayed: false }, 200)
        : response({ courierId: "courier-1", status: "ONLINE", version: 1, replayed: false }, 200);
    };
    const order = await transitionCourierOrder({
      session: courierSession,
      orderId: "order-1",
      target: "ACCEPTED",
      expectedVersion: 2,
      fetchImpl,
      idempotencyKey: "courier-accept-fixed",
    });
    const shift = await transitionCourierShift({
      session: courierSession,
      courierId: "courier-1",
      target: "ONLINE",
      expectedVersion: 0,
      fetchImpl,
      idempotencyKey: "courier-online-fixed",
    });
    const location = await recordCourierLocation({
      session: courierSession,
      courierId: "courier-1",
      latitude: 31.2,
      longitude: 121.5,
      observedAt: "2026-08-22T12:00:00Z",
      sequence: 4,
      online: false,
      fetchImpl,
      idempotencyKey: "courier-location-fixed",
    });

    expect(order.kind).toBe("success");
    expect(shift.kind).toBe("success");
    expect(location.kind).toBe("success");
    expect(new Headers(requests[0].headers).get("X-Actor")).toBe("courier");
    expect(requests[0].body).toBe(JSON.stringify({ target: "ACCEPTED", expectedVersion: 2 }));
    expect(requests[1].body).toBe(JSON.stringify({ target: "ONLINE", expectedVersion: 0 }));
    expect(requests[2].body).toBe(
      JSON.stringify({
        latitude: 31.2,
        longitude: 121.5,
        observedAt: "2026-08-22T12:00:00Z",
        sequence: 4,
        online: false,
      }),
    );
  });

  it("classifies timeout and unavailable failures without losing the retry key", async () => {
    const timeout = await createCustomerOrder({
      session: customerSession,
      idempotencyKey: "customer-timeout-fixed",
      fetchImpl: async () => {
        const error = new DOMException("timed out", "AbortError");
        throw error;
      },
    });
    const unavailable = await transitionMerchantOrder({
      session: merchantSession,
      orderId: "order-1",
      target: "PREPARING",
      expectedVersion: 1,
      idempotencyKey: "merchant-unavailable-fixed",
      fetchImpl: async () => {
        return response({ code: "service_unavailable" }, 503, "trace-unavailable");
      },
    });

    expect(timeout).toMatchObject({
      kind: "error",
      failureState: "timeout",
      retryable: true,
      idempotencyKey: "customer-timeout-fixed",
    });
    expect(unavailable).toMatchObject({
      kind: "error",
      failureState: "unavailable",
      retryable: true,
      idempotencyKey: "merchant-unavailable-fixed",
      traceId: "trace-unavailable",
    });
  });
});
