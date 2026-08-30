import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { demoDataSource } from "../data/demoSnapshot";
import { OperationsAnalyticalStrip } from "./AnalyticalVisualizationFoundation";

describe("analytical visualization foundation", () => {
  it("renders representative operational chart surfaces with provenance", () => {
    const { container } = render(
      <OperationsAnalyticalStrip snapshot={demoDataSource.getSnapshot()} />,
    );

    expect(
      screen.getByRole("heading", {
        name: "Operational signals, rendered with one visual language.",
      }),
    ).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Network throughput" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "SLA / risk trend" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Latency / throughput" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Strategy distribution" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Zone pressure field" })).toBeInTheDocument();
    expect(screen.getByText("Visual demo · non-production")).toBeInTheDocument();
    expect(container.querySelectorAll(".chart-point").length).toBeGreaterThan(10);
    expect(container.querySelectorAll(".heatmap-cell").length).toBe(24);
  });
});
