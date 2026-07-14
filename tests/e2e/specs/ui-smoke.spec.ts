import { expect, test, type Page } from "@playwright/test";

const teacherEmail = process.env.E2E_TEACHER_EMAIL ?? "teacher@wfjosephlee.edu.hk";
const studentEmail = process.env.E2E_STUDENT_EMAIL ?? "student@wfjosephlee.edu.hk";
const adminEmail = process.env.E2E_ADMIN_EMAIL ?? "admin@wfjosephlee.edu.hk";
const password = process.env.E2E_PASSWORD ?? "Password123!";

async function login(page: Page, email: string) {
  await page.goto("/");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
}

async function expectNoHorizontalOverflow(page: Page) {
  const widths = await page.evaluate(() => ({
    clientWidth: document.documentElement.clientWidth,
    scrollWidth: document.documentElement.scrollWidth,
  }));
  expect(widths.scrollWidth).toBeLessThanOrEqual(widths.clientWidth + 2);
}

test("teacher desktop shell exposes productized navigation and report controls", async ({ page }) => {
  await login(page, teacherEmail);
  await expect(page).toHaveURL(/\/teacher$/);
  await expect(page.getByRole("heading", { name: "Today" })).toBeVisible();
  await expect(page.locator(".sidebar")).toBeVisible();
  await expect(page.getByRole("link", { name: "Prepare & assign" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Review writing" })).toBeVisible();
  await page.getByRole("link", { name: "Class insights", exact: true }).click();
  await expect(page).toHaveURL(/\/teacher\/reports$/);
  await expect(page.getByRole("heading", { name: "Class insights" })).toBeVisible();
  await expect(page.getByTestId("report-generate")).toBeVisible();
  await expectNoHorizontalOverflow(page);
});

test("student mobile shell and personal-practice builder avoid horizontal overflow", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await login(page, studentEmail);
  await expect(page).toHaveURL(/\/student\/writing$/);
  await expect(page.getByRole("heading", { name: "Your next story starts here." })).toBeVisible();
  await expect(page.getByRole("navigation", { name: "Page navigation" })).toBeVisible();
  await expectNoHorizontalOverflow(page);
  await page.getByRole("link", { name: "My Practice" }).click();
  await expect(page).toHaveURL(/\/student\/practice$/);
  await expect(page.getByRole("heading", { name: "Choose one thing to practise today." })).toBeVisible();
  await expect(page.getByRole("button", { name: "Make my practice" })).toBeVisible();
  await expectNoHorizontalOverflow(page);
});

test("admin mobile shell keeps import and account controls reachable", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await login(page, adminEmail);
  await expect(page).toHaveURL(/\/admin$/);
  await expect(page.getByRole("heading", { name: "School overview" })).toBeVisible();
  await page.getByRole("link", { name: "People & classes", exact: true }).click();
  await expect(page).toHaveURL(/\/admin\/classes$/);
  await expect(page.getByRole("heading", { name: "People & classes" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Import users" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Class roster" })).toBeVisible();
  await expectNoHorizontalOverflow(page);
});
