import { describe, expect, it, vi } from "vitest";
import { createSimulationDataSource } from "./simulation";

function response(body: unknown): Response {
  return { ok: true, json: async () => body } as Response;
}

const state = {
  scenario_id: "control-default",
  seed: 7,
  strategy: "nearest",
  strategy_version: "1.0.0",
  status: "paused",
  speed: 1,
  simulated_time_seconds: 0,
  tick: 0,
  generation: 0,
  event_count: 0,
  last_command_id: null,
  replay_digest: "digest-1",
};

describe("simulation data source", () => {
  it("loads state and merges command events into the operations snapshot", async () => {
    const fetchImpl = vi
      .fn<typeof fetch>()
      .mockResolvedValueOnce(response(state))
      .mockResolvedValueOnce(
        response({
          state: {
            ...state,
            simulated_time_seconds: 60,
            tick: 1,
            event_count: 1,
            replay_digest: "digest-2",
          },
          events: [
            {
              event_id: "event-1",
              event_type: "simulation.started",
              simulated_time_seconds: 0,
              command_id: "start-1",
              details: [],
            },
          ],
        }),
      );
    const source = createSimulationDataSource(fetchImpl);

    const loaded = await source.loadSnapshot?.();
    expect(loaded?.source).toBe("simulation");
    const next = await source.controlSimulation?.({
      commandId: "start-1",
      action: "step",
      seconds: 60,
    });
    expect(next?.simulation?.simulatedTimeSeconds).toBe(60);
    expect(next?.simulation?.events[0].eventType).toBe("simulation.started");
  });

  it("keeps source failures explicit", async () => {
    const source = createSimulationDataSource(
      vi.fn<typeof fetch>().mockRejectedValue(new Error("offline")),
    );
    const snapshot = await source.loadSnapshot?.();
    expect(snapshot?.availability).toBe("unavailable");
    expect(snapshot?.sourceDetail).toContain("Simulation unavailable");
  });
});
