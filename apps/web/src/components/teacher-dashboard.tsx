"use client";

import type { FormEvent } from "react";
import type {
  ClassReportPayload,
  ReportExportAudit,
  Rubric,
  SchoolClass,
  TeacherMarkingSubmission,
  WritingTask,
} from "@english-ai-writing/shared";
import { useEffect, useState } from "react";

import { AppShell, type AppShellUser } from "@/components/app-shell";
import { currentUser, logout } from "@/lib/auth";
import {
  assignTask,
  createRubric,
  createTask,
  duplicateRubric,
  downloadClassReport,
  generateClassReport,
  getClassReport,
  listClassReportExports,
  listTeacherClasses,
  listTeacherMarkingSubmissions,
  listTeacherRubrics,
  listTeacherTasks,
  reviewMarking,
  releaseFeedback,
  runMarking,
  updateRubric,
  updateTask,
} from "@/lib/school-data";

type TeacherState =
  | { status: "loading" }
  | { status: "denied"; message: string }
  | {
      status: "ready";
      user: AppShellUser;
      classes: SchoolClass[];
      rubrics: Rubric[];
      tasks: WritingTask[];
      markingItems: TeacherMarkingSubmission[];
    };

type TaskForm = {
  title: string;
  level: string;
  instruction: string;
  genre: string;
  mode: "PRACTICE" | "EXAM";
  word_minimum: string;
  word_maximum: string;
  due_at: string;
  exam_duration_minutes: string;
  status: "DRAFT" | "PUBLISHED";
  rubric_id: string;
};

type TeacherWorkbench = "overview" | "tasks" | "rubrics" | "marking" | "reports";

const defaultDimensions = [
  {
    name: "Content",
    min_score: 0,
    max_score: 5,
    descriptor: "Ideas are relevant and developed for the writing task.",
    sort_order: 1,
  },
  {
    name: "Language",
    min_score: 0,
    max_score: 5,
    descriptor: "Vocabulary, grammar and sentence structures support clear expression.",
    sort_order: 2,
  },
  {
    name: "Organisation",
    min_score: 0,
    max_score: 5,
    descriptor: "Writing is logically sequenced with clear paragraphing.",
    sort_order: 3,
  },
];

function scorePercent(value: number | null | undefined, maxScore: number) {
  if (!Number.isFinite(value ?? Number.NaN) || maxScore <= 0) return "0%";
  return `${Math.max(0, Math.min(100, Math.round(((value ?? 0) / maxScore) * 100)))}%`;
}

