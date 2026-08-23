import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { demoDataSource } from "../data/demoSnapshot";
import { DecisionXrayPanel } from "./DecisionXrayPanel";

describe("DecisionXrayPanel", () => {
  it("renders structured decision evidence and labels inferred fields honestly", () => {
    render(<DecisionXrayPanel snapshot={demoDataSource.getSnapshot()} />);

    const panel = screen.getByRole("region", { name: "Decision X-Ray" });
    expect(within(panel).getByRole("heading", { name: "Decision X-Ray" })).toBeInTheDocument();
    expect(panel.querySelector(".eyebrow")?.textContent).toContain("read-only snapshot projection");
    expect(within(panel).getAllByText("courier-17").length).toBeGreaterThan(0);
    expect(within(panel).getByText("Travel evidence")).toBeInTheDocument();
    expect(
      within(panel).getByText("unavailable", { selector: ".decision-xray-state" }),
    ).toBeInTheDocument();
    expect(within(panel).getByText("courier is already on route")).toBeInTheDocument();
    expect(
      within(panel).getByText(
        "No provider travel metric is present; no travel duration is inferred.",
      ),
    ).toBeInTheDocument();
    expect(within(panel).getByText("not-captured")).toBeInTheDocument();
  });
});
