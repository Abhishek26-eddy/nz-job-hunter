import { test, expect } from "@playwright/test";

test.describe("Europe Job Agent E2E", () => {
  test("dashboard loads without console errors", async ({ page }) => {
    const errors: string[] = [];
    page.on("pageerror", (err) => errors.push(err.message));
    page.on("console", (msg) => {
      if (msg.type() === "error") errors.push(msg.text());
    });

    await page.goto("/");
    await expect(page).toHaveTitle(/Europe Job Agent/);
    await expect(page.locator("h1")).toContainText("Dashboard");
    expect(errors).toEqual([]);
  });

  test("jobs page: search and filter", async ({ page }) => {
    await page.goto("/jobs");
    await expect(page.locator("h1")).toContainText("Jobs worth applying to");

    await expect(page.locator("text=Loading jobs...")).not.toBeVisible();

    const searchInput = page.locator('input[placeholder*="Search"]');
    await searchInput.fill("Engineer");
    await searchInput.press("Enter");

    await expect(page.locator("text=Engineer").first()).toBeVisible({ timeout: 10000 });
  });

  test("companies page loads", async ({ page }) => {
    await page.goto("/companies");
    await expect(page.locator("h1")).toContainText("Companies");
    await expect(page.locator("text=Loading").first()).not.toBeVisible();
    await expect(page.locator("text=ARM").first()).toBeVisible({ timeout: 10000 });
  });

  test("analytics page loads", async ({ page }) => {
    await page.goto("/analytics");
    await expect(page.locator("h1")).toContainText("Analytics");
    await expect(page.locator("text=Total Jobs").first()).toBeVisible();
  });

  test("settings page loads", async ({ page }) => {
    await page.goto("/settings");
    await expect(page.locator("h1")).toContainText("Settings");
    await expect(page.locator("text=AI Configuration")).toBeVisible();
  });

  test("job card shows crawled job data", async ({ page }) => {
    await page.goto("/jobs");
    await expect(page.locator("text=Loading jobs...")).not.toBeVisible();

    await page.waitForSelector("[data-testid='job-card']", { timeout: 10000 });

    const firstJob = page.locator("[data-testid='job-card']").first();
    await expect(firstJob).toContainText(/Engineer|DevOps|Manager|Developer/, { timeout: 5000 });
  });

  test("company card shows seeded company data", async ({ page }) => {
    await page.goto("/companies");
    await expect(page.locator("text=Loading").first()).not.toBeVisible();
    await page.waitForSelector("[data-testid='company-card']", { timeout: 10000 });

    const firstCompany = page.locator("[data-testid='company-card']").first();
    await expect(firstCompany).toContainText(/ABB|ARM|Booking\.com|Spotify|Wise|Monzo/, { timeout: 5000 });
  });

  test("resume upload from dashboard persists and triggers matching", async ({ page }) => {
    test.setTimeout(120000);
    const errors: string[] = [];
    page.on("pageerror", (err) => errors.push(err.message));
    page.on("console", (msg) => {
      if (msg.type() === "error") errors.push(msg.text());
    });

    await page.goto("/");
    await expect(page.locator("h1")).toContainText("Dashboard");

    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles("/tmp/resume.pdf");

    await expect(page.getByRole("button").filter({ hasText: /\.pdf$/ })).toBeVisible({ timeout: 30000 });
    await expect(page.locator("text=Uploading...")).not.toBeVisible();

    await page.waitForResponse(
      (resp) => resp.url().includes("/v1/ai/match") && resp.status() === 200,
      { timeout: 120000 }
    );

    await page.goto("/settings");
    await expect(page.getByRole("heading", { name: "Resume", exact: true })).toBeVisible();
    await expect(page.getByText(/\.pdf/)).toBeVisible({ timeout: 10000 });

    expect(errors).toEqual([]);
  });
});
