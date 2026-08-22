import { CircleAlert, CircleCheck, Clock3, LoaderCircle } from "lucide-react";
import type { ServiceStatus } from "../domain/model";

interface StatusPillProps {
  status: ServiceStatus | "available" | "on_route" | "offline" | "open" | "busy" | "paused";
  label?: string;
}

const iconByStatus = {
  healthy: CircleCheck,
  unavailable: CircleAlert,
  checking: LoaderCircle,
  available: CircleCheck,
  on_route: Clock3,
  offline: CircleAlert,
  open: CircleCheck,
  busy: Clock3,
  paused: CircleAlert,
} as const;

export function StatusPill({ status, label }: StatusPillProps) {
  const Icon = iconByStatus[status];
  return (
    <span className={`status-pill status-${status}`}>
      <Icon aria-hidden="true" size={13} className={status === "checking" ? "spin" : undefined} />
      <span>{label ?? status.replace("_", " ")}</span>
    </span>
  );
}
