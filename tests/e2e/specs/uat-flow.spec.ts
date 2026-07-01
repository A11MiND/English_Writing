import { mkdir } from "node:fs/promises";
import path from "node:path";

import { expect, test, type APIResponse, type Page } from "@playwright/test";

const teacherEmail = process.env.E2E_TEACHER_EMAIL ?? "teacher@wfjosephlee.edu.hk";
const studentEmail = process.env.E2E_STUDENT_EMAIL ?? "student@wfjosephlee.edu.hk";
const adminEmail = process.env.E2E_ADMIN_EMAIL ?? "admin@wfjosephlee.edu.hk";
const password = process.env.E2E_PASSWORD ?? "Password123!";
const evidenceDir = process.env.E2E_EVIDENCE_DIR;
const apiBaseUrl = (process.env.E2E_API_BASE_URL ?? "http://localhost:8000").replace(/\/$/, "");

let practiceTitle = "";
let examTitle = "";
let practiceFeedbackHref = "";

type ApiEnvelope<T> =
  | { success: true; data: T; request_id: string }
  | { success: false; error_code: string; message: string; request_id: string };

type Rubric = { id: string; title: string };
type SchoolClass = { id: string; name: string };
type WritingTask = { id: string; title: string };

test.describe.configure({ mode: "serial" });

async function login(page: Page, email: string) {
  await page.goto("/");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
}

async function logout(page: Page) {
  await page.getByRole("button", { name: "Logout" }).click();
  await expect(page.getByRole("button", { name: "Sign in" })).toBeVisible();
}

async function expectNoBrowserStoredToken(page: Page) {
  const storageSnapshot = await page.evaluate(() => ({
    localStorage: Object.keys(window.localStorage),
    sessionStorage: Object.keys(window.sessionStorage),
  }));
  expect(storageSnapshot.localStorage).toEqual([]);
  expect(storageSnapshot.sessionStorage).toEqual([]);
}

async function showAllStudentTasksIfAvailable(page: Page) {
  await expect(page.getByRole("heading", { name: "Student home" })).toBeVisible();
  const showAll = page.getByTestId("student-show-all-tasks");
  if ((await showAll.count()) > 0) {
    await showAll.first().click();
  }
}

async function parseApi<T>(response: APIResponse): Promise<T> {
  const body = (await response.json()) as ApiEnvelope<T>;
  expect(response.ok(), body.success ? undefined : body.message).toBeTruthy();
  expect(body.success, body.success ? undefined : body.message).toBeTruthy();
  return (body as { success: true; data: T }).data;
}

async function apiGet<T>(page: Page, url: string): Promise<T> {
  return parseApi<T>(await page.request.get(`${apiBaseUrl}${url}`));
}

async function apiPost<T>(page: Page, url: string, data?: unknown): Promise<T> {
  return parseApi<T>(
    await page.request.post(`${apiBaseUrl}${url}`, {
      data,
      headers: data ? { "content-type": "application/json" } : undefined,
    }),
  );
}

test("admin imports a CSV student and sees row-level result", async ({ page }) => {
  await login(page, adminEmail);
  await expect(page).toHaveURL(/\/admin$/);
  await expectNoBrowserStoredToken(page);
  await expect(page.getByRole("heading", { name: "Admin management" })).toBeVisible();
  await expect(page.getByText("AI provider")).toBeVisible();

  const suffix = Date.now();
  await page.getByTestId("admin-import-textarea").fill(
    [
      "email,display_name,student_number,level,class_name",
      `uat.student.${suffix}@wfjosephlee.edu.hk,UAT Student ${suffix},UAT${suffix},P5,P5A`,
    ].join("\n"),
  );
  await page.getByTestId("admin-import-submit").click();
  await expect(page.getByTestId("admin-notice")).toContainText("1 successful, 0 rejected");
  await expect(page.getByTestId("admin-import-result")).toContainText(`uat.student.${suffix}@wfjosephlee.edu.hk`);
  await logout(page);
});

