import { demoDataSource } from "./demoSnapshot";
import type {
  OperationsDataSource,
  OperationsSnapshot,
  ReplayAction,
  ReplayCommand,
  ReplayEvent,
  ReplaySnapshot,
} from "../domain/model";

export interface ReplayArtifact {
  artifactId: string;
  scenarioId: string;
  seed: number;
  provenance: string;
  events: readonly ReplayEvent[];
  digest: string;
}

const artifactPayload = {
  artifactId: "replay-control-default-v1",
  scenarioId: "control-default",
  seed: 7,
  provenance: "seeded local fixture; source simulation control API",
  events: [
    {
      eventId: "replay:order-1:created",
      eventType: "order.created",
      simulatedTimeSeconds: 0,
      details: [["order_id", "order-1"]] as const,
    },
    {
      eventId: "replay:order-1:assigned",
      eventType: "dispatch.decision.recorded",
      simulatedTimeSeconds: 30,
      details: [["courier_id", "courier-1"]] as const,
    },
    {
      eventId: "replay:order-1:delivered",
      eventType: "order.status.changed",
      simulatedTimeSeconds: 90,
      details: [["status", "DELIVERED"]] as const,
    },
  ] as const,
};

export const replayArtifact: ReplayArtifact = {
  ...artifactPayload,
  digest: "8614e7962a3a2f341d8a90729642dbb49311f095293a0661c89e92d57d0f0a63",
};

function canonicalArtifact(artifact: ReplayArtifact): string {
  return JSON.stringify({
    artifactId: artifact.artifactId,
    scenarioId: artifact.scenarioId,
    seed: artifact.seed,
    provenance: artifact.provenance,
    events: artifact.events,
  });
}

async function sha256Hex(value: string): Promise<string> {
  const bytes = new TextEncoder().encode(value);
  const digest = await globalThis.crypto.subtle.digest("SHA-256", bytes);
  return [...new Uint8Array(digest)].map((byte) => byte.toString(16).padStart(2, "0")).join("");
}

export async function verifyReplayArtifact(artifact: ReplayArtifact): Promise<boolean> {
  return (await sha256Hex(canonicalArtifact(artifact))) === artifact.digest;
}

function emptyReplay(status: ReplaySnapshot["status"] = "verifying"): ReplaySnapshot {
  return {
    clockDomain: "REPLAY",
    artifactId: replayArtifact.artifactId,
    scenarioId: replayArtifact.scenarioId,
    seed: replayArtifact.seed,
    status,
    verified: false,
    cursorSeconds: 0,
    durationSeconds: 90,
    speed: 1,
    replayDigest: replayArtifact.digest,
    provenance: replayArtifact.provenance,
    events: [],
    visibleEvents: [],
    verificationError: null,
  };
}

function operationSnapshot(replay: ReplaySnapshot, detail: string): OperationsSnapshot {
  const base = demoDataSource.getSnapshot();
  return {
    ...base,
    source: "replay",
    clockDomain: "REPLAY",
    availability:
      replay.status === "invalid"
        ? "unavailable"
        : replay.status === "verifying"
          ? "loading"
          : "ready",
    sourceDetail: detail,
    generatedAt: new Date().toISOString(),
    replay,
  };
}

function withCursor(
  replay: ReplaySnapshot,
  cursorSeconds: number,
  status = replay.status,
): ReplaySnapshot {
  const cursor = Math.max(0, Math.min(replay.durationSeconds, cursorSeconds));
  return {
    ...replay,
    status,
    cursorSeconds: cursor,
    visibleEvents: replay.events.filter((event) => event.simulatedTimeSeconds <= cursor),
  };
}

function applyReplayCommand(replay: ReplaySnapshot, command: ReplayCommand): ReplaySnapshot {
  if (!replay.verified) throw new Error("Replay artifact is not verified");
  if (command.action === "play") return { ...replay, status: "playing" };
  if (command.action === "pause") return { ...replay, status: "paused" };
  if (command.action === "reset") return withCursor(replay, 0, "paused");
  if (command.action === "seek") return withCursor(replay, command.seconds ?? 0, "paused");
  if (command.action === "step")
    return withCursor(
      replay,
      replay.cursorSeconds + (command.seconds ?? 1) * replay.speed,
      "paused",
    );
  if (command.action === "speed") {
    if (command.speed === undefined || command.speed < 0.1 || command.speed > 10) {
      throw new Error("Replay speed must be between 0.1 and 10");
    }
    return { ...replay, speed: command.speed };
  }
  const unsupported: ReplayAction = command.action;
  throw new Error(`Unsupported replay action: ${unsupported}`);
}

export function createReplayDataSource(): OperationsDataSource {
  let current = operationSnapshot(emptyReplay("invalid"), "Select a verified replay artifact");
  return {
    getSnapshot: () => current,
    loadSnapshot: async () => {
      try {
        const verified = await verifyReplayArtifact(replayArtifact);
        if (!verified) {
          current = operationSnapshot(
            {
              ...emptyReplay("invalid"),
              verificationError: "Replay digest does not match artifact payload",
            },
            "Replay unavailable: digest verification failed",
          );
          return current;
        }
        const replay: ReplaySnapshot = {
          ...emptyReplay("ready"),
          verified: true,
          events: replayArtifact.events,
          replayDigest: replayArtifact.digest,
        };
        current = operationSnapshot(withCursor(replay, 0, "ready"), "Verified replay artifact");
      } catch (error) {
        const detail = error instanceof Error ? error.message : "Replay verification unavailable";
        current = operationSnapshot(
          { ...emptyReplay("invalid"), verificationError: detail },
          `Replay unavailable: ${detail}`,
        );
      }
      return current;
    },
    controlReplay: async (command: ReplayCommand) => {
      current = operationSnapshot(
        applyReplayCommand(current.replay ?? emptyReplay("invalid"), command),
        "Verified replay artifact",
      );
      return current;
    },
  };
}

export const replayDataSource = createReplayDataSource();
