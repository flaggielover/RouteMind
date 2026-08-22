import type { LucideIcon } from "lucide-react";

interface MetricCellProps {
  label: string;
  value: string;
  detail: string;
  icon: LucideIcon;
  tone?: "neutral" | "accent" | "warning" | "success";
}

export function MetricCell({
  label,
  value,
  detail,
  icon: Icon,
  tone = "neutral",
}: MetricCellProps) {
  return (
    <div className={`metric-cell metric-${tone}`}>
      <div className="metric-icon" aria-hidden="true">
        <Icon size={16} />
      </div>
      <div>
        <p className="eyebrow">{label}</p>
        <p className="metric-value">{value}</p>
        <p className="metric-detail">{detail}</p>
      </div>
    </div>
  );
}
