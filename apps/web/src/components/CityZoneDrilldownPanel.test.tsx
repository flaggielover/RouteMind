import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { demoDataSource } from "../data/demoSnapshot";
import { CityZoneDrilldownPanel } from "./CityZoneDrilldownPanel";

describe("city zone drilldown panel", () => {
  it("shows source, freshness, units, and zone metrics", () => {
    render(<CityZoneDrilldownPanel snapshot={demoDataSource.getSnapshot()} />);

    expect(screen.getAllByText("DEMO source").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("City / zone drilldown")).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Density / 100" })).toBeInTheDocument();
    expect(screen.getByText("North Loop")).toBeInTheDocument();
    expect(screen.getByText(/Derived from the selected Operations snapshot/)).toBeInTheDocument();
  });

  it("changes aggregation with zoom and renders stale/empty state labels", () => {
    const snapshot = demoDataSource.getSnapshot();
    render(<CityZoneDrilldownPanel snapshot={snapshot} />);

    fireEvent.change(screen.getByLabelText("Zoom 11"), { target: { value: "6" } });
    expect(screen.getByText("City aggregate")).toBeInTheDocument();
    expect(screen.getByText("City total")).toBeInTheDocument();

    const emptySnapshot = { ...snapshot, orders: [], couriers: [], merchants: [] };
    render(<CityZoneDrilldownPanel snapshot={emptySnapshot} />);
    expect(screen.getByText(/Empty source/)).toBeInTheDocument();
    expect(screen.getByText(/No orders, merchants, or couriers/)).toBeInTheDocument();
  });
});
