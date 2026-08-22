import type { DataSourceMode, OperationsSnapshot } from "../domain/model";
import type { RealtimeConnectionState, RealtimeItem } from "../data/realtime";

interface ActivityStreamProps {
  snapshot: OperationsSnapshot;
  realtime: RealtimeConnectionState;
}

interface ActivityRecord {
  key: string;
  label: string;
  detail: string;
  occurredAt: string;
  source: DataSourceMode;
}

export function ActivityStream({ snapshot, realtime }: ActivityStreamProps) {
  const records = realtime.recentEvents.length
    ? realtime.recentEvents.slice(0, 4).map(toLiveRecord)
    : snapshot.source === "demo"
      ? demoRecords(snapshot)
      : [];
  const emptyMessage =
    snapshot.source === "replay"
      ? "No verified replay activity is available."
      : snapshot.source === "live"
        ? realtime.status === "stale"
          ? (realtime.staleReason ?? "Live activity is stale; refresh the authoritative snapshot.")
          : realtime.status === "degraded"
            ? realtime.detail
            : "Waiting for verified live events."
        : "No activity is present in the selected source.";

  return (
    <section className="activity-stream" aria-labelledby="activity-stream-title">
      <div className="activity-stream-heading">
        <div>
          <p className="eyebrow">Verified events</p>
          <h3 id="activity-stream-title">Activity stream</h3>
        </div>
        <span className={`activity-freshness freshness-${snapshot.source}-${realtime.status}`}>
          {snapshot.source === "live"
            ? realtime.cursor === "0"
              ? "Awaiting cursor"
              : `Cursor ${realtime.cursor}`
            : snapshot.source === "demo"
              ? "Demo source"
              : "Replay source"}
        </span>
      </div>
      {records.length ? (
        <ol className="activity-list" aria-label="Verified activity events">
          {records.map((record) => (
            <li className="activity-item" key={record.key}>
              <span className="activity-marker" aria-hidden="true" />
              <div className="activity-copy">
                <strong>{record.label}</strong>
                <small>{record.detail}</small>
              </div>
              <span className={`activity-source source-${record.source}`}>
                {sourceLabel(record.source)}
              </span>
              <time dateTime={record.occurredAt}>{formatTime(record.occurredAt)}</time>
            </li>
          ))}
        </ol>
      ) : (
        <p className="empty-state activity-empty">{emptyMessage}</p>
      )}
    </section>
  );
}

function toLiveRecord(item: RealtimeItem): ActivityRecord {
  return {
    key: item.event.eventId,
    label: item.event.eventType.replaceAll(".", " "),
    detail: `cursor ${item.cursor} · trace ${item.event.traceId.slice(0, 12)}`,
    occurredAt: item.event.occurredAt,
    source: "live",
  };
}

function demoRecords(snapshot: OperationsSnapshot): ActivityRecord[] {
  return snapshot.orders
    .flatMap((order) =>
      order.events.slice(-2).map((event) => ({
        key: `${order.id}-${event.status}-${event.at}`,
        label: `${order.shortId} ${event.label}`,
        detail: "Deterministic lifecycle fixture",
        occurredAt: event.at,
        source: "demo" as const,
      })),
    )
    .slice(-4)
    .reverse();
}

function sourceLabel(source: DataSourceMode): string {
  return source === "live" ? "Live" : source === "demo" ? "Demo" : "Replay";
}

function formatTime(value: string): string {
  if (!value) return "--:--";
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}
