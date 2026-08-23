import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { demoDataSource } from "../data/demoSnapshot";
import { FlowVisualizationPanel } from "./FlowVisualizationPanel";

describe("flow visualization panel", () => {
  it("shows source, flow units, and selected record evidence", () => {
    render(
      <FlowVisualizationPanel
        snapshot={demoDataSource.getSnapshot()}
        now={new Date("2026-08-22T09:49:00Z")}
      />,
    );

    expect(
      screen.getByRole("heading", { name: "Data-backed flow visualization" }),
    ).toBeInTheDocument();
    expect(screen.getByText(/DEMO source · Fresh snapshot/)).toBeInTheDocument();
    expect(screen.getByText("orders represented")).toBeInTheDocument();
    expect(
      screen.getByRole("img", { name: /derived from 3 route-bearing order records/ }),
    ).toBeInTheDocument();
    expect(screen.getByText(/Arcs are derived from order route records/)).toBeInTheDocument();

    const firstFlow = screen.getAllByRole("button")[0];
    fireEvent.click(firstFlow);
    expect(screen.getByRole("heading", { name: /Selected flow evidence/ })).toBeInTheDocument();
    expect(screen.getByText(/coordinates averaged from each route endpoint/)).toBeInTheDocument();
  });

  it("renders an honest empty state when no route records exist", () => {
    const snapshot = demoDataSource.getSnapshot();
    render(
      <FlowVisualizationPanel
        snapshot={{
          ...snapshot,
          orders: snapshot.orders.map((order) => ({ ...order, route: [] })),
        }}
        now={new Date("2026-08-22T09:49:00Z")}
      />,
    );

    expect(screen.getByRole("status")).toHaveTextContent("No order route records");
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
  });
});
