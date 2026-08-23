export interface CustomerOrderCommandSuccess {
  kind: "success";
  orderId: string;
  status: string;
  version: number;
  replayed: boolean;
  traceId: string | null;
  idempotencyKey: string;
}

export interface CustomerOrderCommandFailure {
  kind: "error";
  failureState: "conflict" | "validation" | "timeout" | "unavailable";
  code: string;
  status: number;
  traceId: string | null;
  retryable: boolean;
  idempotencyKey: string;
}

export type CustomerOrderCommandResult = CustomerOrderCommandSuccess | CustomerOrderCommandFailure;

export type CourierCommandSuccess = CustomerOrderCommandSuccess & { courierId: string };
export type CourierCommandFailure = CustomerOrderCommandFailure;
export type CourierCommandResult = CourierCommandSuccess | CourierCommandFailure;

function failureState(status: number, code: string): CustomerOrderCommandFailure["failureState"] {
  if (status === 408 || code === "command_timeout") return "timeout";
  if (
    status === 409 ||
    code.includes("conflict") ||
    code.includes("stale") ||
    code.includes("reused")
  )
    return "conflict";
  if (status >= 500 || status === 0 || code === "service_unavailable") return "unavailable";
  return "validation";
}

function commandFailure(
  status: number,
  code: string,
  traceId: string | null,
  idempotencyKey: string,
): CustomerOrderCommandFailure {
  return {
    kind: "error",
    failureState: failureState(status, code),
    code,
    status,
    traceId,
    retryable: status >= 500 || status === 408 || status === 0,
    idempotencyKey,
  };
}

interface OrderCommandResponse {
  orderId?: string;
  status?: string;
  version?: number;
  replayed?: boolean;
  code?: string;
  traceId?: string;
}

interface CourierCommandResponse {
  courierId?: string;
  status?: string;
  version?: number;
  replayed?: boolean;
  code?: string;
  traceId?: string;
}

const businessApi = import.meta.env.VITE_BUSINESS_API_URL ?? "http://localhost:18080";
const timeoutMs = 2_000;
let localIdempotencySequence = 0;

export function createIdempotencyKey(
  randomUuid: () => string = () =>
    typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
      ? crypto.randomUUID()
      : `browser-${++localIdempotencySequence}`,
): string {
  return `customer-create-${randomUuid()}`;
}

function traceId(response: Response, body: OrderCommandResponse): string | null {
  return response.headers.get("X-Trace-Id") ?? body.traceId ?? null;
}

function isSuccess(
  body: OrderCommandResponse,
): body is Required<Pick<OrderCommandResponse, "orderId" | "status" | "version" | "replayed">> {
  return (
    typeof body.orderId === "string" &&
    typeof body.status === "string" &&
    typeof body.version === "number" &&
    typeof body.replayed === "boolean"
  );
}

function isCourierSuccess(
  body: CourierCommandResponse,
): body is Required<Pick<CourierCommandResponse, "courierId" | "status" | "version" | "replayed">> {
  return (
    typeof body.courierId === "string" &&
    typeof body.status === "string" &&
    typeof body.version === "number" &&
    typeof body.replayed === "boolean"
  );
}

async function runCourierCommand(
  path: string,
  options: { idempotencyKey: string; body: unknown; fetchImpl?: typeof fetch },
): Promise<CourierCommandResult> {
  const fetchImpl = options.fetchImpl ?? fetch;
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetchImpl(`${businessApi}${path}`, {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
        "Idempotency-Key": options.idempotencyKey,
        "X-Actor": "courier",
      },
      body: JSON.stringify(options.body),
      signal: controller.signal,
    });
    const body = (await response.json().catch(() => ({}))) as CourierCommandResponse;
    const responseTraceId = traceId(response, body);
    if (response.ok && isCourierSuccess(body)) {
      return {
        kind: "success",
        orderId: body.courierId,
        courierId: body.courierId,
        status: body.status,
        version: body.version,
        replayed: body.replayed,
        traceId: responseTraceId,
        idempotencyKey: options.idempotencyKey,
      };
    }
    const code = typeof body.code === "string" ? body.code : `HTTP ${response.status}`;
    return commandFailure(response.status, code, responseTraceId, options.idempotencyKey);
  } catch (error) {
    const code =
      error instanceof DOMException && error.name === "AbortError"
        ? "command_timeout"
        : "service_unavailable";
    return commandFailure(0, code, null, options.idempotencyKey);
  } finally {
    clearTimeout(timeout);
  }
}

export async function createCustomerOrder(
  options: {
    fetchImpl?: typeof fetch;
    idempotencyKey?: string;
    correlationId?: string;
  } = {},
): Promise<CustomerOrderCommandResult> {
  const fetchImpl = options.fetchImpl ?? fetch;
  const idempotencyKey = options.idempotencyKey ?? createIdempotencyKey();
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetchImpl(`${businessApi}/api/v1/orders`, {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
        "Idempotency-Key": idempotencyKey,
        "X-Actor": "customer",
        ...(options.correlationId ? { "X-Correlation-Id": options.correlationId } : {}),
      },
      body: JSON.stringify({}),
      signal: controller.signal,
    });
    const body = (await response.json().catch(() => ({}))) as OrderCommandResponse;
    const responseTraceId = traceId(response, body);
    if (response.ok && isSuccess(body)) {
      return {
        kind: "success",
        orderId: body.orderId,
        status: body.status,
        version: body.version,
        replayed: body.replayed,
        traceId: responseTraceId,
        idempotencyKey,
      };
    }
    const code = typeof body.code === "string" ? body.code : `HTTP ${response.status}`;
    return commandFailure(response.status, code, responseTraceId, idempotencyKey);
  } catch (error) {
    const code =
      error instanceof DOMException && error.name === "AbortError"
        ? "command_timeout"
        : "service_unavailable";
    return commandFailure(0, code, null, idempotencyKey);
  } finally {
    clearTimeout(timeout);
  }
}

