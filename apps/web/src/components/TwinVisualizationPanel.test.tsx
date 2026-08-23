import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { demoDataSource } from "../data/demoSnapshot";
import type { OperationsSnapshot } from "../domain/model";
import { TwinVisualizationPanel } from "./TwinVisualizationPanel";

describe("TwinVisualizationPanel", () => {
  it("renders bounded simulation state and separate execution modes", () => {
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
        speed: 1,
        simulatedTimeSeconds: 60,
        tick: 1,
        generation: 0,
        eventCount: 1,
        lastCommandId: "step-1",
        replayDigest: "a".repeat(64),
        events: [
          {
            eventId: "event-1",
            eventType: "order.assigned",
            simulatedTimeSeconds: 60,
            commandId: "step-1",
            details: [],
          },
        ],
      },
    };
    render(<TwinVisualizationPanel snapshot={snapshot} />);
    expect(
      screen.getByRole("heading", { name: "Compare clock, state, and replay provenance." }),
    ).toBeInTheDocument();
    expect(screen.getByText("simulation")).toBeInTheDocument();
    expect(screen.getByText("benchmark")).toBeInTheDocument();
    expect(screen.getAllByText("unavailable")).toHaveLength(2);
    expect(screen.getByText("timeline · order / assigned")).toBeInTheDocument();
  });
});
