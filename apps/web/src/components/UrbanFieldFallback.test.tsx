import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { demoDataSource } from "../data/demoSnapshot";
import { toUrbanFieldState } from "../visuals/urbanFieldState";
import { UrbanFieldFallback } from "./UrbanFieldFallback";

describe("urban field fallback", () => {
  it("keeps semantic metrics visible when WebGL is unavailable", () => {
    render(<UrbanFieldFallback state={toUrbanFieldState(demoDataSource.getSnapshot())} />);

    expect(
      screen.getByRole("img", { name: "RouteMind urban field fallback summary" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Demo · non-production")).toBeInTheDocument();
    expect(screen.getByText(/WebGL is unavailable in this environment/)).toBeInTheDocument();
    expect(screen.getByText("Pressure").parentElement).toHaveTextContent("50%");
  });
});
