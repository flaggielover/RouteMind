import { CircleAlert, CircleCheck, Clock3, LoaderCircle } from "lucide-react";
import type { ServiceStatus } from "../domain/model";
import { useLocale } from "../i18n";

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
  const { locale } = useLocale();
  const Icon = iconByStatus[status];
  const zhLabels: Partial<Record<StatusPillProps["status"], string>> = {
    healthy: "正常",
    unavailable: "不可用",
    checking: "检查中",
    available: "可用",
    on_route: "路线中",
    offline: "离线",
    open: "开放",
    busy: "繁忙",
    paused: "已暂停",
  };
  return (
    <span className={`status-pill status-${status}`}>
      <Icon aria-hidden="true" size={13} className={status === "checking" ? "spin" : undefined} />
      <span>{label ?? (locale === "zh-CN" ? zhLabels[status] : status.replace("_", " "))}</span>
    </span>
  );
}
