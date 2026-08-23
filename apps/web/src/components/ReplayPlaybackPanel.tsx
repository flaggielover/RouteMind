import { CircleCheck, Pause, Play, RotateCcw, Search, SkipForward } from "lucide-react";
import { useState } from "react";
import type { ReplayAction, ReplayCommand, ReplaySnapshot } from "../domain/model";

interface ReplayPlaybackPanelProps {
  snapshot: ReplaySnapshot;
  onControl: (command: ReplayCommand) => Promise<void>;
}

let replayCommandSequence = 0;

function replayCommandId(action: ReplayAction): string {
  replayCommandSequence += 1;
  return `web-replay-${action}-${replayCommandSequence}`;
}

export function ReplayPlaybackPanel({ snapshot, onControl }: ReplayPlaybackPanelProps) {
  const [seconds, setSeconds] = useState(15);
  const [speed, setSpeed] = useState(snapshot.speed);
  const [selectedEventId, setSelectedEventId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(snapshot.verificationError);
  const playing = snapshot.status === "playing";
  const disabled = !snapshot.verified;

  const issue = async (
    action: ReplayAction,
    values: Omit<ReplayCommand, "action" | "commandId"> = {},
  ) => {
    setError(null);
    try {
      await onControl({ commandId: replayCommandId(action), action, ...values });
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Replay control unavailable");
    }
  };

  const selected = snapshot.visibleEvents.find((event) => event.eventId === selectedEventId);
  return (
    <section className="replay-panel panel" aria-label="Verified replay playback">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Replay / verified artifact</p>
          <h2>Inspect the recorded run.</h2>
          <p className="panel-subtitle">
            {snapshot.verified
              ? "Digest verified"
              : snapshot.status === "verifying"
                ? "Verifying digest"
                : "Playback blocked"}
            {" · "}
            {snapshot.cursorSeconds.toFixed(0)} / {snapshot.durationSeconds.toFixed(0)} simulated
            seconds
          </p>
        </div>
        <CircleCheck
          className={snapshot.verified ? "replay-verified" : "heading-icon"}
          size={18}
          aria-hidden="true"
        />
      </div>
      <div className="replay-provenance">
        <span>{snapshot.artifactId}</span>
        <code>{snapshot.replayDigest.slice(0, 16)}</code>
        <small>{snapshot.provenance}</small>
      </div>
      <div className="replay-toolbar" aria-label="Replay playback controls">
        <button
          className="button button-primary"
          type="button"
          disabled={disabled}
          onClick={() => void issue(playing ? "pause" : "play")}
        >
          {playing ? <Pause size={15} /> : <Play size={15} />}
          {playing ? "Pause" : "Play"}
        </button>
        <label>
          Step seconds
          <input
            aria-label="Replay step seconds"
            type="number"
            min="1"
            max="3600"
            value={seconds}
            onChange={(event) => setSeconds(Number(event.target.value))}
          />
        </label>
        <button
          className="button"
          type="button"
          disabled={disabled}
          onClick={() => void issue("step", { seconds })}
        >
          <SkipForward size={15} /> Step
        </button>
        <button
          className="icon-button"
          type="button"
          title="Reset replay"
          aria-label="Reset replay"
          disabled={disabled}
          onClick={() => void issue("reset")}
        >
          <RotateCcw size={16} />
        </button>
      </div>
      <div className="replay-seek">
        <label htmlFor="replay-seek-slider">Seek</label>
        <input
          id="replay-seek-slider"
          aria-label="Seek replay"
          type="range"
          min="0"
          max={snapshot.durationSeconds}
          step="1"
          value={snapshot.cursorSeconds}
          disabled={disabled}
          onChange={(event) => void issue("seek", { seconds: Number(event.target.value) })}
        />
        <label>
          Speed {speed.toFixed(1)}x
          <input
            aria-label="Replay speed"
            type="range"
            min="0.1"
            max="10"
            step="0.1"
            value={speed}
            disabled={disabled}
            onChange={(event) => setSpeed(Number(event.target.value))}
            onMouseUp={() => void issue("speed", { speed })}
          />
        </label>
      </div>
      {error && (
        <div className="projection-state projection-degraded" role="alert">
          {error}
        </div>
      )}
      <div className="replay-events" aria-label="Replay event inspection">
        <div className="panel-heading compact-heading">
          <div>
            <p className="eyebrow">Event inspection</p>
            <h3>
              {snapshot.visibleEvents.length} visible of {snapshot.events.length} events
            </h3>
          </div>
          <Search size={16} className="heading-icon" />
        </div>
        {snapshot.visibleEvents.length ? (
          <ol>
            {snapshot.visibleEvents.map((event) => (
              <li key={event.eventId}>
                <button
                  type="button"
                  className="replay-event-button"
                  onClick={() => setSelectedEventId(event.eventId)}
                >
                  <span>{event.eventType}</span>
                  <small>t+{event.simulatedTimeSeconds}s</small>
                </button>
              </li>
            ))}
          </ol>
        ) : (
          <p className="empty-state">Advance the verified replay to inspect events.</p>
        )}
        {selected && (
          <div className="replay-event-detail" role="status">
            <strong>{selected.eventId}</strong>
            {selected.details.map(([key, value]) => (
              <span key={key}>
                {key}: {value}
              </span>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
