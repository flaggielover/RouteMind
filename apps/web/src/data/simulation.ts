import { demoDataSource } from "./demoSnapshot";
import type {
  OperationsDataSource,
  OperationsSnapshot,
  SimulationCommand,
  SimulationEvent,
  SimulationSnapshot,
} from "../domain/model";

interface TwinStateWire {
  scenario_id: string;
  seed: number;
  strategy: string;
  strategy_version: string;
  status: SimulationSnapshot["status"];
  speed: number;
  simulated_time_seconds: number;
  tick: number;
  generation: number;
  event_count: number;
  last_command_id: string | null;
  replay_digest: string;
}

interface TwinEventWire {
  event_id: string;
  event_type: string;
  simulated_time_seconds: number;
  command_id: string;
  details: [string, string][];
}

interface TwinControlWire {
  state: TwinStateWire;
  events: TwinEventWire[];
}

const computeApi = import.meta.env.VITE_COMPUTE_API_URL ?? "http://localhost:18081";
const timeoutMs = 2_000;

function emptySimulation(): SimulationSnapshot {
  return {
    scenarioId: "control-default",
    seed: 7,
    strategy: "nearest",
    strategyVersion: "1.0.0",
    status: "paused",
    speed: 1,
    simulatedTimeSeconds: 0,
    tick: 0,
    generation: 0,
    eventCount: 0,
    lastCommandId: null,
    replayDigest: "",
    events: [],
  };
}

function asSimulationState(
  state: TwinStateWire,
  events: readonly SimulationEvent[],
): SimulationSnapshot {
  return {
    scenarioId: state.scenario_id,
    seed: state.seed,
    strategy: state.strategy,
    strategyVersion: state.strategy_version,
    status: state.status,
    speed: state.speed,
    simulatedTimeSeconds: state.simulated_time_seconds,
    tick: state.tick,
    generation: state.generation,
    eventCount: state.event_count,
    lastCommandId: state.last_command_id,
    replayDigest: state.replay_digest,
    events,
  };
}

function asEvent(event: TwinEventWire): SimulationEvent {
  return {
    eventId: event.event_id,
    eventType: event.event_type,
    simulatedTimeSeconds: event.simulated_time_seconds,
    commandId: event.command_id,
    details: event.details,
  };
}

function operationSnapshot(simulation: SimulationSnapshot, detail: string): OperationsSnapshot {
  const base = demoDataSource.getSnapshot();
  return {
    ...base,
    source: "simulation",
    availability: "ready",
    sourceDetail: detail,
    generatedAt: new Date().toISOString(),
    simulation,
  };
}

async function fetchJson<T>(
  url: string,
  init: RequestInit = {},
  fetchImpl: typeof fetch = fetch,
): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetchImpl(url, { ...init, signal: controller.signal });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return (await response.json()) as T;
  } finally {
    clearTimeout(timeout);
  }
}

export function createSimulationDataSource(fetchImpl: typeof fetch = fetch): OperationsDataSource {
  let current = operationSnapshot(emptySimulation(), "Digital Twin simulation ready");

  return {
    getSnapshot: () => current,
    loadSnapshot: async () => {
      try {
        const wire = await fetchJson<TwinStateWire>(
          `${computeApi}/api/v1/twin/state`,
          { headers: { Accept: "application/json" } },
          fetchImpl,
        );
        current = operationSnapshot(
          asSimulationState(wire, current.simulation?.events ?? []),
          "Python Digital Twin simulation",
        );
      } catch (error) {
        const detail = error instanceof Error ? error.message : "Simulation unavailable";
        current = {
          ...current,
          availability: "unavailable",
          sourceDetail: `Simulation unavailable: ${detail}`,
        };
      }
      return current;
    },
    controlSimulation: async (command: SimulationCommand) => {
      const wire = await fetchJson<TwinControlWire>(
        `${computeApi}/api/v1/twin/control`,
        {
          method: "POST",
          headers: { Accept: "application/json", "Content-Type": "application/json" },
          body: JSON.stringify({
            command_id: command.commandId,
            action: command.action,
            seconds: command.seconds,
            speed: command.speed,
            scenario_id: command.scenarioId,
            seed: command.seed,
            strategy: command.strategy,
          }),
        },
        fetchImpl,
      );
      const nextEvents =
        wire.state.generation !== current.simulation?.generation
          ? wire.events.map(asEvent)
          : [...(current.simulation?.events ?? []), ...wire.events.map(asEvent)].filter(
              (event, index, all) =>
                all.findIndex((candidate) => candidate.eventId === event.eventId) === index,
            );
      current = operationSnapshot(
        asSimulationState(wire.state, nextEvents.slice(-64)),
        "Python Digital Twin simulation",
      );
      return current;
    },
  };
}

export const simulationDataSource = createSimulationDataSource();
