import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { SimulationControlPanel } from "./SimulationControlPanel";
import type { SimulationSnapshot } from "../domain/model";

const snapshot: SimulationSnapshot = {
  scenarioId: "control-default",
  seed: 7,
  strategy: "nearest",
  strategyVersion: "1.0.0",
  status: "paused",
  speed: 1,
  simulatedTimeSeconds: 0,
  tick: 0,
  generation: 0,
  eventCount: 1,
  lastCommandId: "reset-1",
  replayDigest: "0123456789abcdef0123456789abcdef",
  events: [
    {
      eventId: "event-1",
      eventType: "simulation.reset",
      simulatedTimeSeconds: 0,
      commandId: "reset-1",
      details: [],
    },
  ],
};

describe("SimulationControlPanel", () => {
  it("exposes scenario controls, metrics, and event provenance", () => {
    render(
      <SimulationControlPanel
        snapshot={snapshot}
        demandCount={2}
        supplyCount={2}
        trafficLabel="seeded 1.0x"
        onControl={vi.fn().mockResolvedValue(undefined)}
      />,
    );

    expect(
      screen.getByRole("heading", { name: "Control the scenario clock." }),
    ).toBeInTheDocument();
    expect(screen.getByText("2 orders")).toBeInTheDocument();
    expect(screen.getByText("seeded 1.0x")).toBeInTheDocument();
    expect(screen.getByText("simulation.reset")).toBeInTheDocument();
    expect(screen.getByDisplayValue("control-default")).toBeInTheDocument();
  });

  it("sends bounded playback and parameter commands", async () => {
    const user = userEvent.setup();
    const onControl = vi.fn().mockResolvedValue(undefined);
    render(
      <SimulationControlPanel
        snapshot={snapshot}
        demandCount={2}
        supplyCount={2}
        trafficLabel="seeded 1.0x"
        onControl={onControl}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Resume" }));
    await user.click(screen.getByRole("button", { name: /Step/ }));
    await user.click(screen.getByRole("button", { name: "Reset simulation" }));

    expect(onControl).toHaveBeenCalledTimes(3);
    expect(onControl.mock.calls.map(([command]) => command.action)).toEqual([
      "resume",
      "step",
      "reset",
    ]);
  });
});
