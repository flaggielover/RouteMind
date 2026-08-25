import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { BrowserRouter } from "react-router-dom";
import App, { AppRoutes } from "./App";
import { demoDataSource } from "./data/demoSnapshot";
import type { ServiceHealth } from "./domain/model";
import type { TenantSession } from "./data/session";

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

const customerSession: TenantSession = {
  tenantId: "10000000-0000-4000-8000-000000000001",
  subject: "customer-42",
  roles: ["customer"],
  accessToken: "access-token",
  expiresAt: "2099-08-25T10:00:00Z",
};

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

  it("fails closed when a deep link is outside the verified session roles", () => {
    window.history.replaceState({}, "", "/merchant");
    render(
      <BrowserRouter>
        <AppRoutes
          snapshot={demoDataSource.getSnapshot()}
          realtime={{
            status: "disabled",
            cursor: "0",
            detail: "test",
            appliedEvents: 0,
            staleReason: null,
            recentEvents: [],
          }}
          health={healthyServices}
          session={customerSession}
          allowedRoles={customerSession.roles}
        />
      </BrowserRouter>,
    );

    expect(screen.getByRole("alert")).toHaveTextContent(
      "not authorized for the merchant workspace",
    );
    expect(screen.queryByRole("heading", { name: "Prep with the handoff in view." })).toBeNull();
  });

  it("clears cached role data before accepting a changed tenant session", async () => {
    window.history.replaceState({}, "", "/customer");
    const merchantSession: TenantSession = {
      ...customerSession,
      tenantId: "20000000-0000-4000-8000-000000000002",
      subject: "merchant-7",
      roles: ["merchant"],
      accessToken: "merchant-token",
    };
    let releaseMerchant!: () => void;
    const merchantPending = new Promise<void>((resolve) => {
      releaseMerchant = resolve;
    });
    const sessionProvider = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        session: customerSession,
        detail: "Verified tenant session is active",
      })
      .mockImplementationOnce(async () => {
        await merchantPending;
        return {
          ok: true,
          session: merchantSession,
          detail: "Verified tenant session is active",
        };
      });
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: string | URL | Request, init?: RequestInit) => {
        const url = String(input);
        if (url.includes("/api/v1/operations/snapshot")) {
          return new Response(
            JSON.stringify({
              source: "live",
              generatedAt: "2026-08-25T10:00:00Z",
              orders: [],
              parties: [],
              courierLocations: [],
            }),
            { status: 200 },
          );
        }
        if (url.includes("/api/v1/dispatch/snapshot")) {
          return new Response(
            JSON.stringify({
              source: "live",
              strategy: "weighted-greedy",
              strategy_version: "1.0.0",
              selected_courier: null,
              score: null,
              rationale: ["No candidates"],
              latency_millis: 1,
              trace_id: "trace-session-change",
            }),
            { status: 200 },
          );
        }
        if (url.includes("/api/v1/events/stream")) {
          return await new Promise<Response>((_resolve, reject) => {
            init?.signal?.addEventListener("abort", () =>
              reject(new DOMException("aborted", "AbortError")),
            );
          });
        }
        throw new Error(`Unexpected request: ${url}`);
      }),
    );
    render(
      <App
        healthProbe={vi.fn().mockResolvedValue(healthyServices)}
        sessionProvider={sessionProvider}
      />,
    );

    expect(
      await screen.findByRole("heading", { name: "Your delivery, clearly explained." }),
    ).toBeInTheDocument();
    act(() => window.dispatchEvent(new Event("routemind:session-changed")));
    await waitFor(() =>
      expect(
        screen.queryByRole("heading", { name: "Your delivery, clearly explained." }),
      ).toBeNull(),
    );
    expect(screen.getByRole("alert")).toHaveTextContent(
      "not authorized for the customer workspace",
    );

    releaseMerchant();
    expect(await screen.findByRole("link", { name: /Merchant/ })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /Customer/ })).toBeNull();
  });

  it("opens the mobile workspace drawer and closes it on escape or navigation", async () => {
    const user = userEvent.setup();
    renderApp();

    const toggle = screen.getByRole("button", { name: "Open workspace navigation" });
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    await user.click(toggle);
    expect(screen.getByRole("navigation", { name: "RouteMind navigation" })).toBeInTheDocument();
    expect(toggle).toHaveAttribute("aria-expanded", "true");

    await user.keyboard("{Escape}");
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    await user.click(toggle);
    await user.click(screen.getByRole("link", { name: /Courier/ }));
    expect(
      await screen.findByRole("heading", { name: "A focused shift, one next action." }),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Open workspace navigation" })).toHaveAttribute(
      "aria-expanded",
      "false",
    );
  });

  it("keeps customer, merchant, and courier actions explicit on the role surfaces", async () => {
    const user = userEvent.setup();
    renderApp();

    await user.click(screen.getByRole("link", { name: /Customer/ }));
    expect(screen.getByRole("button", { name: "Create order" })).toBeVisible();
    await user.click(screen.getByRole("link", { name: /Merchant/ }));
    expect(screen.getByRole("button", { name: "Mark ready" })).toBeVisible();
    await user.click(screen.getByRole("link", { name: /Courier/ }));
    expect(screen.getByRole("button", { name: "Complete delivery" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Go online" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Send location" })).toBeVisible();
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
    expect(
      await screen.findByRole("heading", { name: "Inspect the recorded run." }),
    ).toBeInTheDocument();
    expect(screen.getByText(/Digest verified/)).toBeInTheDocument();
  });

  it("disables role writes when a supplied live fixture has no verified identity", async () => {
    const user = userEvent.setup();
    const degradedSource = {
      getSnapshot: () => ({
        ...demoDataSource.getSnapshot(),
        source: "live" as const,
        availability: "degraded" as const,
        sourceDetail: "Live data is degraded; courier location is stale",
      }),
    };
    render(
      <App dataSource={degradedSource} healthProbe={vi.fn().mockResolvedValue(healthyServices)} />,
    );
    await user.click(screen.getByRole("link", { name: /Customer/ }));

    expect(screen.getByRole("button", { name: "Create order" })).toBeDisabled();
    expect(
      screen.getByText("A verified customer identity is required for commands."),
    ).toBeInTheDocument();
  });

  it("keeps the authenticated degraded state explicit and write disabled", () => {
    window.history.replaceState({}, "", "/customer");
    const degradedSnapshot = {
      ...demoDataSource.getSnapshot(),
      source: "live" as const,
      identityScope: `${customerSession.tenantId}:${customerSession.subject}:customer`,
      availability: "degraded" as const,
      sourceDetail: "Live data is degraded; courier location is stale",
    };
    render(
      <BrowserRouter>
        <AppRoutes
          snapshot={degradedSnapshot}
          realtime={{
            status: "degraded",
            cursor: "0",
            detail: "stream unavailable",
            appliedEvents: 0,
            staleReason: "stream unavailable",
            recentEvents: [],
          }}
          health={healthyServices}
          session={customerSession}
          allowedRoles={customerSession.roles}
        />
      </BrowserRouter>,
    );

    expect(screen.getByRole("button", { name: "Create order" })).toBeDisabled();
    expect(
      screen.getByText("Live data is degraded; commands are temporarily unavailable."),
    ).toBeInTheDocument();
  });
});
