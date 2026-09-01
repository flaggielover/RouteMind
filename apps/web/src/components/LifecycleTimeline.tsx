import { Check, Circle } from "lucide-react";
import type { Order } from "../domain/model";
import { orderStatusLabel } from "../domain/selectors";
import { useLocale } from "../i18n";

interface LifecycleTimelineProps {
  order: Order;
}

export function LifecycleTimeline({ order }: LifecycleTimelineProps) {
  const { locale } = useLocale();
  const statusLabelZh: Partial<Record<keyof typeof orderStatusLabel, string>> = {
    CREATED: "已创建",
    CONFIRMED: "已确认",
    PREPARING: "备餐中",
    READY_FOR_PICKUP: "待取货",
    ASSIGNED: "已分配",
    ACCEPTED: "已接受分配",
    ARRIVED: "已到达商户",
    PICKED_UP: "已取货",
    OUT_FOR_DELIVERY: "配送中",
    DELIVERED: "已送达",
  };
  const eventLabelZh: Partial<Record<keyof typeof orderStatusLabel, string>> = {
    CREATED: "收到订单",
    CONFIRMED: "商户已确认",
    PREPARING: "厨房开始备餐",
    READY_FOR_PICKUP: "可以取货",
    ASSIGNED: "已分配骑手",
    PICKED_UP: "已取货",
    OUT_FOR_DELIVERY: "配送中",
    DELIVERED: "已送达",
  };
  return (
    <ol
      className="timeline"
      aria-label={`${locale === "zh-CN" ? "订单生命周期" : "Lifecycle for"} ${order.shortId}`}
    >
      {order.events.map((event) => (
        <li
          className={event.completed ? "timeline-item completed" : "timeline-item"}
          key={event.status}
        >
          <span className="timeline-marker" aria-hidden="true">
            {event.completed ? <Check size={12} strokeWidth={3} /> : <Circle size={8} />}
          </span>
          <span className="timeline-copy">
            <strong>
              {locale === "zh-CN"
                ? (statusLabelZh[event.status] ?? orderStatusLabel[event.status])
                : orderStatusLabel[event.status]}
            </strong>
            <span>
              {locale === "zh-CN" ? (eventLabelZh[event.status] ?? event.label) : event.label}
            </span>
          </span>
          <time dateTime={`2026-08-22T${event.at}:00`}>{event.at}</time>
        </li>
      ))}
    </ol>
  );
}
