import type { OperationsSnapshot } from "./model";

export type TwinExecutionMode = "simulation" | "replay" | "benchmark";
export type TwinModeStatus = "active" | "available" | "fixture" | "unavailable";

export interface TwinModeEvidence {
  mode: TwinExecutionMode;
  status: TwinModeStatus;
  detail: string;
}

export interface TwinTimelineItem {
  eventId: string;
  eventType: string;
  seconds: number;
  detail: string;
}

export interface TwinStateBar {
  label: string;
  value: number;
  detail: string;
}

export interface TwinVisualizationProjection {
  sourceLabel: string;
  scenarioId: string;
  seed: number;
  clockDomain: "SIMULATED" | "REPLAY";
  status: string;
  currentSeconds: number;
  durationSeconds: number;
  speed: number;
  replayDigest: string;
  eventCount: number;
  timeline: readonly TwinTimelineItem[];
  stateBars: readonly TwinStateBar[];
  modes: readonly TwinModeEvidence[];
  detail: string;
}

export function projectTwinVisualization(
  snapshot: OperationsSnapshot,
): TwinVisualizationProjection {
  const simulation = snapshot.simulation;
  const replay = snapshot.replay;
  const isSimulation = snapshot.source === "simulation" && Boolean(simulation);
  const isReplay = snapshot.source === "replay" && Boolean(replay);
  const scenarioId = simulation?.scenarioId ?? replay?.scenarioId ?? "unavailable";
  const seed = simulation?.seed ?? replay?.seed ?? 0;
  const clockDomain = simulation?.clockDomain ?? replay?.clockDomain ?? "SIMULATED";
  const currentSeconds = simulation?.simulatedTimeSeconds ?? replay?.cursorSeconds ?? 0;
  const durationSeconds = replay?.durationSeconds ?? Math.max(currentSeconds, 1);
  const status = simulation?.status ?? replay?.status ?? "unavailable";
  const speed = simulation?.speed ?? replay?.speed ?? 1;
  const replayDigest = simulation?.replayDigest ?? replay?.replayDigest ?? "";
  const rawEvents = simulation?.events ?? replay?.visibleEvents ?? [];
  const timeline = rawEvents.slice(-12).map((event) => ({
    eventId: event.eventId,
    eventType: event.eventType,
    seconds: event.simulatedTimeSeconds,
    detail:
      "commandId" in event
        ? `${event.commandId}${event.details.length ? ` · ${event.details[0][1]}` : ""}`
        : event.details.length
          ? event.details[0][1]
          : "recorded replay event",
  }));
  const modes: TwinModeEvidence[] = [
    {
      mode: "simulation",
      status: isSimulation ? "active" : simulation ? "available" : "unavailable",
      detail: isSimulation
        ? "Live Digital Twin control state is attached."
        : simulation
          ? "Simulation state is attached but another mode is selected."
          : "No simulation control state is attached.",
    },
    {
      mode: "replay",
      status: isReplay ? "active" : replay ? "available" : "unavailable",
      detail: isReplay
        ? replay?.verified
          ? "Verified replay artifact is selected."
          : "Replay artifact is selected but verification is incomplete."
        : replay
          ? "Replay artifact is attached but another mode is selected."
          : "No verified replay artifact is attached.",
    },
    {
      mode: "benchmark",
      status: "unavailable",
      detail: "RouteBench benchmark artifacts are separate from simulation and replay state.",
    },
  ];
  const eventProgress =
    durationSeconds > 0 ? Math.min(100, (currentSeconds / durationSeconds) * 100) : 0;
  const stateBars: TwinStateBar[] = [
    {
      label: "Clock",
      value: eventProgress,
      detail: `${currentSeconds.toFixed(0)} / ${durationSeconds.toFixed(0)}s`,
    },
    {
      label: "Events",
      value: Math.min(100, rawEvents.length * 10),
      detail: `${rawEvents.length} shown of ${simulation?.eventCount ?? replay?.events.length ?? 0}`,
    },
    {
      label: "Replay digest",
      value: replayDigest ? 100 : 0,
      detail: replayDigest ? replayDigest.slice(0, 16) : "unavailable",
    },
  ];
  return {
    sourceLabel: snapshot.source.toUpperCase(),
    scenarioId,
    seed,
    clockDomain,
    status,
    currentSeconds,
    durationSeconds,
    speed,
    replayDigest,
    eventCount: simulation?.eventCount ?? replay?.events.length ?? 0,
    timeline,
    stateBars,
    modes,
    detail:
      snapshot.source === "simulation"
        ? "Simulation state is bounded to the attached Digital Twin control API."
        : snapshot.source === "replay"
          ? "Replay state is read from a verified artifact and does not issue simulation commands."
          : "Twin visualization is unavailable until a simulation or replay source is selected.",
  };
}
