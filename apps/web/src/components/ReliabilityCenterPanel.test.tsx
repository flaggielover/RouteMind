import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { demoDataSource } from "../data/demoSnapshot";
import type { RealtimeConnectionState } from "../data/realtime";
import type { ServiceHealth } from "../domain/model";
import { ReliabilityCenterPanel } from "./ReliabilityCenterPanel";

const realtime: RealtimeConnectionState = {
  status: "disabled",
  cursor: "0",
  detail: "Realtime disabled for supplied data source",
  appliedEvents: 0,
  staleReason: null,
  recentEvents: [],
};

const health: ServiceHealth[] = [
  {
    service: "business-api",
    label: "Business API",
    status: "healthy",
    endpoint: "/actuator/health",
    checkedAt: "2026-08-24T00:00:00Z",
    detail: "UP",
  },
];

describe("Reliability Center panel", () => {
  it("renders bounded timeline, invariant, dependency, and recovery evidence", () => {
    render(
      <ReliabilityCenterPanel
        snapshot={demoDataSource.getSnapshot()}
        health={health}
        realtime={realtime}
      />,
    );

    expect(screen.getByRole("status")).toHaveTextContent("FIXTURE");
    expect(screen.getByText("Reliability timeline")).toBeInTheDocument();
    expect(screen.getByText("Invariant matrix")).toBeInTheDocument();
    expect(screen.getByText("Continuous reconciliation")).toBeInTheDocument();
    expect(screen.getByText("Dependencies and trace links")).toBeInTheDocument();
    expect(screen.getByText("Recovery evidence")).toBeInTheDocument();
    expect(screen.getByText("Autonomous remediation")).toBeInTheDocument();
    expect(screen.getAllByText("unavailable").length).toBeGreaterThanOrEqual(2);
  });
});