test("teacher creates unique Practice and Exam tasks and assigns them to P5A", async ({ page }) => {
  await login(page, teacherEmail);
  await expect(page).toHaveURL(/\/teacher$/);
  await expectNoBrowserStoredToken(page);
  await expect(page.getByRole("heading", { name: "Teacher dashboard" })).toBeVisible();

  const [{ rubrics }, { classes }] = await Promise.all([
    apiGet<{ rubrics: Rubric[] }>(page, "/api/teacher/rubrics"),
    apiGet<{ classes: SchoolClass[] }>(page, "/api/teacher/classes"),
  ]);
  const rubric = rubrics[0];
  const targetClass = classes.find((row) => row.name === "P5A") ?? classes[0];
  expect(rubric?.id).toBeTruthy();
  expect(targetClass?.id).toBeTruthy();

  const suffix = Date.now();
  practiceTitle = `UAT Practice ${suffix}`;
  examTitle = `UAT Exam ${suffix}`;

  const createTask = async (title: string, mode: "PRACTICE" | "EXAM") => {
    const { task } = await apiPost<{ task: WritingTask }>(page, "/api/teacher/tasks", {
      title,
      level: "P5",
      instruction: `Write a complete school-based ${mode.toLowerCase()} composition for UAT evidence.`,
      genre: "Narrative",
      mode,
      word_minimum: 80,
      word_maximum: 180,
      ...(mode === "EXAM" ? { exam_duration_minutes: 1 } : {}),
      rubric_id: rubric.id,
      status: "PUBLISHED",
    });
    await apiPost(page, `/api/teacher/tasks/${task.id}/assignments`, { class_id: targetClass.id });
    return task;
  };

  await createTask(practiceTitle, "PRACTICE");
  await createTask(examTitle, "EXAM");

  await page.reload();
  await page.getByTestId("teacher-workbench-tasks").click();
  await expect(page.getByTestId("teacher-active-task").filter({ hasText: practiceTitle }).first()).toBeVisible();
  await expect(page.getByTestId("teacher-active-task").filter({ hasText: examTitle }).first()).toBeVisible();
  await logout(page);
});

test("student completes Practice Mode with grammar suggestion and locked submission", async ({ page }) => {
  test.setTimeout(90_000);

  await login(page, studentEmail);
  await expect(page).toHaveURL(/\/student$/);
  await expect(page.getByRole("heading", { name: "Student home" })).toBeVisible();
  await showAllStudentTasksIfAvailable(page);

  const taskCard = page.getByTestId("student-task-practice").filter({ hasText: practiceTitle }).first();
  await expect(taskCard).toBeVisible();
  await taskCard.getByTestId("open-practice-task").click();
  await expect(page.getByTestId("writing-editor-page")).toBeVisible();

  const editor = page.locator('[data-testid="editor-content"] .ProseMirror');
  await editor.fill("I has a apple. Yesterday I go to the library and learn many thing.");
  await page.getByTestId("full-check-button").click();
  await expect(page.getByTestId("suggestion-card").first()).toBeVisible({ timeout: 30_000 });
  await page.getByTestId("accept-suggestion").first().click();

  await page.getByTestId("submit-writing").click();
  await expect(page.getByText("Submitted and locked")).toBeVisible();
  const feedbackLink = page.getByTestId("view-feedback");
  await expect(feedbackLink).toBeVisible();
  practiceFeedbackHref = (await feedbackLink.getAttribute("href")) ?? "";
  expect(practiceFeedbackHref).toContain("/student/submissions/");
  await logout(page);
});

test("student completes Exam Mode, paste is blocked and timer auto-submits", async ({ page }) => {
  test.setTimeout(90_000);

  await login(page, studentEmail);
  await expect(page).toHaveURL(/\/student$/);
  await expect(page.getByRole("heading", { name: "Student home" })).toBeVisible();
  await showAllStudentTasksIfAvailable(page);

  const taskCard = page.getByTestId("student-task-exam").filter({ hasText: examTitle }).first();
  await expect(taskCard).toBeVisible();
  await taskCard.getByTestId("open-exam-task").click();
  await expect(page.getByTestId("exam-mode-notice")).toBeVisible();
  await expect(page.getByTestId("full-check-button")).toHaveCount(0);

  const editor = page.locator('[data-testid="editor-content"] .ProseMirror');
  await editor.fill("This is my exam writing. I will explain how my classmate helped me during a school activity.");
  const pastePrevented = await editor.evaluate((node) => {
    const data = new DataTransfer();
    data.setData("text/plain", "PASTED TEXT SHOULD BE BLOCKED");
    const event = new ClipboardEvent("paste", { bubbles: true, cancelable: true, clipboardData: data });
    return !node.dispatchEvent(event);
  });
  expect(pastePrevented).toBeTruthy();
  await expect(editor).not.toContainText("PASTED TEXT SHOULD BE BLOCKED");

  await expect(page.getByTestId("exam-timer")).toContainText(/^(00|01):[0-5][0-9]$/);
  await expect(page.getByText("Submitted and locked")).toBeVisible({ timeout: 70_000 });
  await logout(page);
});

