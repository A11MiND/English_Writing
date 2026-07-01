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

async function showAllStudentTasksIfAvailable(page: Page) {
  await expect(page.getByRole("heading", { name: "Student home" })).toBeVisible();
  const showAll = page.getByTestId("student-show-all-tasks");
  if ((await showAll.count()) > 0) {
    await showAll.first().click();
  }
}

test("teacher desktop shell exposes productized navigation and report controls", async ({ page }) => {
  await login(page, teacherEmail);
  await expect(page).toHaveURL(/\/teacher$/);
  await expect(page.locator(".portal-sidebar")).toBeVisible();
  await expect(page.getByRole("link", { name: /Reports/ })).toBeVisible();
  await expect(page.getByRole("link", { name: /Marking/ })).toBeVisible();
  await expect(page.getByTestId("teacher-workbench-overview")).toBeVisible();
  await expect(page.getByText("Things to do")).toBeVisible();
  await page.getByTestId("teacher-workbench-reports").click();
  await expect(page.getByTestId("report-generate")).toBeVisible();
  await expectNoHorizontalOverflow(page);
});

test("student mobile shell and practice editor avoid horizontal overflow", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await login(page, studentEmail);
  await expect(page).toHaveURL(/\/student$/);
  await expect(page.getByRole("heading", { name: "Student home" })).toBeVisible();
  await expect(page.locator(".mobile-section-nav")).toBeVisible();
  await expectNoHorizontalOverflow(page);
  await showAllStudentTasksIfAvailable(page);

  const practiceTask = page.getByTestId("student-task-practice").first();
  await expect(practiceTask).toBeVisible();
  await practiceTask.getByTestId("open-practice-task").click();
  await expect(page.getByTestId("writing-editor-page")).toBeVisible();
  await expect(page.getByTestId("full-check-button")).toBeVisible();
  await expect(page.getByTestId("exam-mode-notice")).toHaveCount(0);
  await expectNoHorizontalOverflow(page);
});

test("admin mobile shell keeps import and account controls reachable", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await login(page, adminEmail);
  await expect(page).toHaveURL(/\/admin$/);
  await expect(page.getByRole("heading", { name: "Admin management" })).toBeVisible();
  await expect(page.locator(".mobile-section-nav")).toBeVisible();
  await expect(page.getByTestId("admin-import-submit")).toBeVisible();
  await expect(page.getByText("Account management")).toBeVisible();
  await expectNoHorizontalOverflow(page);
});
