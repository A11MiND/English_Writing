import { expect, test, type Page, type Route } from "@playwright/test";

const taskId = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
const classId = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb";

function success(data: unknown) {
  return { success: true, data, request_id: "e2e-demo-closure" };
}

async function fulfillJson(route: Route, data: unknown, status = 200) {
  await route.fulfill({ status, contentType: "application/json", body: JSON.stringify(data) });
}

async function mockSession(page: Page, role: "STUDENT" | "TEACHER") {
  await page.route("**/api/auth/session", (route) => fulfillJson(route, success({
    user: {
      id: role === "STUDENT" ? "student-1" : "teacher-1",
      school_id: "school-1",
      email: role === "STUDENT" ? "student@example.edu" : "teacher@example.edu",
      display_name: role === "STUDENT" ? "Student One" : "Teacher One",
      role,
      status: "ACTIVE",
    },
  })));
}

async function mockCapabilities(page: Page, plan: "FREE" | "SCHOOL_PRO" = "SCHOOL_PRO") {
  const pro = plan === "SCHOOL_PRO";
  await page.route("**/api/account/capabilities", (route) => fulfillJson(route, success({
    plan_code: plan,
    subscription_status: "ACTIVE",
    subscription_renews_at: null,
    features: {
      grammar_check: true,
      ai_assist: true,
      read_aloud: pro,
      image_generation: pro,
      ai_marking: pro,
      reports: pro,
    },
  })));
}

function practiceTask(title = "A Helpful Surprise") {
  return {
    id: taskId,
    title,
    level: "P5",
    instruction: "Write about a surprising moment when somebody helped you.",
    genre: "Narrative",
    mode: "PRACTICE",
    word_minimum: 80,
    word_maximum: 150,
    due_at: null,
    exam_duration_minutes: null,
    rubric_id: "rubric-1",
    rubric_title: "P5 Writing Rubric",
    status: "PUBLISHED",
    assigned_classes: ["P5A"],
    image_url: null,
  };
}

test("three-level language support, inline apply and AI rewrite form one deterministic writing loop", async ({ page }) => {
  await mockSession(page, "STUDENT");
  await mockCapabilities(page);
  await page.route(`**/api/student/tasks/${taskId}/writing`, (route) => fulfillJson(route, success({
    task: practiceTask(),
    draft: null,
    submission: null,
    locked: false,
  })));
  await page.route(`**/api/student/tasks/${taskId}/draft`, async (route) => {
    const payload = route.request().postDataJSON();
    await fulfillJson(route, success({
      draft: {
        id: "draft-1",
        ...payload,
        version: 1,
        status: "ACTIVE",
        saved_at: "2026-07-14T08:00:00Z",
      },
    }));
  });
  await page.route("**/api/suggestions/check", async (route) => {
    const payload = route.request().postDataJSON() as { text: string; check_mode: string };
    const wordOffset = payload.text.indexOf("sorrey");
    const sentenceOffset = payload.text.indexOf("went");
    await fulfillJson(route, success({
      suggestions: [
        {
          id: "word-spelling",
          rule_id: "MORFOLOGIK_RULE_EN_US",
          category: "TYPOS",
          message: "Check the spelling of this word.",
          short_message: "Spelling mistake",
          offset: wordOffset,
          length: 6,
          replacements: ["Sorry"],
          severity: "ERROR",
          level: "WORD",
        },
        {
          id: "sentence-modal",
          rule_id: "MODAL_BASE_FORM",
          category: "GRAMMAR",
          message: "The modal verb ‘will’ needs the base form of the verb.",
          short_message: "Use the base verb after will",
          offset: sentenceOffset,
          length: 4,
          replacements: ["go"],
          severity: "WARNING",
          level: "SENTENCE",
        },
      ].filter((item) => item.offset >= 0),
      cached: false,
      service_status: "ok",
      check_mode: payload.check_mode,
    }));
  });
  await page.route("**/api/suggestions/paragraph", (route) => fulfillJson(route, success({
    suggestions: [{
      id: "paragraph-repetition",
      level: "PARAGRAPH",
      focus: "REPETITION",
      title: "Vary the sentence openings",
      message: "Several sentences begin with the same words.",
      evidence: "My dog is kind. My dog is friendly.",
      action: "Start one sentence with a time phrase or an action.",
    }],
    cached: false,
    service_status: "ok",
  })));
  let rewriteRequest: { text: string; goal: string } | null = null;
  await page.route("**/api/student/rewrite", async (route) => {
    rewriteRequest = route.request().postDataJSON() as { text: string; goal: string };
    await fulfillJson(route, success({ rewrite: {
      original: rewriteRequest.text,
      revised: "Sorry. Tomorrow, I will go to the hospital. My friendly dog waits beside me and quietly shares his food.",
      explanation: "The new details make the paragraph clearer and more descriptive.",
      goal: rewriteRequest.goal,
    } }));
  });

  await page.goto(`/student/tasks/${taskId}/practice`);
  const editor = page.getByRole("textbox", { name: "Practice writing editor" });
  await expect(editor).toBeVisible();
  await editor.fill(
    "sorrey. I will went to hospital tomorrow. My dog is kind. My dog is friendly. My dog likes food very much.",
  );
  await page.getByTestId("full-check-button").click();

  await expect(page.getByTestId("word-suggestion-card")).toContainText("Spelling mistake");
  await expect(page.getByTestId("sentence-suggestion-card")).toContainText("Use the base verb after will");
  await expect(page.getByTestId("paragraph-suggestion-card")).toContainText("Vary the sentence openings");

  await page.getByRole("button", { name: /Word suggestion: Spelling mistake/ }).click();
  await expect(page.getByTestId("grammar-suggestion-popover")).toContainText("Sorry");
  await page.getByTestId("inline-apply-suggestion").click();
  await expect(editor).toContainText("Sorry. I will went");

  await page.getByRole("button", { name: /Sentence suggestion: Use the base verb after will/ }).press("Enter");
  await page.getByTestId("inline-apply-suggestion").click();
  await expect(editor).toContainText("I will go to hospital tomorrow");

  await page.getByRole("button", { name: "✦ Polish my story" }).click();
  await page.getByRole("button", { name: /Suggest one change/ }).click();
  await expect(page.getByText("Pip's suggestion")).toBeVisible();
  expect(rewriteRequest?.goal).toBe("MORE_DESCRIPTIVE");
  expect(rewriteRequest?.text).toContain("I will go");
  await page.getByRole("button", { name: "Use this change" }).click();
  await expect(editor).toContainText("Tomorrow, I will go to the hospital");
});