test("teacher runs real AI marking, reviews and releases feedback", async ({ page }) => {
  test.setTimeout(180_000);

  await login(page, teacherEmail);
  await expect(page).toHaveURL(/\/teacher$/);
  await page.getByTestId("teacher-workbench-marking").click();

  const markingItem = page.getByTestId("marking-item").filter({ hasText: practiceTitle }).first();
  await expect(markingItem).toBeVisible({ timeout: 20_000 });
  await markingItem.getByTestId("run-ai-marking").click();
  await expect(page.getByTestId("teacher-notice")).toContainText("AI_MARKED", { timeout: 120_000 });

  const reviewedItem = page.getByTestId("marking-item").filter({ hasText: practiceTitle }).first();
  await reviewedItem.getByTestId("review-content").fill("4");
  await reviewedItem.getByTestId("review-language").fill("4");
  await reviewedItem.getByTestId("review-organisation").fill("4");
  await reviewedItem.getByTestId("review-notes").fill("Teacher reviewed and released through UAT E2E.");
  await reviewedItem.getByTestId("save-review").click();
  await expect(page.getByTestId("teacher-notice")).toContainText("Teacher review saved");

  await expect(reviewedItem.getByTestId("release-feedback")).toBeEnabled();
  await reviewedItem.getByTestId("release-feedback").click();
  await expect(page.getByTestId("teacher-notice")).toContainText("Feedback released");
  await logout(page);
});

test("student views released feedback and completes a post-writing exercise", async ({ page }) => {
  await login(page, studentEmail);
  await expect(page).toHaveURL(/\/student$/);
  await page.goto(practiceFeedbackHref);
  await expect(page.getByTestId("released-feedback")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Feedback" })).toBeVisible();

  const exercise = page.getByTestId("exercise-card").first();
  await expect(exercise).toBeVisible();
  await exercise.getByTestId("exercise-response").fill("I revised the sentence and explained the grammar correction.");
  await exercise.getByTestId("complete-exercise").click();
  await expect(page.getByText("Exercise saved.")).toBeVisible();
  await logout(page);
});

test("teacher previews class report and exports CSV and PDF evidence", async ({ page }) => {
  test.setTimeout(90_000);

  await login(page, teacherEmail);
  await expect(page).toHaveURL(/\/teacher$/);
  await page.getByTestId("teacher-workbench-reports").click();

  await page.getByTestId("report-generate").click();
  const reportResult = page.getByTestId("report-result");
  await expect(reportResult).toBeVisible({ timeout: 30_000 });
  await expect(reportResult.getByText("Rubric breakdown")).toBeVisible();
  await expect(reportResult.getByText("Common weaknesses")).toBeVisible();

  if (evidenceDir) {
    await mkdir(evidenceDir, { recursive: true });
  }

  const [csvDownload] = await Promise.all([
    page.waitForEvent("download"),
    page.getByTestId("report-export-csv").click(),
  ]);
  if (evidenceDir) {
    await csvDownload.saveAs(path.join(evidenceDir, csvDownload.suggestedFilename()));
  }

  const [pdfDownload] = await Promise.all([
    page.waitForEvent("download"),
    page.getByTestId("report-export-pdf").click(),
  ]);
  if (evidenceDir) {
    await pdfDownload.saveAs(path.join(evidenceDir, pdfDownload.suggestedFilename()));
  }

  await expect(page.getByTestId("teacher-notice")).toContainText("PDF export downloaded");
  await logout(page);
});