export function TeacherDashboard() {
  const [state, setState] = useState<TeacherState>({ status: "loading" });
  const [activeWorkbench, setActiveWorkbench] = useState<TeacherWorkbench>("overview");
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [rubricForm, setRubricForm] = useState({
    title: "P5 Narrative Writing Rubric",
    level: "P5",
  });
  const [taskForm, setTaskForm] = useState<TaskForm>({
    title: "A Kind Act",
    level: "P5",
    instruction: "Write a complete story about a time when someone did something kind.",
    genre: "Narrative",
    mode: "PRACTICE",
    word_minimum: "120",
    word_maximum: "180",
    due_at: "",
    exam_duration_minutes: "30",
    status: "PUBLISHED",
    rubric_id: "",
  });
  const [assignmentForm, setAssignmentForm] = useState({ task_id: "", class_id: "" });
  const [reportClassId, setReportClassId] = useState("");
  const [classReport, setClassReport] = useState<ClassReportPayload | null>(null);
  const [reportBusy, setReportBusy] = useState(false);
  const [reportExports, setReportExports] = useState<ReportExportAudit[]>([]);
  const [lastExport, setLastExport] = useState<{ format: string; filename: string; bytes: number } | null>(null);
  const [reviewDrafts, setReviewDrafts] = useState<
    Record<string, { content: string; language: string; organisation: string; notes: string }>
  >({});

  async function refresh(user?: AppShellUser) {
    const [classes, rubrics, tasks, markingItems] = await Promise.all([
      listTeacherClasses(),
      listTeacherRubrics(),
      listTeacherTasks(),
      listTeacherMarkingSubmissions(),
    ]);
    setState((current) => {
      const shellUser = user ?? (current.status === "ready" ? current.user : null);
      if (!shellUser) return current;
      return { status: "ready", user: shellUser, classes, rubrics, tasks, markingItems };
    });
    setTaskForm((current) => ({ ...current, rubric_id: current.rubric_id || rubrics[0]?.id || "" }));
    setAssignmentForm((current) => ({
      task_id: current.task_id || tasks[0]?.id || "",
      class_id: current.class_id || classes[0]?.id || "",
    }));
    setReportClassId((current) => current || classes[0]?.id || "");
    setReviewDrafts((current) => {
      const next = { ...current };
      for (const item of markingItems) {
        const result = item.marking_result;
        if (result && !next[result.id]) {
          next[result.id] = {
            content: String(result.content_score ?? ""),
            language: String(result.language_score ?? ""),
            organisation: String(result.organisation_score ?? ""),
            notes: "",
          };
        }
      }
      return next;
    });
  }

  useEffect(() => {
    let active = true;
    async function load() {
      const user = await currentUser();
      if (!active) return;
      if (!user) {
        window.location.href = "/";
        return;
      }
      if (user.role !== "TEACHER") {
        setState({ status: "denied", message: "Your role cannot access teacher dashboard." });
        return;
      }
      await refresh({ display_name: user.display_name, email: user.email, role: user.role });
    }
    void load().catch((error) => {
      setState({
        status: "denied",
        message: error instanceof Error ? error.message : "Unable to load teacher dashboard.",
      });
    });
    return () => {
      active = false;
    };
  }, []);

  async function onLogout() {
    await logout();
    window.location.href = "/";
  }

  async function onCreateRubric(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setNotice("");
    setError("");
    try {
      const rubric = await createRubric({
        title: rubricForm.title,
        level: rubricForm.level,
        total_score: 15,
        status: "ACTIVE",
        dimensions: defaultDimensions,
      });
      setNotice(`Rubric created: ${rubric.title}`);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to create rubric.");
    }
  }

  async function onCreateTask(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setNotice("");
    setError("");
    try {
      const task = await createTask({
        title: taskForm.title,
        level: taskForm.level,
        instruction: taskForm.instruction,
        genre: taskForm.genre,
        mode: taskForm.mode,
        word_minimum: Number(taskForm.word_minimum),
        word_maximum: Number(taskForm.word_maximum),
        due_at: taskForm.due_at ? new Date(taskForm.due_at).toISOString() : undefined,
        exam_duration_minutes:
          taskForm.mode === "EXAM" ? Number(taskForm.exam_duration_minutes || "30") : undefined,
        rubric_id: taskForm.rubric_id,
        status: taskForm.status,
      });
      setNotice(`Task created: ${task.title}`);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to create task.");
    }
  }

  async function onAssignTask(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setNotice("");
    setError("");
    try {
      const assignment = await assignTask(assignmentForm.task_id, assignmentForm.class_id);
      setNotice(`Task assigned to ${assignment.class_name}.`);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to assign task.");
    }
  }

  async function onDuplicateRubric(rubric: Rubric) {
    setNotice("");
    setError("");
    try {
      const copy = await duplicateRubric(rubric.id, `${rubric.title} Copy`);
      setNotice(`Rubric duplicated as draft: ${copy.title}`);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to duplicate rubric.");
    }
  }

  async function onArchiveRubric(rubric: Rubric) {
    setNotice("");
    setError("");
    try {
      const archived = await updateRubric(rubric.id, { status: "ARCHIVED" });
      setNotice(`Rubric archived: ${archived.title}`);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to archive rubric.");
    }
  }

  async function onChangeTaskStatus(
    task: WritingTask,
    status: "DRAFT" | "PUBLISHED" | "CLOSED" | "ARCHIVED",
  ) {
    setNotice("");
    setError("");
    try {
      const updated = await updateTask(task.id, { status });
      setNotice(`Task status updated: ${updated.title} is ${updated.status}`);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to update task status.");
    }
  }

  async function onRunMarking(markingResultId: string) {
    setNotice("");
    setError("");
    try {
      const result = await runMarking(markingResultId);
      setNotice(`AI marking status: ${result.status}`);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to run AI marking.");
    }
  }

  async function onReviewMarking(markingResultId: string) {
    setNotice("");
    const draft = reviewDrafts[markingResultId];
    if (!draft) return;
    const content = Number(draft.content);
    const language = Number(draft.language);
    const organisation = Number(draft.organisation);
    setError("");
    if (
      [content, language, organisation].some(
        (score) => !Number.isFinite(score) || score < 0 || score > 5,
      )
    ) {
      setError("Review scores must be numbers from 0 to 5.");
      return;
    }
    try {
      const review = await reviewMarking(markingResultId, {
        content_score: content,
        language_score: language,
        organisation_score: organisation,
        total_score: content + language + organisation,
        review_notes: draft.notes,
        status: "REVIEWED",
      });
      setNotice(`Teacher review saved: total ${review.total_score ?? 0}`);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to save teacher review.");
    }
  }

  async function onReleaseFeedback(markingResultId: string) {
    setNotice("");
    setError("");
    try {
      const review = await releaseFeedback(markingResultId);
      setNotice(`Feedback released: ${review.feedback_released_at ?? "released"}`);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to release feedback.");
    }
  }

  async function onGenerateReport() {
    if (!reportClassId) return;
    setNotice("");
    setError("");
    setReportBusy(true);
    try {
      const report = await generateClassReport(reportClassId);
      setClassReport(report);
      setReportExports(await listClassReportExports(reportClassId));
      setNotice(`Class report generated: ${report.class_report.class_name}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to generate report.");
    } finally {
      setReportBusy(false);
    }
  }

  async function onPreviewReport() {
    if (!reportClassId) return;
    setNotice("");
    setError("");
    setReportBusy(true);
    try {
      setClassReport(await getClassReport(reportClassId));
      setReportExports(await listClassReportExports(reportClassId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to preview report.");
    } finally {
      setReportBusy(false);
    }
  }

  async function onDownloadReport(format: "csv" | "pdf") {
    if (!reportClassId) return;
    setNotice("");
    setError("");
    try {
      const downloaded = await downloadClassReport(reportClassId, format);
      setLastExport({ format, filename: downloaded.filename, bytes: downloaded.bytes });
      setReportExports(await listClassReportExports(reportClassId));
      setNotice(`${format.toUpperCase()} export downloaded: ${downloaded.filename}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : `${format.toUpperCase()} export failed.`);
    }
  }

  if (state.status === "loading") {
    return <main className="loading-state">Loading teacher dashboard...</main>;
  }

  if (state.status === "denied") {
    return (
      <main className="centered-state">
        <h1 className="text-4xl font-semibold">Access denied</h1>
        <p className="mt-4 text-ink/65">{state.message}</p>
      </main>
    );
  }

  const publishedTasks = state.tasks.filter((task) => task.status === "PUBLISHED").length;
  const examTasks = state.tasks.filter((task) => task.mode === "EXAM").length;
  const pendingMarking = state.markingItems.filter((item) => item.marking_result?.status !== "AI_MARKED").length;
  const currentTasks = state.tasks.filter((task) => task.status !== "ARCHIVED").slice(0, 5);
  const reportDistributionMax = classReport
    ? Math.max(1, ...Object.values(classReport.score_distribution))
    : 1;

  return (
    <AppShell title="Teacher dashboard" user={state.user} onLogout={() => void onLogout()}>
      {notice ? (
        <div className="notice-success" data-testid="teacher-notice">
          {notice}
        </div>
      ) : null}
      {error ? (
        <div className="notice-error" data-testid="teacher-error">
          {error}
        </div>
      ) : null}

      <section id="overview" className="section-anchor grid gap-4 md:grid-cols-4">
        <div className="metric-card">
          <p className="metric-label">Assigned classes</p>
          <p className="metric-value">{state.classes.length}</p>
          <p className="metric-hint">{state.classes.map((schoolClass) => schoolClass.name).join(", ") || "-"}</p>
        </div>
        <div className="metric-card">
          <p className="metric-label">Published writing</p>
          <p className="metric-value">{publishedTasks}</p>
          <p className="metric-hint">{examTasks} Exam Mode tasks</p>
        </div>
        <div className="metric-card">
          <p className="metric-label">Rubrics</p>
          <p className="metric-value">{state.rubrics.length}</p>
          <p className="metric-hint">Scoring criteria</p>
        </div>
        <div className="metric-card">
          <p className="metric-label">To mark</p>
          <p className="metric-value">{state.markingItems.length}</p>
          <p className="metric-hint">{pendingMarking} need attention</p>
        </div>
      </section>

      <section className="section-card">
        <div className="panel-header">
          <div>
            <h2 className="panel-title">What do you want to do now?</h2>
            <p className="panel-subtitle">Choose one job. Setup, marking and reports stay separate.</p>
          </div>
        </div>
        <div className="mt-4 grid gap-2 sm:grid-cols-2 xl:grid-cols-5">
          {([
            ["overview", "Today", "Next steps"],
            ["tasks", "Set writing task", "Create and publish"],
            ["marking", "Mark writing", "Review and release"],
            ["reports", "Class progress", "Report and export"],
            ["rubrics", "Rubrics", "Scoring criteria"],
          ] as const).map(([workbench, label, description]) => (
            <button
              key={workbench}
              type="button"
              onClick={() => setActiveWorkbench(workbench)}
              className={`rounded-md border px-4 py-3 text-left transition ${
                activeWorkbench === workbench
                  ? "border-ink bg-ink text-paper"
                  : "border-ink/10 bg-paper text-ink hover:border-moss/50"
              }`}
              data-testid={`teacher-workbench-${workbench}`}
            >
              <span className="block text-sm font-semibold">{label}</span>
              <span className={`mt-1 block text-xs ${activeWorkbench === workbench ? "text-paper/65" : "text-ink/55"}`}>
                {description}
              </span>
            </button>
          ))}
        </div>
      </section>

      {activeWorkbench === "overview" ? (
        <section className="grid gap-5 lg:grid-cols-[0.9fr_1.1fr]">
          <div className="section-card">
            <div className="panel-header">
              <div>
                <h2 className="panel-title">Things to do</h2>
                <p className="panel-subtitle">Start here instead of scanning every tool on the page.</p>
              </div>
            </div>
            <div className="mt-4 grid gap-3">
              <button type="button" onClick={() => setActiveWorkbench("marking")} className="muted-panel text-left">
                <p className="font-semibold text-ink">{pendingMarking} writings need marking</p>
                <p className="mt-1 text-sm text-ink/60">Check AI feedback, adjust scores, then release to students.</p>
              </button>
              <button type="button" onClick={() => setActiveWorkbench("reports")} className="muted-panel text-left">
                <p className="font-semibold text-ink">View class progress</p>
                <p className="mt-1 text-sm text-ink/60">See who finished and what the class should practise next.</p>
              </button>
              <button type="button" onClick={() => setActiveWorkbench("tasks")} className="muted-panel text-left">
                <p className="font-semibold text-ink">Set a writing task</p>
                <p className="mt-1 text-sm text-ink/60">Choose a class, choose the writing, then publish.</p>
              </button>
            </div>
          </div>
          <div className="section-card">
            <div className="panel-header">
              <div>
                <h2 className="panel-title">Current writing tasks</h2>
                <p className="panel-subtitle">A short operational list. Full management is in Tasks.</p>
              </div>
              <span className="status-pill-muted">{state.tasks.length} total</span>
            </div>
            <div className="mt-4 grid gap-3">
              {currentTasks.map((task) => (
                <div key={task.id} className="muted-panel">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <p className="font-semibold text-ink">{task.title}</p>
                    <span className={task.mode === "EXAM" ? "status-pill-warning" : "status-pill"}>{task.mode}</span>
                  </div>
                  <p className="mt-1 text-sm text-ink/65">
                    {task.level} · {task.status} · Assigned: {task.assigned_classes.join(", ") || "-"}
                  </p>
                </div>
              ))}
              {currentTasks.length === 0 ? <p className="empty-state">No active tasks.</p> : null}
            </div>
          </div>
        </section>
      ) : null}

      <section className={`grid gap-5 lg:grid-cols-3 ${activeWorkbench === "tasks" || activeWorkbench === "rubrics" ? "" : "hidden"}`}>
        <form id="rubrics" onSubmit={onCreateRubric} className={`section-anchor section-card ${activeWorkbench === "rubrics" ? "" : "hidden"}`}>
          <div className="panel-header">
            <div>
              <h2 className="panel-title">Rubric builder</h2>
              <p className="panel-subtitle">Create reusable P4 to P6 rubric dimensions for teacher review.</p>
            </div>
          </div>
          <input
            value={rubricForm.title}
            onChange={(event) => setRubricForm({ ...rubricForm, title: event.target.value })}
            className="mt-4 w-full form-control"
            placeholder="Rubric title"
          />
          <select
            value={rubricForm.level}
            onChange={(event) => setRubricForm({ ...rubricForm, level: event.target.value })}
            className="mt-3 w-full form-control"
          >
            <option>P4</option>
            <option>P5</option>
            <option>P6</option>
          </select>
          <div className="mt-4 grid gap-2 text-sm text-ink/65">
            {defaultDimensions.map((dimension) => (
              <div key={dimension.name} className="rounded-md bg-chalk px-3 py-2">
                {dimension.name}: 0-{dimension.max_score}
              </div>
            ))}
          </div>
          <button type="submit" className="mt-4 btn btn-primary btn-lg">
            Create rubric
          </button>
          <div className="mt-5 border-t border-ink/10 pt-4">
            <h3 className="text-sm font-semibold uppercase tracking-[0.14em] text-ink/55">Rubrics</h3>
            <div className="mt-3 grid gap-2">
              {state.rubrics.map((rubric) => (
                <div key={rubric.id} className="rounded-md border border-ink/10 bg-white px-3 py-3">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold text-ink">{rubric.title}</p>
                      <p className="mt-1 text-xs font-semibold text-moss">
                        {rubric.level} · {rubric.status} · {rubric.total_score} pts
                      </p>
                    </div>
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2">
                    <button
                      type="button"
                      onClick={() => void onDuplicateRubric(rubric)}
                      className="btn btn-secondary text-xs"
                    >
                      Duplicate
                    </button>
                    <button
                      type="button"
                      onClick={() => void onArchiveRubric(rubric)}
                      className="btn btn-secondary text-xs"
                    >
                      Archive
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </form>

        <form id="tasks" onSubmit={onCreateTask} className={`section-anchor section-card lg:col-span-2 ${activeWorkbench === "tasks" ? "" : "hidden"}`}>
          <div className="panel-header">
            <div>
              <h2 className="panel-title">Task builder</h2>
              <p className="panel-subtitle">Create draft or published Practice and Exam Mode writing tasks.</p>
            </div>
            <span className={taskForm.mode === "EXAM" ? "status-pill-warning" : "status-pill"}>
              {taskForm.mode === "EXAM" ? "Exam Mode" : "Practice Mode"}
            </span>
          </div>
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            <input
              value={taskForm.title}
              onChange={(event) => setTaskForm({ ...taskForm, title: event.target.value })}
              className="form-control"
              placeholder="Task title"
            />
            <select
              value={taskForm.rubric_id}
              onChange={(event) => setTaskForm({ ...taskForm, rubric_id: event.target.value })}
              className="form-control"
            >
              {state.rubrics.map((rubric) => (
                <option key={rubric.id} value={rubric.id}>{rubric.title}</option>
              ))}
            </select>
            <select
              value={taskForm.level}
              onChange={(event) => setTaskForm({ ...taskForm, level: event.target.value })}
              className="form-control"
            >
              <option>P4</option>
              <option>P5</option>
              <option>P6</option>
            </select>
            <select
              value={taskForm.mode}
              onChange={(event) => setTaskForm({ ...taskForm, mode: event.target.value as "PRACTICE" | "EXAM" })}
              className="form-control"
              data-testid="task-mode-select"
            >
              <option value="PRACTICE">Practice Mode</option>
              <option value="EXAM">Exam Mode</option>
            </select>
            <input
              value={taskForm.word_minimum}
              onChange={(event) => setTaskForm({ ...taskForm, word_minimum: event.target.value })}
              className="form-control"
              placeholder="Minimum words"
            />
            <input
              value={taskForm.word_maximum}
              onChange={(event) => setTaskForm({ ...taskForm, word_maximum: event.target.value })}
              className="form-control"
              placeholder="Maximum words"
            />
            <input
              type="datetime-local"
              value={taskForm.due_at}
              onChange={(event) => setTaskForm({ ...taskForm, due_at: event.target.value })}
              className="form-control"
            />
            {taskForm.mode === "EXAM" ? (
              <input
                type="number"
                min={1}
                max={240}
                value={taskForm.exam_duration_minutes}
                onChange={(event) => setTaskForm({ ...taskForm, exam_duration_minutes: event.target.value })}
                className="form-control"
                placeholder="Exam minutes"
                data-testid="exam-duration-input"
              />
            ) : null}
            <select
              value={taskForm.status}
              onChange={(event) => setTaskForm({ ...taskForm, status: event.target.value as "DRAFT" | "PUBLISHED" })}
              className="form-control"
            >
              <option>DRAFT</option>
              <option>PUBLISHED</option>
            </select>
          </div>
          <textarea
            value={taskForm.instruction}
            onChange={(event) => setTaskForm({ ...taskForm, instruction: event.target.value })}
            rows={4}
            className="mt-3 w-full form-control"
            placeholder="Writing instruction"
          />
          <button type="submit" className="mt-4 btn btn-primary btn-lg">
            Create task
          </button>
        </form>
      </section>

      <section className={`grid gap-5 lg:grid-cols-[0.85fr_1.15fr] ${activeWorkbench === "tasks" ? "" : "hidden"}`}>
        <form onSubmit={onAssignTask} className="section-card">
          <div className="panel-header">
            <div>
              <h2 className="panel-title">Assignment flow</h2>
              <p className="panel-subtitle">Publish a task to one assigned class at a time.</p>
            </div>
          </div>
          <select
            value={assignmentForm.task_id}
            onChange={(event) => setAssignmentForm({ ...assignmentForm, task_id: event.target.value })}
            className="mt-4 w-full form-control"
          >
            {state.tasks.map((task) => (
              <option key={task.id} value={task.id}>{task.title}</option>
            ))}
          </select>
          <select
            value={assignmentForm.class_id}
            onChange={(event) => setAssignmentForm({ ...assignmentForm, class_id: event.target.value })}
            className="mt-3 w-full form-control"
          >
            {state.classes.map((schoolClass) => (
              <option key={schoolClass.id} value={schoolClass.id}>{schoolClass.name}</option>
            ))}
          </select>
          <button type="submit" className="mt-4 btn btn-primary btn-lg">
            Assign task
          </button>
        </form>

        <div className="section-card">
          <div className="panel-header">
            <div>
              <h2 className="panel-title">Active tasks</h2>
              <p className="panel-subtitle">Draft, publish, close and archive teacher-owned writing tasks.</p>
            </div>
            <span className="status-pill-muted">{state.tasks.length} tasks</span>
          </div>
          <div className="mt-4 grid gap-3">
            {state.tasks.map((task) => (
              <div key={task.id} className="muted-panel" data-testid="teacher-active-task">
                <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                  <p className="font-semibold text-ink">{task.title}</p>
                  <p className="text-xs font-semibold text-moss">{task.status} · {task.mode}</p>
                </div>
                <p className="mt-2 text-sm text-ink/65">
                  {task.level} · {task.rubric_title ?? "No rubric"} · Assigned: {task.assigned_classes.join(", ") || "-"}
                </p>
                <div className="mt-3 flex flex-wrap gap-2">
                  {task.status === "DRAFT" ? (
                    <button
                      type="button"
                      onClick={() => void onChangeTaskStatus(task, "PUBLISHED")}
                      className="btn btn-primary text-xs"
                    >
                      Publish
                    </button>
                  ) : null}
                  {task.status === "PUBLISHED" ? (
                    <button
                      type="button"
                      onClick={() => void onChangeTaskStatus(task, "CLOSED")}
                      className="btn btn-secondary text-xs"
                    >
                      Close
                    </button>
                  ) : null}
                  {task.status !== "ARCHIVED" ? (
                    <button
                      type="button"
                      onClick={() => void onChangeTaskStatus(task, "ARCHIVED")}
                      className="btn btn-secondary text-xs"
                    >
                      Archive
                    </button>
                  ) : null}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section id="reports" className={`section-anchor ${activeWorkbench === "reports" || activeWorkbench === "marking" ? "" : "hidden"}`}>
        <div className={`mb-5 section-card ${activeWorkbench === "reports" ? "" : "hidden"}`}>
          <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <h2 className="text-xl font-semibold text-ink">Data / report page</h2>
              <p className="mt-1 text-sm text-ink/65">Class completion, rubric breakdown, weaknesses and exports.</p>
            </div>
            <div className="flex flex-wrap gap-2">
              <select
                value={reportClassId}
                onChange={(event) => {
                  setReportClassId(event.target.value);
                  setClassReport(null);
                  setReportExports([]);
                  setLastExport(null);
                }}
                className="form-control"
                data-testid="report-class-select"
              >
                {state.classes.map((schoolClass) => (
                  <option key={schoolClass.id} value={schoolClass.id}>{schoolClass.name}</option>
                ))}
              </select>
              <button
                type="button"
                onClick={() => void onPreviewReport()}
                disabled={!reportClassId || reportBusy}
                className="btn btn-secondary disabled:opacity-50"
                data-testid="report-preview"
              >
                Preview
              </button>
              <button
                type="button"
                onClick={() => void onGenerateReport()}
                disabled={!reportClassId || reportBusy}
                className="btn btn-primary disabled:opacity-50"
                data-testid="report-generate"
              >
                Generate
              </button>
              <button
                type="button"
                onClick={() => void onDownloadReport("csv")}
                disabled={!reportClassId || reportBusy}
                className="btn btn-outline disabled:opacity-50"
                data-testid="report-export-csv"
              >
                CSV
              </button>
              <button
                type="button"
                onClick={() => void onDownloadReport("pdf")}
                disabled={!reportClassId || reportBusy}
                className="btn btn-outline disabled:opacity-50"
                data-testid="report-export-pdf"
              >
                PDF
              </button>
            </div>
          </div>

          {lastExport ? (
            <div className="mt-4 rounded-md bg-moss/10 px-3 py-2 text-sm text-moss" data-testid="report-export-status">
              Last export: {lastExport.filename} · {Math.max(1, Math.ceil(lastExport.bytes / 1024))} KB
            </div>
          ) : null}

          {classReport ? (
            <div className="mt-5 grid gap-4" data-testid="report-result">
              <div className="grid gap-3 md:grid-cols-4">
                <div className="muted-panel">
                  <p className="text-xs font-semibold uppercase text-ink/55">Students</p>
                  <p className="mt-1 text-2xl font-semibold">{classReport.summary.student_count}</p>
                </div>
                <div className="muted-panel">
                  <p className="text-xs font-semibold uppercase text-ink/55">Completion</p>
                  <p className="mt-1 text-2xl font-semibold">
                    {Math.round(classReport.summary.completion_rate * 100)}%
                  </p>
                </div>
                <div className="muted-panel">
                  <p className="text-xs font-semibold uppercase text-ink/55">Submitted</p>
                  <p className="mt-1 text-2xl font-semibold">
                    {classReport.summary.submitted_count}/{classReport.summary.expected_submissions}
                  </p>
                </div>
                <div className="muted-panel">
                  <p className="text-xs font-semibold uppercase text-ink/55">Avg score</p>
                  <p className="mt-1 text-2xl font-semibold">
                    {classReport.summary.average_total_score ?? "-"}
                  </p>
                </div>
              </div>
              <div className="grid gap-4 lg:grid-cols-2">
                <div className="muted-panel">
                  <p className="text-sm font-semibold text-ink">Rubric breakdown</p>
                  <div className="mt-4 grid gap-3 text-sm text-ink/70">
                    {[
                      ["Content", classReport.rubric_breakdown.content_average],
                      ["Language", classReport.rubric_breakdown.language_average],
                      ["Organisation", classReport.rubric_breakdown.organisation_average],
                    ].map(([label, value]) => (
                      <div key={label}>
                        <div className="mb-1 flex items-center justify-between gap-3">
                          <span>{label}</span>
                          <span className="font-semibold text-ink">{value ?? "-"}/5</span>
                        </div>
                        <div className="bar-track" aria-hidden="true">
                          <div className="bar-fill" style={{ width: scorePercent(value as number | null, 5) }} />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
                <div className="muted-panel">
                  <p className="text-sm font-semibold text-ink">Common weaknesses</p>
                  <div className="mt-3 grid gap-2 text-sm text-ink/70">
                    {classReport.common_weaknesses.length === 0 ? <p>No weakness data yet.</p> : null}
                    {classReport.common_weaknesses.slice(0, 5).map((item) => (
                      <div key={item.weakness} className="flex items-center justify-between gap-3 rounded-md bg-paper px-3 py-2">
                        <span>{item.weakness}</span>
                        <span className="text-sm font-semibold text-coral">{item.count}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
              <div className="muted-panel">
                <p className="text-sm font-semibold text-ink">Score distribution</p>
                <div className="mt-4 grid gap-3 text-sm text-ink/70">
                  {Object.entries(classReport.score_distribution).length === 0 ? <p>No score data yet.</p> : null}
                  {Object.entries(classReport.score_distribution).map(([bucket, count]) => (
                    <div key={bucket} className="grid gap-2 sm:grid-cols-[110px_1fr_48px] sm:items-center">
                      <span className="font-semibold text-ink">{bucket}</span>
                      <div className="bar-track" aria-hidden="true">
                        <div
                          className="bar-fill"
                          style={{ width: `${Math.round((count / reportDistributionMax) * 100)}%` }}
                        />
                      </div>
                      <span className="text-right font-semibold text-ink">{count}</span>
                    </div>
                  ))}
                </div>
              </div>
              <div className="muted-panel">
                <p className="text-sm font-semibold text-ink">Export audit</p>
                {reportExports.length === 0 ? (
                  <p className="mt-2 text-sm text-ink/60">No report exports recorded for this class yet.</p>
                ) : (
                  <div className="mt-3 grid gap-2 text-sm text-ink/70" data-testid="report-export-audit">
                    {reportExports.slice(0, 5).map((entry) => (
                      <p key={entry.id}>
                        {entry.format.toUpperCase()} · {new Date(entry.created_at).toLocaleString()} · task{" "}
                        {entry.task_id ?? "all"}
                      </p>
                    ))}
                  </div>
                )}
              </div>
              <div className="overflow-x-auto rounded-md bg-chalk">
                <table className="w-full min-w-[760px] text-left text-sm">
                  <thead className="border-b border-ink/10 text-xs uppercase text-ink/55">
                    <tr>
                      <th className="px-3 py-2">Student</th>
                      <th className="px-3 py-2">Task</th>
                      <th className="px-3 py-2">Submitted</th>
                      <th className="px-3 py-2">Words</th>
                      <th className="px-3 py-2">Score</th>
                      <th className="px-3 py-2">Review</th>
                    </tr>
                  </thead>
                  <tbody>
                    {classReport.completion_rows.slice(0, 12).map((row) => (
                      <tr key={`${row.student_id}-${row.task_id}`} className="border-b border-ink/5">
                        <td className="px-3 py-2">{row.student_number} · {row.student_name}</td>
                        <td className="px-3 py-2">{row.task_title}</td>
                        <td className="px-3 py-2">{row.submitted ? "Yes" : "No"}</td>
                        <td className="px-3 py-2">{row.word_count ?? "-"}</td>
                        <td className="px-3 py-2">{row.total_score ?? "-"}</td>
                        <td className="px-3 py-2">{row.review_status ?? row.marking_status ?? "-"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ) : (
            <p className="mt-4 empty-state">
              Select a class and generate or preview a report.
            </p>
          )}
        </div>

        <div id="marking" className={`section-anchor section-card ${activeWorkbench === "marking" ? "" : "hidden"}`}>
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <h2 className="text-xl font-semibold text-ink">AI marking queue</h2>
            <button
              type="button"
              onClick={() => void refresh()}
              className="w-fit btn btn-secondary"
            >
              Refresh
            </button>
          </div>
          <div className="mt-4 grid gap-4">
            {state.markingItems.length === 0 ? (
              <p className="empty-state">No submitted writing yet.</p>
            ) : null}
            {state.markingItems.map((item) => {
              const result = item.marking_result;
              const draft = result ? reviewDrafts[result.id] : undefined;
              return (
                <div key={item.submission.id} className="muted-panel border border-ink/10" data-testid="marking-item">
                  <div className="flex flex-col gap-2 lg:flex-row lg:items-start lg:justify-between">
                    <div>
                      <p className="font-semibold text-ink">{item.task.title}</p>
                      <p className="mt-1 text-sm text-ink/65">
                        {item.class_name} · {item.task.mode} · {item.submission.word_count} words
                      </p>
                      <p className="mt-2 line-clamp-2 max-w-3xl text-sm text-ink/70">{item.submission.content_text}</p>
                    </div>
                    <div className="text-sm font-semibold text-moss">{result?.status ?? "NO_JOB"}</div>
                  </div>
                  {result ? (
                    <div className="mt-4 grid gap-4 lg:grid-cols-[1fr_0.9fr]">
                      <div className="rounded-md bg-paper p-4 text-sm text-ink/75">
                        <p className="font-semibold text-ink">
                          AI score: {result.total_score ?? "-"} · confidence {result.confidence_level ?? "-"}
                        </p>
                        <div className="mt-3 grid gap-2 sm:grid-cols-3">
                          {[
                            ["Content", result.content_score],
                            ["Language", result.language_score],
                            ["Organisation", result.organisation_score],
                          ].map(([label, value]) => (
                            <div key={label} className="rounded-md bg-chalk px-3 py-2">
                              <p className="text-xs font-semibold uppercase text-ink/45">{label}</p>
                              <p className="mt-1 text-lg font-semibold text-ink">{value ?? "-"}/5</p>
                            </div>
                          ))}
                        </div>
                        <div className="mt-3 grid gap-2 leading-6">
                          <p>{result.content_feedback ?? result.last_error ?? "Queued for marking."}</p>
                          {result.language_feedback ? <p>{result.language_feedback}</p> : null}
                          {result.organisation_feedback ? <p>{result.organisation_feedback}</p> : null}
                        </div>
                        {result.strengths.length > 0 ? (
                          <div className="mt-3 flex flex-wrap gap-2">
                            {result.strengths.slice(0, 4).map((strength) => (
                              <span key={strength} className="insight-chip">{strength}</span>
                            ))}
                          </div>
                        ) : null}
                        {result.weaknesses.length > 0 ? (
                          <div className="mt-2 flex flex-wrap gap-2">
                            {result.weaknesses.slice(0, 4).map((weakness) => (
                              <span key={weakness} className="insight-chip-warning">{weakness}</span>
                            ))}
                          </div>
                        ) : null}
                        {result.warning_flags.length > 0 ? (
                          <div className="mt-3 rounded-md border border-coral/20 bg-coral/5 p-3 text-coral">
                            Warning flags: {result.warning_flags.join(", ")}
                          </div>
                        ) : null}
                        {result.sentence_level_comments.length > 0 ? (
                          <div className="mt-3 rounded-md bg-chalk p-3">
                            <p className="font-semibold text-ink">Sentence comments</p>
                            <div className="mt-2 grid gap-2">
                              {result.sentence_level_comments.slice(0, 3).map((comment, index) => (
                                <p key={`${comment.sentence}-${index}`}>
                                  <span className="font-semibold text-ink">{comment.category}: </span>
                                  {comment.comment}
                                </p>
                              ))}
                            </div>
                          </div>
                        ) : null}
                        {result.recommended_exercises.length > 0 ? (
                          <div className="mt-3 rounded-md bg-chalk p-3">
                            <p className="font-semibold text-ink">Recommended exercises</p>
                            <div className="mt-2 grid gap-1">
                              {result.recommended_exercises.slice(0, 3).map((exercise) => (
                                <p key={exercise.title}>{exercise.title} · {exercise.focus_area}</p>
                              ))}
                            </div>
                          </div>
                        ) : null}
                        <button
                          type="button"
                          onClick={() => void onRunMarking(result.id)}
                          className="mt-3 btn btn-primary"
                          data-testid="run-ai-marking"
                        >
                          Run AI marking
                        </button>
                      </div>
                      <div className="rounded-md bg-paper p-4">
                        <p className="text-sm font-semibold text-ink">Teacher review override</p>
                        <div className="mt-3 grid grid-cols-3 gap-2">
                          <input
                            value={draft?.content ?? ""}
                            onChange={(event) =>
                              setReviewDrafts((current) => ({
                                ...current,
                                [result.id]: { ...(current[result.id] ?? { language: "", organisation: "", notes: "" }), content: event.target.value },
                              }))
                            }
                            className="form-control-compact"
                            placeholder="Content"
                            data-testid="review-content"
                          />
                          <input
                            value={draft?.language ?? ""}
                            onChange={(event) =>
                              setReviewDrafts((current) => ({
                                ...current,
                                [result.id]: { ...(current[result.id] ?? { content: "", organisation: "", notes: "" }), language: event.target.value },
                              }))
                            }
                            className="form-control-compact"
                            placeholder="Language"
                            data-testid="review-language"
                          />
                          <input
                            value={draft?.organisation ?? ""}
                            onChange={(event) =>
                              setReviewDrafts((current) => ({
                                ...current,
                                [result.id]: { ...(current[result.id] ?? { content: "", language: "", notes: "" }), organisation: event.target.value },
                              }))
                            }
                            className="form-control-compact"
                            placeholder="Organisation"
                            data-testid="review-organisation"
                          />
                        </div>
                        <textarea
                          value={draft?.notes ?? ""}
                          onChange={(event) =>
                            setReviewDrafts((current) => ({
                              ...current,
                              [result.id]: { ...(current[result.id] ?? { content: "", language: "", organisation: "" }), notes: event.target.value },
                            }))
                          }
                          rows={2}
                          className="form-control-compact mt-2 w-full"
                          placeholder="Review notes"
                          data-testid="review-notes"
                        />
                        <button
                          type="button"
                          onClick={() => void onReviewMarking(result.id)}
                          className="mt-3 btn btn-outline"
                          data-testid="save-review"
                        >
                          Save review
                        </button>
                        <button
                          type="button"
                          onClick={() => void onReleaseFeedback(result.id)}
                          disabled={result.status !== "AI_MARKED"}
                          className="ml-2 mt-3 btn btn-primary disabled:cursor-not-allowed disabled:bg-ink/25"
                          data-testid="release-feedback"
                        >
                          Release feedback
                        </button>
                      </div>
                    </div>
                  ) : null}
                </div>
              );
            })}
          </div>
        </div>
      </section>
    </AppShell>
  );
}
