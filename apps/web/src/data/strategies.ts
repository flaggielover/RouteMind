export type StrategyMaturity =
  "BASELINE" | "ENGINEERING" | "PRODUCTION-CANDIDATE" | "RESEARCH" | "EXTERNAL-VALIDATED";

export interface StrategyParameterDescriptor {
  key: string;
  type: "float" | "integer";
  default: string;
  minimum: number | null;
  maximum: number | null;
}

export interface StrategyDescriptor {
  name: string;
  version: string;
  capabilities: readonly string[];
  parameters: readonly StrategyParameterDescriptor[];
  status: "available";
  maturity: StrategyMaturity;
}

export const fallbackStrategyRegistry: readonly StrategyDescriptor[] = [
  ["nearest", "BASELINE", ["dispatch"], []],
  ["weighted-greedy", "BASELINE", ["dispatch"], ["distance_weight"]],
  ["hungarian", "BASELINE", ["dispatch", "batch-assignment"], []],
  [
    "risk-aware",
    "BASELINE",
    ["dispatch", "risk-scoring"],
    ["distance", "readiness", "overtime", "service_risk", "balance"],
  ],
  ["minimum-cost-flow", "ENGINEERING", ["dispatch", "batch-assignment"], []],
  ["partitioned-assignment", "ENGINEERING", ["dispatch", "partitioned-assignment"], []],
  [
    "local-search",
    "ENGINEERING",
    ["dispatch", "batch-assignment", "local-search"],
    ["max_iterations"],
  ],
  ["vrptw", "BASELINE", ["dispatch", "vrp", "vrptw"], []],
].map(([name, maturity, capabilities, parameterKeys]) => ({
  name: name as string,
  version: "1.0.0",
  capabilities: capabilities as string[],
  parameters: (parameterKeys as string[]).map((key) => ({
    key,
    type: key === "max_iterations" ? ("integer" as const) : ("float" as const),
    default: key === "max_iterations" ? "32" : "1.0",
    minimum: key === "max_iterations" ? 1 : 0,
    maximum: key === "max_iterations" ? 256 : null,
  })),
  status: "available" as const,
  maturity: maturity as StrategyMaturity,
}));

const computeApi = import.meta.env.VITE_COMPUTE_API_URL ?? "http://localhost:18081";

export async function loadStrategyRegistry(
  fetchImpl: typeof fetch = fetch,
): Promise<readonly StrategyDescriptor[]> {
  try {
    const response = await fetchImpl(`${computeApi}/api/v1/strategies`, {
      headers: { Accept: "application/json" },
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const descriptors = (await response.json()) as StrategyDescriptor[];
    return descriptors.length ? descriptors : fallbackStrategyRegistry;
  } catch {
    return fallbackStrategyRegistry;
  }
}
