import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { createCityOperationalDataset } from "../visuals/cityGeo";
import { GeoWorldFallback } from "./GeoWorldFallback";

describe("geo world fallback", () => {
  it("preserves city geography, routes, and explicit demo provenance", () => {
    const dataset = createCityOperationalDataset("shenzhen");
    render(<GeoWorldFallback dataset={dataset} reason="WebGL unavailable" />);

    expect(
      screen.getByRole("region", { name: "Shenzhen geographic fallback" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("img", { name: "Shenzhen static courier route geography" }),
    ).toBeInTheDocument();
    expect(screen.getByText("GEOGRAPHIC FALLBACK / DEMO")).toBeInTheDocument();
    expect(screen.getByText("SIMULATED")).toBeInTheDocument();
    expect(screen.getByText(/WebGL unavailable/)).toBeInTheDocument();
  });
});
