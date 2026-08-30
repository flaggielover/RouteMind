import { Gauge, Pause, Play, RotateCcw, SkipForward, SlidersHorizontal } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import type { SimulationAction, SimulationCommand, SimulationSnapshot } from "../domain/model";
import { scenarioCatalog } from "../data/scenarioCatalog";
import { fallbackStrategyRegistry } from "../data/strategies";

interface SimulationControlPanelProps {
  snapshot: SimulationSnapshot;
  demandCount: number;
  supplyCount: number;
  trafficLabel: string;
  onControl: (command: SimulationCommand) => Promise<void>;
}

let commandSequence = 0;

function commandId(action: SimulationAction): string {
  commandSequence += 1;
  return `web-${action}-${commandSequence}`;
}

export function SimulationControlPanel({
  snapshot,
  demandCount,
  supplyCount,
  trafficLabel,
  onControl,
}: SimulationControlPanelProps) {
  const [speed, setSpeed] = useState(snapshot.speed);
  const [seconds, setSeconds] = useState(60);
  const [scenarioId, setScenarioId] = useState(snapshot.scenarioId);
  const [seed, setSeed] = useState(snapshot.seed);
  const [strategy, setStrategy] = useState(snapshot.strategy);
  const [pending, setPending] = useState<SimulationAction | null>(null);
  const [error, setError] = useState<string | null>(null);
  const mounted = useRef(true);

  useEffect(() => {
    setSpeed(snapshot.speed);
    setScenarioId(snapshot.scenarioId);
    setSeed(snapshot.seed);
    setStrategy(snapshot.strategy);
  }, [snapshot.speed, snapshot.scenarioId, snapshot.seed, snapshot.strategy]);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  const issue = async (
    action: SimulationAction,
    values: Omit<SimulationCommand, "commandId" | "action"> = {},
  ) => {
    setPending(action);
    setError(null);
    try {
      await onControl({ commandId: commandId(action), action, ...values });
    } catch (cause) {
      if (mounted.current)
        setError(cause instanceof Error ? cause.message : "Simulation control unavailable");
    } finally {
      if (mounted.current) setPending(null);
    }
  };

  const running = snapshot.status === "running";
  const disabled = pending !== null || snapshot.status === "completed";
  return (
    <section className="simulation-panel panel" aria-label="Digital Twin simulation controls">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Simulation / Digital Twin</p>
          <h2>Control the scenario clock.</h2>
          <p className="panel-subtitle">
            {snapshot.status} · {snapshot.simulatedTimeSeconds.toFixed(0)} simulated seconds · tick{" "}
            {snapshot.tick}
          </p>
        </div>
        <Gauge className="heading-icon" size={18} aria-hidden="true" />
      </div>
      <div className="simulation-metrics" aria-label="Simulation inputs and metrics">
        <div>
          <span>Demand</span>
          <strong>{demandCount} orders</strong>
        </div>
        <div>
          <span>Supply</span>
          <strong>{supplyCount} couriers</strong>
        </div>
        <div>
          <span>Traffic</span>
          <strong>{trafficLabel}</strong>
        </div>
        <div>
          <span>Replay</span>
          <strong>{snapshot.replayDigest ? snapshot.replayDigest.slice(0, 10) : "pending"}</strong>
        </div>
      </div>
      <div className="simulation-toolbar" aria-label="Simulation playback controls">
        <button
          className="button button-primary"
          type="button"
          disabled={pending !== null}
          onClick={() =>
            void issue(running ? "pause" : snapshot.status === "paused" ? "resume" : "reset")
          }
        >
          {running ? <Pause size={15} /> : <Play size={15} />}
          {running ? "Pause" : snapshot.status === "completed" ? "Restart" : "Resume"}
        </button>
        <label className="simulation-step-field">
          <span>Step seconds</span>
          <input
            aria-label="Step seconds"
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
          title="Reset simulation"
          aria-label="Reset simulation"
          disabled={pending !== null}
          onClick={() => void issue("reset")}
        >
          <RotateCcw size={16} />
        </button>
      </div>
      <div className="simulation-settings">
        <label>
          Scenario
          <select
            aria-label="Scenario"
            value={scenarioId}
            onChange={(event) => setScenarioId(event.target.value)}
          >
            {!scenarioCatalog.some((scenario) => scenario.id === scenarioId) && (
              <option value={scenarioId}>{scenarioId} · current</option>
            )}
            {scenarioCatalog.map((scenario) => (
              <option key={scenario.id} value={scenario.id}>
                {scenario.label} · {scenario.authority}
              </option>
            ))}
          </select>
          <button
            className="button button-quiet"
            type="button"
            disabled={pending !== null}
            onClick={() => void issue("scenario", { scenarioId })}
          >
            Apply
          </button>
        </label>
        <label>
          Seed
          <input
            type="number"
            min="0"
            max="2147483647"
            value={seed}
            onChange={(event) => setSeed(Number(event.target.value))}
          />
          <button
            className="button button-quiet"
            type="button"
            disabled={pending !== null}
            onClick={() => void issue("seed", { seed })}
          >
            Apply
          </button>
        </label>
        <label>
          Strategy
          <select value={strategy} onChange={(event) => setStrategy(event.target.value)}>
            {fallbackStrategyRegistry.map((descriptor) => (
              <option key={descriptor.name} value={descriptor.name}>
                {descriptor.name}
              </option>
            ))}
          </select>
          <button
            className="button button-quiet"
            type="button"
            disabled={pending !== null}
            onClick={() => void issue("strategy", { strategy })}
          >
            Apply
          </button>
        </label>
        <label className="speed-setting">
          <span>Speed {speed.toFixed(1)}x</span>
          <input
            aria-label="Simulation speed"
            type="range"
            min="0.1"
            max="10"
            step="0.1"
            value={speed}
            onChange={(event) => setSpeed(Number(event.target.value))}
          />
          <button
            className="button button-quiet"
            type="button"
            disabled={pending !== null}
            onClick={() => void issue("speed", { speed })}
          >
            <SlidersHorizontal size={14} /> Apply
          </button>
        </label>
      </div>
      {error && (
        <div className="projection-state projection-degraded" role="alert">
          {error}
        </div>
      )}
      <div className="simulation-events" aria-label="Simulation events">
        <div className="panel-heading compact-heading">
          <div>
            <p className="eyebrow">Event stream</p>
            <h3>{snapshot.eventCount} recorded transitions</h3>
          </div>
        </div>
        {snapshot.events.length ? (
          <ol>
            {snapshot.events
              .slice(-6)
              .reverse()
              .map((event) => (
                <li key={event.eventId}>
                  <span>{event.eventType}</span>
                  <small>
                    t+{event.simulatedTimeSeconds.toFixed(0)}s · {event.commandId}
                  </small>
                </li>
              ))}
          </ol>
        ) : (
          <p className="empty-state">No simulation events yet. Start or step the clock.</p>
        )}
      </div>
    </section>
  );
}
