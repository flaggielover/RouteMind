import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

const roles = [
  ["operations", "Keep the city moving."],
  ["strategy", "Decisions you can inspect."],
  ["customer", "Your delivery, clearly explained."],
  ["merchant", "Prep with the handoff in view."],
  ["courier", "A focused shift, one next action."],
] as const;

test.describe("role-aware web smoke", () => {
  test("shows the full lifecycle on the default operations route", async ({ page }) => {
    await page.goto("/operations");
    await expect(page.getByRole("heading", { name: "Keep the city moving." })).toBeVisible();
    await expect(page.getByRole("list", { name: "Lifecycle for RM-2041" })).toBeVisible();
    await expect(page.getByText("Order received")).toBeVisible();
    await expect(page.getByText("Delivered", { exact: true }).first()).toBeVisible();
    await expect(page.getByText("Demo snapshot")).toBeVisible();
  });

  for (const [path, heading] of roles) {
    test(`renders the ${path} role surface`, async ({ page }) => {
      await page.goto(`/${path}`);
      await expect(page.getByRole("heading", { name: heading })).toBeVisible();
      await expect(page.getByRole("navigation", { name: "RouteMind navigation" })).toBeVisible();
    });
  }

  test("keeps the mobile layout inside the viewport", async ({ page }) => {
    await page.goto("/operations");
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth - window.innerWidth,
    );
    expect(overflow).toBeLessThanOrEqual(1);
    await expect(page.getByRole("link", { name: /Operations/ })).toBeVisible();
    await page.screenshot({ path: "test-results/operations-mobile.png", fullPage: true });
  });

  test("passes the accessibility smoke gate for every role route", async ({ page }) => {
    for (const [path] of roles) {
      await page.goto(`/${path}`);
      const results = await new AxeBuilder({ page }).analyze();
      expect(results.violations, `${path} accessibility violations`).toEqual([]);
    }
  });
});
