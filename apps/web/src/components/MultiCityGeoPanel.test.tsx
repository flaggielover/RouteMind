import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { MultiCityGeoPanel } from "./MultiCityGeoPanel";

describe("multi-city geo operations panel", () => {
  it("labels demo data and hides raw points at national scale", () => {
    render(<MultiCityGeoPanel />);

    expect(screen.getByText("DEMO data · coordinate-backed signals")).toBeInTheDocument();
    expect(
      screen.getByText(
        "Scope zoom 4: city-centroid aggregation hides raw points at national scale.",
      ),
    ).toBeInTheDocument();
    expect(screen.getByText("Shanghai")).toBeInTheDocument();
  });

  it("switches to city detail and exposes operational-point semantics", () => {
    render(<MultiCityGeoPanel />);

    fireEvent.click(screen.getByRole("tab", { name: "City detail" }));

    expect(
      screen.getByText("City detail: operational points may render within this city."),
    ).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "City detail" })).toHaveAttribute(
      "aria-selected",
      "true",
    );
  });
});
