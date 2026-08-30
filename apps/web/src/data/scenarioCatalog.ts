export interface ScenarioCatalogEntry {
  id:
    | "NORMAL_BASELINE"
    | "DINNER_RUSH"
    | "COURIER_SHORTAGE"
    | "MERCHANT_DELAY"
    | "TRAFFIC_DEGRADATION"
    | "ROUTING_PROVIDER_FAILURE"
    | "DISPATCH_PRESSURE"
    | "RECOVERY";
  label: string;
  authority: "SIMULATION";
}

export const scenarioCatalog: readonly ScenarioCatalogEntry[] = [
  { id: "NORMAL_BASELINE", label: "Normal baseline", authority: "SIMULATION" },
  { id: "DINNER_RUSH", label: "Dinner rush", authority: "SIMULATION" },
  { id: "COURIER_SHORTAGE", label: "Courier shortage", authority: "SIMULATION" },
  { id: "MERCHANT_DELAY", label: "Merchant delay", authority: "SIMULATION" },
  { id: "TRAFFIC_DEGRADATION", label: "Traffic degradation", authority: "SIMULATION" },
  { id: "ROUTING_PROVIDER_FAILURE", label: "Routing provider failure", authority: "SIMULATION" },
  { id: "DISPATCH_PRESSURE", label: "Dispatch pressure", authority: "SIMULATION" },
  { id: "RECOVERY", label: "Recovery", authority: "SIMULATION" },
];
