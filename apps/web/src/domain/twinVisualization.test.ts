import { describe, expect, it } from "vitest";
import { demoDataSource } from "../data/demoSnapshot";
import { projectTwinVisualization } from "./twinVisualization";
import type { OperationsSnapshot } from "./model";

describe("twin visualization projection", () => {
  it("keeps simulation state, bounded timeline, and distinct mode evidence", () => {
    const base = demoDataSource.getSnapshot();
    const snapshot: OperationsSnapshot = {
      ...base,
      source: "simulation",
      clockDomain: "SIMULATED",
      simulation: {
        clockDomain: "SIMULATED",
        scenarioId: "control-default",
        seed: 7,
        strategy: "nearest",
        strategyVersion: "1.0.0",
        status: "running",
        speed: 2,
        simulatedTimeSeconds: 60,
        tick: 1,
        generation: 0,
        eventCount: 20,
        lastCommandId: "step-1",
        replayDigest: "a".repeat(64),
        events: Array.from({ length: 20 }, (_, index) => ({
          eventId: `event-${index}`,
          eventType: "simulation.tick",
          simulatedTimeSeconds: index * 3,
          commandId: "step-1",
          details: [["tick", String(index)] as const],
        })),
      },
    };
    const projection = projectTwinVisualization(snapshot);
    expect(projection.clockDomain).toBe("SIMULATED");
    expect(projection.timeline).toHaveLength(12);
    expect(projection.modes.map((mode) => mode.status)).toEqual([
      "active",
      "unavailable",
      "unavailable",
    ]);
    expect(projection.stateBars[0].value).toBe(100);
    expect(projection.replayDigest).toHaveLength(64);
  });

  it("labels a verified replay separately and never claims benchmark evidence", () => {
    const base = demoDataSource.getSnapshot();
    const snapshot: OperationsSnapshot = {
      ...base,
      source: "replay",
      clockDomain: "REPLAY",
      replay: {
        clockDomain: "REPLAY",
        artifactId: "artifact-1",
        scenarioId: "scenario-1",
        seed: 3,
        status: "ready",
        verified: true,
        cursorSeconds: 10,
        durationSeconds: 100,
        speed: 1,
        replayDigest: "b".repeat(64),
        provenance: "fixture",
        events: [
          { eventId: "e1", eventType: "order.created", simulatedTimeSeconds: 5, details: [] },
        ],
        visibleEvents: [
          { eventId: "e1", eventType: "order.created", simulatedTimeSeconds: 5, details: [] },
        ],
        verificationError: null,
      },
    };
    const projection = projectTwinVisualization(snapshot);
    expect(projection.clockDomain).toBe("REPLAY");
    expect(projection.modes[1].status).toBe("active");
    expect(projection.modes[2].status).toBe("unavailable");
    expect(projection.detail).toContain("verified artifact");
  });

  it("is explicit when no twin artifact is attached", () => {
    const projection = projectTwinVisualization(demoDataSource.getSnapshot());
    expect(projection.status).toBe("unavailable");
    expect(projection.modes.every((mode) => mode.status === "unavailable")).toBe(true);
    expect(projection.detail).toContain("unavailable");
  });
});
