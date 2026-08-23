import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { demoDataSource } from "../data/demoSnapshot";
import { GeoAnalyticalLayersPanel } from "./GeoAnalyticalLayersPanel";

describe("geo analytical layers panel", () => {
  it("shows source, toggles, scales, units, and disabled unavailable layers", () => {
    render(
      <GeoAnalyticalLayersPanel
        snapshot={demoDataSource.getSnapshot()}
        now={new Date("2026-08-22T09:49:00Z")}
      />,
    );

    expect(screen.getByRole("heading", { name: "Geo analytical layers" })).toBeInTheDocument();
    expect(screen.getByText(/DEMO source · Fresh snapshot/)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Order demand" })).toBeInTheDocument();
    expect(screen.getAllByText("0–N orders").length).toBeGreaterThan(0);
    expect(screen.getByText(/Disabled layers are not inferred:/i)).toBeInTheDocument();
    expect(screen.getByRole("checkbox", { name: /Congestion/ })).toBeDisabled();
  });

  it("hides a layer after its evidence-backed toggle is cleared", () => {
    render(
      <GeoAnalyticalLayersPanel
        snapshot={demoDataSource.getSnapshot()}
        now={new Date("2026-08-22T09:49:00Z")}
      />,
    );

    fireEvent.click(screen.getByRole("checkbox", { name: /Order demand/ }));
    expect(screen.queryByRole("heading", { name: "Order demand" })).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Courier supply" })).toBeInTheDocument();
  });
});
