import { Check, Circle } from "lucide-react";
import type { Order } from "../domain/model";
import { orderStatusLabel } from "../domain/selectors";

interface LifecycleTimelineProps {
  order: Order;
}

export function LifecycleTimeline({ order }: LifecycleTimelineProps) {
  return (
    <ol className="timeline" aria-label={`Lifecycle for ${order.shortId}`}>
      {order.events.map((event) => (
        <li
          className={event.completed ? "timeline-item completed" : "timeline-item"}
          key={event.status}
        >
          <span className="timeline-marker" aria-hidden="true">
            {event.completed ? <Check size={12} strokeWidth={3} /> : <Circle size={8} />}
          </span>
          <span className="timeline-copy">
            <strong>{orderStatusLabel[event.status]}</strong>
            <span>{event.label}</span>
          </span>
          <time dateTime={`2026-08-22T${event.at}:00`}>{event.at}</time>
        </li>
      ))}
    </ol>
  );
}
