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

  test("passes the accessibility smoke gate for every role route", async ({ page }) => {
    for (const [path] of roles) {
      await page.goto(`/${path}`);
      await selectDemo(page);
      const results = await new AxeBuilder({ page }).analyze();
      expect(results.violations, `${path} accessibility violations`).toEqual([]);
    }
  });
});