test("personal practice generation appears in history and its AI result is readable", async ({ page }) => {
  await mockSession(page, "STUDENT");
  await mockCapabilities(page);
  const historyItem = {
    ...practiceTask("Rainy Day Helper"),
    personal_practice: true,
    practice_focus: "Stronger feelings",
    practice_genre: "Narrative",
    draft_saved_at: null,
    submission_id: "submission-1",
    submitted_at: "2026-07-13T08:00:00Z",
    locked: true,
    marking_result: {
      id: "marking-1",
      status: "AI_MARKED",
      content_score: 4,
      language_score: 4,
      organisation_score: 5,
      total_score: 13,
      content_feedback: "Your main event is easy to follow.",
      language_feedback: "Most sentences are clear.",
      organisation_feedback: "The events are in a clear order.",
      strengths: ["Clear ending"],
      weaknesses: ["Add one sensory detail"],
      sentence_level_comments: [],
      recommended_exercises: [],
      marked_at: "2026-07-13T08:01:00Z",
    },
  };
  await page.route("**/api/student/practice", (route) => fulfillJson(route, success({ items: [historyItem] })));
  await page.route("**/api/student/practice/generate", async (route) => {
    const payload = route.request().postDataJSON() as { focus: string; genre: string; duration_minutes: number };
    expect(payload).toEqual({ focus: "PAST_TENSE", genre: "LETTER", duration_minutes: 10 });
    await fulfillJson(route, success({ practice: {
      ...practiceTask("The Lost Lunchbox"),
      id: "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
      personal_practice: true,
      practice_focus: "Past tense",
      practice_genre: "Letter",
      word_minimum: 100,
      word_maximum: 140,
      duration_minutes: 10,
      structure: ["Say where you were", "Explain what happened", "End with what you learnt"],
    } }));
  });

  await page.goto("/student/practice");
  await expect(page.getByRole("heading", { name: "Choose one thing to practise today." })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Rainy Day Helper" })).toBeVisible();
  await page.getByRole("button", { name: /Past tense/ }).click();
  await page.getByRole("button", { name: "Letter" }).click();
  await page.getByRole("button", { name: "10 min" }).click();
  await page.getByRole("button", { name: "Make my practice" }).click();

  await expect(page.getByText("Your new challenge")).toBeVisible();
  await expect(page.getByRole("heading", { name: "The Lost Lunchbox" }).first()).toBeVisible();
  await expect(page.getByText("2 total")).toBeVisible();

  await page.route(`**/api/student/practice/${taskId}/result`, (route) => fulfillJson(route, success({
    task: {
      id: taskId,
      title: "Rainy Day Helper",
      instruction: historyItem.instruction,
      level: "P5",
      practice_focus: "Stronger feelings",
      rubric_total_score: 15,
      rubric_dimensions: [
        { name: "Content", min_score: 0, max_score: 5 },
        { name: "Language", min_score: 0, max_score: 5 },
        { name: "Organisation", min_score: 0, max_score: 5 },
      ],
    },
    submission: {
      id: "submission-1",
      content_text: "I saw my friend in the rain, so I shared my umbrella and walked home with her.",
      word_count: 17,
      submitted_at: "2026-07-13T08:00:00Z",
    },
    marking_result: {
      ...historyItem.marking_result,
      sentence_level_comments: [{
        sentence: "I shared my umbrella.",
        comment: "This action clearly shows kindness.",
        category: "CONTENT",
      }],
      recommended_exercises: [{
        title: "Add a sensory detail",
        exercise_type: "REWRITE",
        focus_area: "DESCRIPTION",
        prompt: "Describe the sound of the rain in one sentence.",
      }],
    },
  })));
  await page.goto(`/student/practice/${taskId}`);
  await expect(page.getByRole("heading", { name: "Rainy Day Helper" })).toBeVisible();
  await expect(page.getByText("13").first()).toBeVisible();
  await expect(page.getByText("Clear ending")).toBeVisible();
  await expect(page.getByText("This action clearly shows kindness.")).toBeVisible();
});

test("teacher creates a pupil from the current roster screen without a real identity call", async ({ page }) => {
  await mockSession(page, "TEACHER");
  await mockCapabilities(page);
  await page.route("**/api/teacher/classes", (route) => fulfillJson(route, success({ classes: [{
    id: classId,
    name: "P5A",
    level: "P5",
    academic_year: "2026-2027",
    status: "ACTIVE",
    teacher_count: 1,
    student_count: 0,
  }] })));
  await page.route("**/api/teacher/rubrics", (route) => fulfillJson(route, success({ rubrics: [] })));
  await page.route("**/api/teacher/tasks", (route) => fulfillJson(route, success({ tasks: [] })));
  await page.route("**/api/teacher/marking/submissions**", (route) => fulfillJson(route, success({ items: [] })));
  const roster: Array<Record<string, string>> = [];
  await page.route("**/api/teacher/students", async (route) => {
    if (route.request().method() === "GET") {
      await fulfillJson(route, success({ students: roster }));
      return;
    }
    const payload = route.request().postDataJSON() as Record<string, string>;
    expect(payload).toMatchObject({
      display_name: "Ada Chan",
      email: "ada.chan@example.edu",
      class_id: classId,
      student_number: "S2042",
    });
    const student = {
      id: "new-student-1",
      display_name: payload.display_name,
      email: payload.email,
      status: "ACTIVE",
      student_number: payload.student_number,
      level: "P5",
      class_id: classId,
      class_name: "P5A",
    };
    roster.push(student);
    await fulfillJson(route, success({ student }));
  });

  await page.goto("/teacher/pupils");
  await expect(page.getByRole("heading", { name: "Pupils" })).toBeVisible();
  await page.getByLabel("Pupil name").fill("Ada Chan");
  await page.getByLabel("School email").fill("ada.chan@example.edu");
  await page.getByLabel(/Student number/).fill("S2042");
  await page.getByLabel("Temporary password").fill("Temporary123!");
  await page.getByRole("button", { name: "Create pupil sign-in" }).click();

  await expect(page.getByText("Ada Chan can now sign in. Share the temporary password privately.")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Pupil roster" })).toBeVisible();
  await expect(page.getByText("Ada Chan", { exact: true })).toBeVisible();
  await expect(page.getByText("Can sign in")).toBeVisible();
});

test("free plan renders read-aloud as locked and never calls the speech provider", async ({ page }) => {
  await mockSession(page, "STUDENT");
  await mockCapabilities(page, "FREE");
  await page.route(`**/api/student/tasks/${taskId}/writing`, (route) => fulfillJson(route, success({
    task: practiceTask(),
    draft: null,
    submission: null,
    locked: false,
  })));
  let speechCalls = 0;
  await page.route("**/api/media/speech", async (route) => {
    speechCalls += 1;
    await fulfillJson(route, { success: false, error_code: "ACCESS_DENIED", message: "School Pro required", request_id: "blocked" }, 403);
  });

  await page.goto(`/student/tasks/${taskId}/practice`);
  await expect(page.getByText("Listen to the prompt · Pro")).toBeVisible();
  await expect(page.getByText("Listen to my writing · Pro")).toBeVisible();
  await expect(page.getByRole("button", { name: "Listen to the prompt" })).toHaveCount(0);
  expect(speechCalls).toBe(0);
});
