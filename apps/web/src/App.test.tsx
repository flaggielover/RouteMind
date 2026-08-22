import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import { demoDataSource } from "./data/demoSnapshot";
import type { ServiceHealth } from "./domain/model";

const healthyServices: ServiceHealth[] = [
  {
    service: "business-api",
    label: "Business API",
    status: "healthy",
    endpoint: "",
    checkedAt: "",
    detail: "Healthy response",
  },
  {
    service: "compute-api",
    label: "Compute API",
    status: "healthy",
    endpoint: "",
    checkedAt: "",
    detail: "Healthy response",
  },
];

function renderApp() {
  return render(
    <App dataSource={demoDataSource} healthProbe={vi.fn().mockResolvedValue(healthyServices)} />,
  );
}

describe("role-aware application", () => {
  beforeEach(() => {
    window.history.replaceState({}, "", "/operations");
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("shows the operations lifecycle and an explicit demo source", async () => {
    renderApp();

    expect(await screen.findByText("Demo snapshot")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Keep the city moving." })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "RM-2041 lifecycle" })).toBeInTheDocument();
    expect(screen.getByText("Delivered", { selector: ".status-pill span" })).toBeInTheDocument();
    expect(screen.getByRole("list", { name: "Lifecycle for RM-2041" })).toBeInTheDocument();
  });

  it("switches role routes without duplicating the application shell", async () => {
    const user = userEvent.setup();
    renderApp();

    await user.click(screen.getByRole("link", { name: /Strategy lab/ }));

    expect(
      await screen.findByRole("heading", { name: "Decisions you can inspect." }),
    ).toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: "RouteMind navigation" })).toBeInTheDocument();
    expect(screen.getByText("weighted-greedy", { selector: "strong" })).toBeInTheDocument();
  });

  it("allows the operator to focus a different order on the shared map and queue", async () => {
    const user = userEvent.setup();
    renderApp();

    const queue = screen.getByRole("region", { name: "Orders in motion" });
    await user.click(within(queue).getByRole("button", { name: /RM-2042/ }));

    expect(screen.getByRole("heading", { name: "RM-2042 lifecycle" })).toBeInTheDocument();
    expect(screen.getByRole("list", { name: "Lifecycle for RM-2042" })).toBeInTheDocument();
  });

  it("applies lifecycle and exception filters to the operational queue", async () => {
    const user = userEvent.setup();
    renderApp();

    await user.click(screen.getByRole("button", { name: /Filter board/ }));
    await user.selectOptions(screen.getByLabelText("Lifecycle"), "OUT_FOR_DELIVERY");
    expect(screen.getByText("Showing 1 of 3")).toBeInTheDocument();
    const queue = screen.getByRole("region", { name: "Orders in motion" });
    expect(within(queue).getByRole("button", { name: /RM-2042/ })).toBeInTheDocument();
    expect(within(queue).queryByRole("button", { name: /RM-2041/ })).not.toBeInTheDocument();
  });

  it("links recorded exceptions to the affected order", async () => {
    const user = userEvent.setup();
    renderApp();

    const alerts = screen.getByRole("region", { name: "Operations alerts and imbalance" });
    await user.click(within(alerts).getByRole("button", { name: /RM-2042/ }));
    expect(screen.getByRole("heading", { name: "RM-2042 lifecycle" })).toBeInTheDocument();
    expect(within(alerts).getByText("1 order gap")).toBeInTheDocument();
    expect(within(alerts).getByText("Unavailable from source")).toBeInTheDocument();
  });

  it("shows customer lifecycle freshness and keeps demo writes disabled", async () => {
    const user = userEvent.setup();
    renderApp();

    await user.click(screen.getByRole("link", { name: /Customer/ }));

    expect(
      await screen.findByRole("heading", { name: "Your delivery, clearly explained." }),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Version unknown · Deterministic fixture for offline demonstration"),
    ).toBeInTheDocument();
    const createOrder = screen.getByRole("button", { name: "Create order" });
    expect(createOrder).toBeDisabled();
    expect(
      screen.getByText("Writing is disabled for demo and replay sources."),
    ).toBeInTheDocument();
  });

  it("shows the merchant lifecycle action while keeping demo commands disabled", async () => {
    const user = userEvent.setup();
    renderApp();

    await user.click(screen.getByRole("link", { name: /Merchant/ }));

    expect(
      await screen.findByRole("heading", { name: "Prep with the handoff in view." }),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Mark ready" })).toBeDisabled();
    expect(
      screen.getByText("Writing is disabled for demo and replay sources."),
    ).toBeInTheDocument();
  });

  it("shows the courier golden path while keeping demo commands disabled", async () => {
    const user = userEvent.setup();
    renderApp();

    await user.click(screen.getByRole("link", { name: /Courier/ }));

    expect(
      await screen.findByRole("heading", { name: "A focused shift, one next action." }),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Complete delivery" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Go online" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Send location" })).toBeDisabled();
    expect(
      screen.getByText("Writing is disabled for demo and replay sources."),
    ).toBeInTheDocument();
  });

  it("keeps live failure explicit while switching through demo and replay modes", async () => {
    const user = userEvent.setup();
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));
    render(<App healthProbe={vi.fn().mockResolvedValue(healthyServices)} />);

    expect(await screen.findByText("Live unavailable")).toBeInTheDocument();
    const source = screen.getByRole("combobox", { name: "Data source mode" });
    await user.selectOptions(source, "demo");
    expect(await screen.findByText("Demo snapshot")).toBeInTheDocument();
    await user.selectOptions(source, "replay");
    expect(
      await screen.findByText("Replay", { selector: ".source-status span" }),
    ).toBeInTheDocument();
    expect(screen.getAllByText("Select a verified replay artifact").length).toBeGreaterThan(0);
  });
});
