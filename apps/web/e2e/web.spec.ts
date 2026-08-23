import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

const roles = [
  ["operations", "Keep the city moving."],
  ["strategy", "Decisions you can inspect."],
  ["customer", "Your delivery, clearly explained."],
  ["merchant", "Prep with the handoff in view."],
  ["courier", "A focused shift, one next action."],
] as const;

test.describe("role-aware web smoke", () => {
  async function selectDemo(page: Page) {
    await page.getByRole("combobox", { name: "Data source mode" }).selectOption("demo");
  }

  async function openMobileNavigation(page: Page) {
    const toggle = page.getByRole("button", { name: "Open workspace navigation" });
    if (await toggle.isVisible()) {
      await toggle.click();
      await expect(page.getByRole("navigation", { name: "RouteMind navigation" })).toBeVisible();
    }
  }

  test("shows the full lifecycle on the default operations route", async ({ page }) => {
    await page.goto("/operations");
    await selectDemo(page);
    await expect(page.getByRole("heading", { name: "Keep the city moving." })).toBeVisible();
    await expect(page.getByRole("list", { name: "Lifecycle for RM-2041" })).toBeVisible();
    await expect(page.getByText("Order received")).toBeVisible();
    await expect(page.getByText("Delivered", { exact: true }).first()).toBeVisible();
    await expect(page.getByText("Demo snapshot")).toBeVisible();
  });

  test("controls a simulation source and surfaces replay events", async ({ page }) => {
    let simulatedTime = 0;
    const state = () => ({
      scenario_id: "control-default",
      seed: 7,
      strategy: "nearest",
      strategy_version: "1.0.0",
      status: simulatedTime >= 60 ? "completed" : "paused",
      speed: 1,
      simulated_time_seconds: simulatedTime,
      tick: Math.floor(simulatedTime / 60),
      generation: 0,
      event_count: simulatedTime >= 60 ? 1 : 0,
      last_command_id: simulatedTime >= 60 ? "simulation-step" : null,
      replay_digest: `digest-${simulatedTime}`,
    });
    await page.route("**/api/v1/twin/state", (route) => route.fulfill({ json: state() }));
    await page.route("**/api/v1/twin/control", async (route) => {
      const request = route.request().postDataJSON() as {
        action: string;
        command_id?: string;
        seconds?: number;
      };
      if (request.action === "step") simulatedTime += request.seconds ?? 60;
      await route.fulfill({
        json: {
          source: "simulation",
          command_id: request.command_id ?? "simulation-command",
          replayed: false,
          state: state(),
          events:
            simulatedTime >= 60
              ? [
                  {
                    event_id: "event-1",
                    event_type: "order.assigned",
                    simulated_time_seconds: 0,
                    command_id: "simulation-step",
                    details: [],
                  },
                ]
              : [],
          trace_id: "trace-simulation",
        },
      });
    });
    await page.goto("/operations");
    await page.getByRole("combobox", { name: "Data source mode" }).selectOption("simulation");
    await expect(page.locator(".source-status span:not(.source-dot)")).toHaveText("Simulation");
    await expect(page.getByRole("heading", { name: "Control the scenario clock." })).toBeVisible();
    await expect(page.getByText("seeded 1.0x")).toBeVisible();
    await page.getByRole("button", { name: /Step/ }).click();
    await expect(page.getByText("order.assigned")).toBeVisible();
    await expect(page.getByText(/completed · 60 simulated seconds/)).toBeVisible();
    await page.screenshot({ path: "test-results/simulation-control.png", fullPage: true });
  });

  test("loads and inspects a verified replay artifact", async ({ page }) => {
    await page.goto("/operations");
    await page.getByRole("combobox", { name: "Data source mode" }).selectOption("replay");
    await expect(page.getByRole("heading", { name: "Inspect the recorded run." })).toBeVisible();
    await expect(page.getByText(/Digest verified/)).toBeVisible();
    await expect(page.getByText("1 visible of 3 events")).toBeVisible();
    await page.getByRole("spinbutton", { name: "Replay step seconds" }).fill("30");
    await page.getByRole("button", { name: /Step/ }).click();
    await expect(page.getByText("2 visible of 3 events")).toBeVisible();
    await expect(page.getByText("order.created")).toBeVisible();
    await expect(page.getByText("dispatch.decision.recorded")).toBeVisible();

    await page.getByRole("button", { name: "order.created" }).click();
    await expect(page.locator(".replay-event-detail")).toContainText("order_id: order-1");
    await page.screenshot({ path: "test-results/replay-playback.png", fullPage: true });
  });

  test("runs a what-if comparison with recorded provenance", async ({ page }) => {
    await page.route("**/api/v1/experiments/what-if", async (route) => {
      expect(route.request().method()).toBe("POST");
      await route.fulfill({
        json: {
          source: "what-if",
          claim_label: "scenario comparison; not a causal production claim",
          recorded_run_id: "replay-control-default-v1",
          comparison_digest: "comparison-digest-123",
          scenario_id: "control-default",
          seed: 7,
          results: [
            {
              variant_id: "baseline",
              label: "Recorded baseline",
              strategy: "nearest",
              strategy_version: "1.0.0",
              request_count: 2,
              assigned_count: 2,
              assignment_rate: 1,
              simulated_end_tick: 1,
              simulated_duration_seconds: 60,
              risk_index: 0,
              replay_digest: "baseline-replay-digest",
              manifest_digest: "baseline-manifest-digest",
              output_digest: "baseline-output-digest",
              observed_runtime_millis: 1,
            },
            {
              variant_id: "traffic-stress",
              label: "Traffic stress",
              strategy: "weighted-greedy",
              strategy_version: "1.0.0",
              request_count: 3,
              assigned_count: 2,
              assignment_rate: 0.6667,
              simulated_end_tick: 3,
              simulated_duration_seconds: 180,
              risk_index: 12.5,
              replay_digest: "variant-replay-digest",
              manifest_digest: "variant-manifest-digest",
              output_digest: "variant-output-digest",
              observed_runtime_millis: 1,
            },
          ],
        },
      });
    });
    await page.goto("/strategy");
    await expect(page.getByRole("heading", { name: "Compare a scenario variant." })).toBeVisible();
    await page.getByRole("button", { name: "Run comparison" }).click();
    await expect(page.getByText("Comparison ready")).toBeVisible();
    await expect(page.getByRole("heading", { name: "Traffic stress" })).toBeVisible();
    await expect(page.getByText("Recorded run: replay-control-default-v1")).toBeVisible();
    await expect(page.getByText(/not a causal production claim/).last()).toBeVisible();
    await page.getByRole("button", { name: "Compare strategies" }).click();
    await expect(page.locator(".strategy-comparison-panel .what-if-status")).toHaveText(
      "Comparison ready",
    );
    await expect(page.getByText("Assignment rate")).toBeVisible();
    await expect(page.getByRole("group", { name: "Recorded strategy metrics" })).toBeVisible();
    await expect(page.getByRole("group", { name: "Assignment rate comparison" })).toBeVisible();
    await expect(page.getByText("Unavailable from recorded run").first()).toBeVisible();
    await page.screenshot({ path: "test-results/what-if-comparison.png", fullPage: true });
  });

  for (const [path, heading] of roles) {
    test(`renders the ${path} role surface`, async ({ page }) => {
      await page.goto(`/${path}`);
      await selectDemo(page);
      await openMobileNavigation(page);
      await expect(page.getByRole("heading", { name: heading })).toBeVisible();
      await expect(page.getByRole("navigation", { name: "RouteMind navigation" })).toBeVisible();
    });
  }

  test("keeps the mobile layout inside the viewport", async ({ page }) => {
    await page.goto("/operations");
    await selectDemo(page);
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth - window.innerWidth,
    );
    expect(overflow).toBeLessThanOrEqual(1);
    await openMobileNavigation(page);
    await expect(page.getByRole("link", { name: /Operations/ })).toBeVisible();
    await page.screenshot({ path: "test-results/operations-mobile.png", fullPage: true });
  });

  test("keeps map, decision details, and queue filters keyboard reachable", async ({ page }) => {
    await page.goto("/operations");
    await selectDemo(page);
    await page.getByRole("button", { name: "Select order RM-2042" }).focus();
    await expect(page.getByRole("button", { name: "Select order RM-2042" })).toBeFocused();
    await page.getByRole("button", { name: "Open decision details" }).click();
    await expect(page.getByRole("region", { name: "Decision details" })).toBeVisible();
    await page.getByRole("button", { name: "Filter board" }).click();
    await page.locator(".operations-filters select").nth(1).selectOption("OUT_FOR_DELIVERY");
    await expect(page.getByRole("button", { name: "Show all orders" })).toBeEnabled();
    await page.getByRole("button", { name: "Show all orders" }).click();
    await expect(page.getByRole("button", { name: "All orders visible" })).toBeDisabled();
  });

  test("opens the strategy registry as an inspectable local surface", async ({ page }) => {
    await page.goto("/strategy");
    await expect(page.getByRole("button", { name: "Open strategy registry" })).toBeVisible();
    await page.getByRole("button", { name: "Open strategy registry" }).click();
    await expect(page.getByRole("region", { name: "Strategy registry" })).toContainText(
      "weighted-greedy",
    );
  });

  test("keeps role actions reachable through the mobile navigation drawer", async ({ page }) => {
    if (test.info().project.name !== "mobile") test.skip();
    await page.goto("/customer");
    await selectDemo(page);
    await openMobileNavigation(page);
    await page.getByRole("link", { name: /Merchant/ }).click();
    await expect(page.getByRole("button", { name: "Mark ready" })).toBeVisible();
    await openMobileNavigation(page);
    await page.getByRole("link", { name: /Courier/ }).click();
    await expect(page.getByRole("button", { name: "Complete delivery" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Go online" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Send location" })).toBeVisible();
    await openMobileNavigation(page);
    await page.getByRole("link", { name: /Customer/ }).click();
    await expect(page.getByRole("button", { name: "Create order" })).toBeVisible();
  });

  test("keeps live loading and unavailable states explicit and accessible", async ({ page }) => {
    let releaseOperations!: () => void;
    const operationsPending = new Promise<void>((resolve) => {
      releaseOperations = resolve;
    });
    await page.route("**/api/v1/operations/snapshot", async (route) => {
      await operationsPending;
      await route.fulfill({ status: 503, contentType: "application/json", body: "{}" });
    });
    await page.goto("/operations");
    await expect(
      page.getByRole("status").filter({ hasText: "Loading operational projections" }),
    ).toBeVisible();
    releaseOperations();
    await expect(page.getByText("Live unavailable: HTTP 503")).toBeVisible();
    const results = await new AxeBuilder({ page }).analyze();
    expect(results.violations, "live unavailable accessibility violations").toEqual([]);
  });

  test("surfaces stale courier data and stale realtime cursors", async ({ page }) => {
    const operations = {
      source: "live",
      generatedAt: "2026-08-23T10:00:00.000Z",
      orders: [],
      parties: [],
      courierLocations: [
        {
          courierId: "courier-stale",
          latitude: 31.23,
          longitude: 121.47,
          observedAt: "2026-08-23T09:55:00.000Z",
        },
      ],
    };
    await page.route("**/api/v1/operations/snapshot", (route) =>
      route.fulfill({ json: operations }),
    );
    await page.route("**/api/v1/dispatch/snapshot", (route) =>
      route.fulfill({
        json: {
          source: "live",
          strategy: "weighted-greedy",
          strategy_version: "1.0.0",
          selected_courier: null,
          score: null,
          rationale: ["No fresh courier candidates"],
          latency_millis: 4,
          trace_id: "trace-stale",
        },
      }),
    );
    await page.addInitScript(() => {
      class StaleEventSource {
        static CONNECTING = 0;
        static OPEN = 1;
        static CLOSED = 2;
        readyState = StaleEventSource.CONNECTING;
        onopen: ((event: Event) => void) | null = null;
        onerror: ((event: Event) => void) | null = null;
        onmessage: ((event: MessageEvent<string>) => void) | null = null;
        listeners = new Map<string, Array<(event: MessageEvent<string>) => void>>();

        constructor() {
          window.setTimeout(() => {
            this.readyState = StaleEventSource.OPEN;
            this.onopen?.(new Event("open"));
            const stale = JSON.stringify({
              schemaVersion: "v1",
              cursor: "1",
              event: {
                specVersion: "1.0",
                eventId: "stale-event",
                eventType: "order.created",
                occurredAt: "2026-08-23T10:00:01.000Z",
                producer: "test",
                aggregateId: "order-stale",
                aggregateVersion: 1,
                correlationId: "correlation-stale",
                causationId: null,
                traceId: "trace-stale",
                payload: { orderId: "order-stale", status: "CREATED" },
              },
              replay: false,
              stale: true,
              staleReason: "Retention boundary reached",
            });
            this.listeners
              .get("order.created")
              ?.forEach((listener) => listener({ data: stale } as MessageEvent<string>));
          }, 30);
        }

        addEventListener(type: string, listener: (event: MessageEvent<string>) => void) {
          this.listeners.set(type, [...(this.listeners.get(type) ?? []), listener]);
        }

        close() {
          this.readyState = StaleEventSource.CLOSED;
        }
      }
      Object.defineProperty(window, "EventSource", { configurable: true, value: StaleEventSource });
    });
    await page.goto("/operations");
    await expect(page.getByText("Operational projections degraded")).toBeVisible();
    await expect(page.getByText(/courier location stale/)).toBeVisible();
    await expect(page.getByRole("status").filter({ hasText: "Stream stale" })).toBeVisible();
    await expect(page.getByText("Retention boundary reached")).toBeVisible();
    const results = await new AxeBuilder({ page }).analyze();
    expect(results.violations, "stale live accessibility violations").toEqual([]);
  });

  test("surfaces simulation control errors without losing the form state", async ({ page }) => {
    await page.route("**/api/v1/twin/state", (route) =>
      route.fulfill({
        json: {
          scenario_id: "control-default",
          seed: 7,
          strategy: "nearest",
          strategy_version: "1.0.0",
          status: "paused",
          speed: 1,
          simulated_time_seconds: 0,
          tick: 0,
          generation: 0,
          event_count: 0,
          last_command_id: null,
          replay_digest: "simulation-digest",
        },
      }),
    );
    await page.route("**/api/v1/twin/control", (route) =>
      route.fulfill({ status: 503, contentType: "application/json", body: "{}" }),
    );
    await page.goto("/operations");
    await page.getByRole("combobox", { name: "Data source mode" }).selectOption("simulation");
    await expect(page.getByRole("heading", { name: "Control the scenario clock." })).toBeVisible();
    await page.getByRole("spinbutton", { name: "Step seconds" }).fill("45");
    const step = page.getByRole("button", { name: "Step", exact: true });
    await expect(step).toBeEnabled();
    await step.click();
    await expect(page.locator(".simulation-panel").getByRole("alert")).toContainText("HTTP 503");
    await expect(page.getByRole("spinbutton", { name: "Step seconds" })).toHaveValue("45");
  });

  test("keeps mobile navigation focus contained and returns it to the toggle", async ({ page }) => {
    if (test.info().project.name !== "mobile") test.skip();
    await page.goto("/operations");
    await selectDemo(page);
    const toggle = page.getByRole("button", { name: "Open workspace navigation" });
    await toggle.click();
    const navigation = page.getByRole("navigation", { name: "RouteMind navigation" });
    await expect(navigation).toBeVisible();
    const links = navigation.getByRole("link");
    await expect(links.first()).toBeFocused();
    await page.keyboard.press("Shift+Tab");
    await expect(links.last()).toBeFocused();
    await page.keyboard.press("Tab");
    await expect(links.first()).toBeFocused();
    await page.keyboard.press("Escape");
    await expect(toggle).toBeFocused();
  });

  test("passes the accessibility smoke gate for every role route", async ({ page }) => {
    for (const [path] of roles) {
      await page.goto(`/${path}`);
      await selectDemo(page);
      const results = await new AxeBuilder({ page }).analyze();
      expect(results.violations, `${path} accessibility violations`).toEqual([]);
    }
  });
});