export async function transitionMerchantOrder(options: {
  orderId: string;
  target: "CONFIRMED" | "PREPARING" | "READY_FOR_PICKUP";
  expectedVersion: number;
  fetchImpl?: typeof fetch;
  idempotencyKey?: string;
}): Promise<CustomerOrderCommandResult> {
  const fetchImpl = options.fetchImpl ?? fetch;
  const idempotencyKey =
    options.idempotencyKey ??
    `merchant-${options.target.toLowerCase()}-${options.orderId}-${options.expectedVersion}`;
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetchImpl(
      `${businessApi}/api/v1/orders/${options.orderId}/transitions`,
      {
        method: "POST",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
          "Idempotency-Key": idempotencyKey,
          "X-Actor": "merchant",
        },
        body: JSON.stringify({ target: options.target, expectedVersion: options.expectedVersion }),
        signal: controller.signal,
      },
    );
    const body = (await response.json().catch(() => ({}))) as OrderCommandResponse;
    const responseTraceId = traceId(response, body);
    if (response.ok && isSuccess(body)) {
      return {
        kind: "success",
        orderId: body.orderId,
        status: body.status,
        version: body.version,
        replayed: body.replayed,
        traceId: responseTraceId,
        idempotencyKey,
      };
    }
    const code = typeof body.code === "string" ? body.code : `HTTP ${response.status}`;
    return commandFailure(response.status, code, responseTraceId, idempotencyKey);
  } catch (error) {
    const code =
      error instanceof DOMException && error.name === "AbortError"
        ? "command_timeout"
        : "service_unavailable";
    return commandFailure(0, code, null, idempotencyKey);
  } finally {
    clearTimeout(timeout);
  }
}

export async function transitionCourierOrder(options: {
  orderId: string;
  target: "ACCEPTED" | "ARRIVED" | "PICKED_UP" | "DELIVERED";
  expectedVersion: number;
  fetchImpl?: typeof fetch;
  idempotencyKey?: string;
}): Promise<CustomerOrderCommandResult> {
  const idempotencyKey =
    options.idempotencyKey ??
    `courier-${options.target.toLowerCase()}-${options.orderId}-${options.expectedVersion}`;
  return transitionOrderAsCourier(
    options.orderId,
    options.target,
    options.expectedVersion,
    idempotencyKey,
    options.fetchImpl,
  );
}

async function transitionOrderAsCourier(
  orderId: string,
  target: "ACCEPTED" | "ARRIVED" | "PICKED_UP" | "DELIVERED",
  expectedVersion: number,
  idempotencyKey: string,
  fetchImpl?: typeof fetch,
): Promise<CustomerOrderCommandResult> {
  const fetcher = fetchImpl ?? fetch;
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetcher(`${businessApi}/api/v1/orders/${orderId}/transitions`, {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
        "Idempotency-Key": idempotencyKey,
        "X-Actor": "courier",
      },
      body: JSON.stringify({ target, expectedVersion }),
      signal: controller.signal,
    });
    const body = (await response.json().catch(() => ({}))) as OrderCommandResponse;
    const responseTraceId = traceId(response, body);
    if (response.ok && isSuccess(body)) {
      return {
        kind: "success",
        orderId: body.orderId,
        status: body.status,
        version: body.version,
        replayed: body.replayed,
        traceId: responseTraceId,
        idempotencyKey,
      };
    }
    const code = typeof body.code === "string" ? body.code : `HTTP ${response.status}`;
    return commandFailure(response.status, code, responseTraceId, idempotencyKey);
  } catch (error) {
    const code =
      error instanceof DOMException && error.name === "AbortError"
        ? "command_timeout"
        : "service_unavailable";
    return commandFailure(0, code, null, idempotencyKey);
  } finally {
    clearTimeout(timeout);
  }
}

export async function transitionCourierShift(options: {
  courierId: string;
  target: "ONLINE" | "OFFLINE";
  expectedVersion: number;
  fetchImpl?: typeof fetch;
  idempotencyKey?: string;
}): Promise<CourierCommandResult> {
  const idempotencyKey =
    options.idempotencyKey ??
    `courier-shift-${options.target.toLowerCase()}-${options.courierId}-${options.expectedVersion}`;
  return runCourierCommand(`/api/v1/couriers/${options.courierId}/shift`, {
    idempotencyKey,
    body: { target: options.target, expectedVersion: options.expectedVersion },
    fetchImpl: options.fetchImpl,
  });
}

export async function recordCourierLocation(options: {
  courierId: string;
  latitude: number;
  longitude: number;
  observedAt?: string;
  sequence?: number;
  online?: boolean;
  fetchImpl?: typeof fetch;
  idempotencyKey?: string;
}): Promise<CourierCommandResult> {
  const observedAt = options.observedAt ?? new Date().toISOString();
  const sequence = options.sequence ?? 1;
  const online = options.online ?? true;
  const idempotencyKey =
    options.idempotencyKey ?? `courier-location-${options.courierId}-${observedAt}`;
  return runCourierCommand(`/api/v1/couriers/${options.courierId}/location`, {
    idempotencyKey,
    body: {
      latitude: options.latitude,
      longitude: options.longitude,
      observedAt,
      sequence,
      online,
    },
    fetchImpl: options.fetchImpl,
  });
}
