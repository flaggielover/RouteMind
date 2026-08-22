import { describe, expect, it } from "vitest";
import {
  createCustomerOrder,
  createIdempotencyKey,
  transitionMerchantOrder,
} from "./orderCommands";

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
    expect(new Headers(request?.headers).get("Idempotency-Key")).toBe("customer-create-fixed");
    expect(new Headers(request?.headers).get("X-Correlation-Id")).toBe("correlation-fixed");
  });

  it("keeps validation and conflict responses explicit and retryable only when safe", async () => {
    const result = await createCustomerOrder({
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
});
