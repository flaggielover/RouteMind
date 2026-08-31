import path from "node:path";
import { expect, test, type Page } from "@playwright/test";

const evidenceDir = path.resolve(process.cwd(), "../../evidence/gates/RM-250");

async function captureChapter(page: Page, selector: string, name: string) {
  await page.evaluate((target) => {
    document.querySelector(target)?.scrollIntoView({ block: "start", behavior: "auto" });
  }, selector);
  await page.waitForTimeout(220);
  await page.screenshot({ path: path.join(evidenceDir, name), animations: "disabled" });
}

test.describe("Operations bilingual composition", () => {
  test("switches locale without reload and persists the selection", async ({ page }, testInfo) => {
    test.skip(testInfo.project.name === "mobile", "Locale controls collapse into the mobile menu.");
    await page.goto("/operations");
    await page.evaluate(() => window.localStorage.removeItem("routemind.locale"));
    await page.reload();
    await page.locator(".source-selector select").selectOption("demo");
    await expect(page.getByRole("heading", { name: "Keep the city moving." })).toBeVisible();
    await expect(page.locator(".persistent-geo-world")).toHaveAttribute(
      "data-map-status",
      "ready",
      {
        timeout: 20_000,
      },
    );
    await page.screenshot({
      path: path.join(evidenceDir, "operations-en-overview.png"),
      animations: "disabled",
    });
    await captureChapter(page, ".chapter-pressure", "operations-en-pressure.png");
    await captureChapter(page, ".chapter-live", "operations-en-live.png");
    await captureChapter(page, ".chapter-research", "operations-en-research.png");

    await page.getByRole("button", { name: "切换到中文" }).click();
    await page.locator(".source-selector select").selectOption("demo");
    await expect(page.getByRole("heading", { name: "让城市持续运转。" })).toBeVisible();
    await page.evaluate(() => window.scrollTo({ top: 0, behavior: "auto" }));
    await page.waitForTimeout(220);
    await page.screenshot({
      path: path.join(evidenceDir, "operations-zh-overview.png"),
      animations: "disabled",
    });
    await expect(page.getByRole("button", { name: "切换到英文" })).toHaveAttribute(
      "aria-pressed",
      "false",
    );
    await expect(page.locator(".persistent-geo-world")).toHaveAttribute(
      "data-courier-population",
      "120",
    );

    await page.reload();
    await page.locator(".source-selector select").selectOption("demo");
    await expect(page.getByRole("heading", { name: "让城市持续运转。" })).toBeVisible();
    await page.getByRole("button", { name: "切换到英文" }).click();
    await expect(page.getByRole("heading", { name: "Keep the city moving." })).toBeVisible();
  });

  test("keeps each chapter composition distinct with motion disabled", async ({
    page,
  }, testInfo) => {
    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.goto("/operations");
    await page.getByRole("combobox", { name: "Data source mode" }).selectOption("demo");
    const chapters = page.locator("[data-chapter]");
    await expect(chapters).toHaveCount(7);
    await expect(page.locator(".persistent-geo-world")).toHaveCount(1);
    await expect(page.locator(".operations-motion-root")).toHaveAttribute(
      "data-motion-reduced",
      "true",
    );
    await expect(page.locator(".chapter-overview")).toHaveCSS(
      "display",
      testInfo.project.name === "mobile" ? "block" : "grid",
    );
    await expect(page.locator(".chapter-live")).toHaveCSS("display", "block");
    await expect(page.locator(".chapter-replay")).toHaveCSS(
      "display",
      testInfo.project.name === "mobile" ? "block" : "grid",
    );

    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - innerWidth);
    expect(overflow).toBeLessThanOrEqual(1);
  });
});
