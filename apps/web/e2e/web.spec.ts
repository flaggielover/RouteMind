import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

const roles = [
  ["operations", "Keep the city moving."],
  ["strategy", "Decisions you can inspect."],
  ["customer", "Your delivery, clearly explained."],
  ["merchant", "Prep with the handoff in view."],
  ["courier", "A focused shift, one next action."],
] as const;

const liveTenantId = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
const liveAccessToken = "e2e-verified-access-token";

async function installVerifiedLiveSession(page: Page) {
  await page.addInitScript((token) => {
    Object.defineProperty(window, "__ROUTEMIND_OIDC_ACCESS_TOKEN__", {
      configurable: true,
      value: async () => token,
    });
  }, liveAccessToken);
  await page.route("**/api/v1/session", async (route) => {
    expect(route.request().headers().authorization).toBe(`Bearer ${liveAccessToken}`);
    await route.fulfill({
      json: {
        schemaVersion: "v1",
        subject: "e2e-user",
        tenantId: liveTenantId,
        roles: ["operator", "analyst", "customer", "merchant", "courier"],
        expiresAt: "2099-01-01T00:00:00Z",
      },
    });
  });
}

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

  test("keeps the premium geographic world inspectable without trapping page scroll", async ({
    page,
  }) => {
    if (test.info().project.name === "mobile") test.skip();
    test.setTimeout(60_000);
    await page.goto("/operations");
    await selectDemo(page);
    const world = page.getByRole("complementary", {
      name: "Persistent Shanghai courier operations map",
    });
    await expect(world).toHaveAttribute("data-map-status", "ready", { timeout: 15_000 });
    await expect(world.locator("canvas")).toHaveCount(1);
    await expect(world.getByText("10", { exact: true })).toBeVisible();

    const bounds = await world.boundingBox();
    expect(bounds).not.toBeNull();
    await page.mouse.move(bounds!.x + bounds!.width * 0.24, bounds!.y + bounds!.height * 0.42);
    await page.mouse.move(bounds!.x + bounds!.width * 0.62, bounds!.y + bounds!.height * 0.48, {
      steps: 2,
    });
    await expect(world).toHaveAttribute("data-lens-active", "true");
    await expect(world).toHaveAttribute("data-lens-mode", "webgl-cc-lens");
    await expect(world).toHaveAttribute("data-lens-distortion", "1.50");
    await expect
      .poll(async () => Number(await world.getAttribute("data-lens-rgb-shift")))
      .toBeGreaterThan(0);
    await page.waitForTimeout(700);
    await expect
      .poll(async () => Number(await world.getAttribute("data-lens-rgb-shift")))
      .toBeLessThan(0.001);

    await world.locator(".geo-map-summary").hover();
    await expect(world).toHaveAttribute("data-lens-active", "false");
    await world.getByRole("button", { name: /Shanghai/ }).hover();
    await expect(world).toHaveAttribute("data-lens-active", "false");

    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.mouse.move(bounds!.x + bounds!.width * 0.2, bounds!.y + bounds!.height * 0.36);
    await page.mouse.move(bounds!.x + bounds!.width * 0.68, bounds!.y + bounds!.height * 0.54, {
      steps: 2,
    });
    await expect(world).toHaveAttribute("data-lens-active", "true");
    await expect(world).toHaveAttribute("data-lens-rgb-shift", "0.00000");
    await expect(world.locator("canvas")).toHaveCount(1);

    await page.getByRole("link", { name: "05 Live operations" }).click();
    await expect(world).toHaveAttribute("data-world-chapter", "live");
    await world.getByRole("button", { name: /Shenzhen/ }).click();
    await expect(
      page.getByRole("complementary", { name: "Persistent Shenzhen courier operations map" }),
    ).toHaveAttribute("data-world-chapter", "live");
    await expect(page.locator(".geo-selected-route")).toHaveCount(0);

    await page.getByRole("link", { name: "01 Network overview" }).click();
    await expect(page.locator(".persistent-geo-world")).toHaveAttribute(
      "data-world-chapter",
      "overview",
    );
    const before = await page.evaluate(() => window.scrollY);
    await page.mouse.move(bounds!.x + bounds!.width * 0.5, bounds!.y + bounds!.height * 0.55);
    await page.mouse.wheel(0, 700);
    await expect.poll(() => page.evaluate(() => window.scrollY)).toBeGreaterThan(before + 300);
  });

  test("exposes deterministic synthetic density and bounded district LOD for every city", async ({
    page,
  }) => {
    if (test.info().project.name === "mobile") test.skip();
    test.setTimeout(60_000);
    await page.goto("/operations");
    await selectDemo(page);
    const cityExpectations = [
      ["Shanghai", "120", "32"],
      ["Shenzhen", "90", "26"],
      ["Chengdu", "104", "28"],
    ] as const;
    for (const [city, population, routes] of cityExpectations) {
      const world = page.getByRole("complementary", {
        name: new RegExp(`Persistent ${city}`),
      });
      await expect(world).toHaveAttribute("data-map-status", "ready", { timeout: 15_000 });
      await expect(world).toHaveAttribute("data-courier-population", population);
      await expect(world).toHaveAttribute("data-emphasized-trajectories", routes);
      await expect(world).toHaveAttribute("data-map-lod", "city");
      if (city !== "Chengdu") {
        await world
          .getByRole("button", {
            name: new RegExp(cityExpectations[city === "Shanghai" ? 1 : 2]![0]),
          })
          .click();
      }
      await page.waitForTimeout(700);
    }
    const world = page.getByRole("complementary", {
      name: "Persistent Chengdu courier operations map",
    });
    await page.getByRole("link", { name: "02 Urban pressure" }).click();
    await expect(world).toHaveAttribute("data-map-lod", "district");
    await expect
      .poll(async () => Number(await world.getAttribute("data-visible-trajectories")))
      .toBeGreaterThanOrEqual(10);
    await expect
      .poll(async () => Number(await world.getAttribute("data-visible-trajectories")))
      .toBeLessThanOrEqual(16);
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
    await selectDemo(page);
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
    await selectDemo(page);
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
    await installVerifiedLiveSession(page);
    let releaseOperations!: () => void;
    const operationsPending = new Promise<void>((resolve) => {
      releaseOperations = resolve;
    });
    await page.route("**/api/v1/operations/snapshot", async (route) => {
      expect(route.request().headers().authorization).toBe(`Bearer ${liveAccessToken}`);
      expect(route.request().headers()["x-actor"]).toBe("operator");
      await operationsPending;
      await route.fulfill({ status: 503, contentType: "application/json", body: "{}" });
    });
    await page.goto("/operations");
    await expect(
      page.getByRole("status").filter({ hasText: "Loading operational projections" }),
    ).toBeVisible();
    releaseOperations();
    await expect(
      page.getByRole("status").filter({ hasText: "Live unavailable: HTTP 503" }),
    ).toBeVisible();
    const results = await new AxeBuilder({ page }).analyze();
    expect(results.violations, "live unavailable accessibility violations").toEqual([]);
  });

  test("surfaces stale courier data and stale realtime cursors", async ({ page }) => {
    await installVerifiedLiveSession(page);
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
    await page.route("**/api/v1/operations/snapshot", async (route) => {
      expect(route.request().headers().authorization).toBe(`Bearer ${liveAccessToken}`);
      expect(route.request().headers()["x-actor"]).toBe("operator");
      await route.fulfill({ json: operations });
    });
    await page.route("**/api/v1/events/stream**", async (route) => {
      expect(route.request().headers().authorization).toBe(`Bearer ${liveAccessToken}`);
      expect(route.request().url()).not.toContain(liveAccessToken);
      await route.fulfill({
        status: 200,
        contentType: "text/event-stream",
        body: `event: order.created\ndata: ${JSON.stringify({
          schemaVersion: "v1",
          cursor: "1",
          event: {
            specVersion: "1.0",
            eventId: "stale-event",
            eventType: "order.created",
            occurredAt: "2026-08-23T10:00:01.000Z",
            producer: "test",
            tenantId: liveTenantId,
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
        })}\n\n`,
      });
    });
    await page.goto("/operations");
    await expect(page.getByText("Operational projections degraded")).toBeVisible();
    await expect(page.getByText(/operational freshness degraded/).first()).toBeVisible();
    await expect(page.getByRole("status").filter({ hasText: "Stream stale" })).toBeVisible();
    await expect(page.getByText("Retention boundary reached", { exact: true })).toBeVisible();
    const results = await new AxeBuilder({ page }).analyze();
    expect(results.violations, "stale live accessibility violations").toEqual([]);
  });

  test("reconnects after a backend interruption without duplicating live events", async ({
    page,
  }) => {
    await installVerifiedLiveSession(page);
    await page.route("**/api/v1/operations/snapshot", (route) =>
      route.fulfill({
        json: {
          source: "live",
          generatedAt: "2026-08-30T12:00:00.000Z",
          orders: [],
          parties: [],
          courierLocations: [],
        },
      }),
    );

    const streamUrls: string[] = [];
    let releaseRecovery!: () => void;
    const backendRecovered = new Promise<void>((resolve) => {
      releaseRecovery = resolve;
    });
    const streamItem = (cursor: string, eventId: string, status: "CREATED" | "CONFIRMED") => ({
      schemaVersion: "v1",
      cursor,
      event: {
        specVersion: "1.0",
        eventId,
        eventType: status === "CREATED" ? "order.created" : "order.status.changed",
        occurredAt: `2026-08-30T12:00:0${cursor}.000Z`,
        producer: "business-api",
        tenantId: liveTenantId,
        aggregateId: "order-reconnect",
        aggregateVersion: Number(cursor),
        correlationId: "correlation-reconnect",
        causationId: null,
        traceId: "0123456789abcdef0123456789abcdef",
        payload: { orderId: "order-reconnect", status },
      },
      replay: false,
      stale: false,
      staleReason: null,
    });
    const created = streamItem("1", "event-created", "CREATED");
    const confirmed = streamItem("2", "event-confirmed", "CONFIRMED");

    await page.route("**/api/v1/events/stream**", async (route) => {
      streamUrls.push(route.request().url());
      if (streamUrls.length === 1) {
        await route.fulfill({
          status: 200,
          contentType: "text/event-stream",
          body: `event: order.created\ndata: ${JSON.stringify(created)}\n\n`,
        });
        return;
      }
      await backendRecovered;
      await route.fulfill({
        status: 200,
        contentType: "text/event-stream",
        body: `event: order.created\ndata: ${JSON.stringify(created)}\n\nevent: order.status.changed\ndata: ${JSON.stringify(confirmed)}\n\n`,
      });
    });

    await page.goto("/operations");
    await expect(page.getByText("Cursor 1", { exact: true })).toBeVisible();
    await expect.poll(() => streamUrls.length).toBeGreaterThanOrEqual(2);
    expect(streamUrls[0]).toContain("after=0");
    expect(streamUrls[1]).toContain("after=1");
    await expect(page.getByRole("status").filter({ hasText: "Stream reconnecting" })).toBeVisible();
    await expect(page.locator(".source-status span:not(.source-dot)")).toHaveText("Live ready");

    releaseRecovery();
    await expect(page.getByText("Cursor 2", { exact: true })).toBeVisible();
    await expect.poll(() => streamUrls.length).toBeGreaterThanOrEqual(3);
    expect(streamUrls[2]).toContain("after=2");
    await expect(page.getByRole("status").filter({ hasText: "Stream reconnecting" })).toBeVisible();
    await expect(
      page.getByRole("list", { name: "Verified activity events" }).getByRole("listitem"),
    ).toHaveCount(2);
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
