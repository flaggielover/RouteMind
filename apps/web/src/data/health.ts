import type { ServiceHealth, ServiceStatus } from "../domain/model";

interface HealthTarget {
  service: ServiceHealth["service"];
  label: string;
  endpoint: string;
}

const targets: HealthTarget[] = [
  {
    service: "business-api",
    label: "Business API",
    endpoint: `${import.meta.env.VITE_BUSINESS_API_URL ?? "http://localhost:18080"}/actuator/health`,
  },
  {
    service: "compute-api",
    label: "Compute API",
    endpoint: `${import.meta.env.VITE_COMPUTE_API_URL ?? "http://localhost:18081"}/healthz`,
  },
];

const timeoutMs = 1_500;

function probeStatus(status: number): { status: ServiceStatus; detail: string } {
  return status >= 200 && status < 300
    ? { status: "healthy", detail: "Healthy response" }
    : { status: "unavailable", detail: `HTTP ${status}` };
}

async function probe(target: HealthTarget, fetchImpl: typeof fetch): Promise<ServiceHealth> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetchImpl(target.endpoint, {
      method: "GET",
      headers: { Accept: "application/json" },
      signal: controller.signal,
    });
    const result = probeStatus(response.status);
    return { ...target, ...result, checkedAt: new Date().toISOString() };
  } catch (error) {
    const detail =
      error instanceof DOMException && error.name === "AbortError"
        ? "Probe timeout"
        : "Network unavailable";
    return { ...target, status: "unavailable", checkedAt: new Date().toISOString(), detail };
  } finally {
    clearTimeout(timeout);
  }
}

export async function probeServices(fetchImpl: typeof fetch = fetch): Promise<ServiceHealth[]> {
  return Promise.all(targets.map((target) => probe(target, fetchImpl)));
}
