"use client";

import type { FormEvent } from "react";
import type {
  AccountCapabilities,
  ClassReportPayload,
  PromptDraft,
  ReportExportAudit,
  Rubric,
  SchoolClass,
  TeacherMarkingSubmission,
  TeacherStudent,
  WritingTask,
} from "@english-ai-writing/shared";
import { useEffect, useState } from "react";
import Link from "next/link";

import { AppShell, type AppShellUser } from "@/components/app-shell";
import { TeacherReviewDesk } from "@/components/teacher-review-desk";
import { currentUser, logout } from "@/lib/auth";
import {
  assignTask,
  authenticatedMediaUrl,
  createTeacherStudent,
  createRubric,
  createTask,
  downloadClassReport,
  generateClassReport,
  generatePromptDraft as generatePromptDraftApi,
  generateTaskImage,
  getAccountCapabilities,
  getClassReport,
  listClassReportExports,
  listTeacherClasses,
  listTeacherMarkingSubmissions,
  listTeacherRubrics,
  listTeacherTasks,
  listTeacherStudents,
  releaseFeedback,
  reviewMarking,
  runMarking,
  updateTask,
} from "@/lib/school-data";

export type TeacherScreen = "home" | "marking" | "assignments" | "reports" | "pupils";

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
      students: TeacherStudent[];
      capabilities: AccountCapabilities;
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

type ReviewDraft = {
  content: string;
  language: string;
  organisation: string;
  notes: string;
};

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

const screenCopy: Record<TeacherScreen, { title: string; subtitle: string }> = {
  home: {
    title: "Today",
    subtitle: "Prepare a lesson, review pupil writing, and choose the next teaching move.",
  },
  marking: {
    title: "Review writing",
    subtitle: "Check AI evidence, make the final judgement, and release feedback when it is ready.",
  },
  assignments: {
    title: "Prepare & assign",
    subtitle: "See what pupils are working on, and publish new writing when you are ready.",
  },
  reports: {
    title: "Class insights",
    subtitle: "See progress, spot shared needs, and prepare a report people can read.",
  },
  pupils: {
    title: "Pupils",
    subtitle: "Create pupil sign-ins and keep each class roster ready for writing lessons.",
  },
};

function scorePercent(value: number | null | undefined, maxScore: number) {
  if (!Number.isFinite(value ?? Number.NaN) || maxScore <= 0) return "0%";
  return `${Math.max(0, Math.min(100, Math.round(((value ?? 0) / maxScore) * 100)))}%`;
}

function statusBadge(status: string | null | undefined) {
  if (status === "PUBLISHED" || status === "AI_MARKED" || status === "RELEASED" || status === "ACTIVE") {
    return "badge-success";
  }
  if (status === "DRAFT" || status === "QUEUED" || status === "PROCESSING" || status === "REVIEWED") {
    return "badge-warning";
  }
  if (status === "ARCHIVED" || status === "CLOSED" || status === "AI_MARKING_FAILED") return "badge-danger";
  return "badge-soft";
}

function formatDate(value: string | null | undefined) {
  if (!value) return "No due date";
  return new Date(value).toLocaleDateString();
}

function words(task: WritingTask) {
  return `${task.word_minimum ?? "-"}-${task.word_maximum ?? "-"} words`;
}

function createDefaultTaskForm(rubricId = ""): TaskForm {
  return {
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
    rubric_id: rubricId,
  };
}

function ReleaseModal({
  open,
  onCancel,
  onConfirm,
}: {
  open: boolean;
  onCancel: () => void;
  onConfirm: () => void;
}) {
  return (
    <div className={`modal-backdrop ${open ? "open" : ""}`} role="dialog" aria-modal="true" aria-labelledby="release-title">
      <div className="modal">
        <p className="eyebrow">Final teacher action</p>
        <h2 className="panel-title" id="release-title" style={{ fontSize: "var(--text-xl)", marginTop: 8 }}>
          Release this feedback to the student?
        </h2>
        <p className="panel-subtitle" style={{ marginTop: 12 }}>
          The student will see only the teacher-confirmed score, final comment, and attached practice tasks.
        </p>
        <div className="row-actions">
          <button className="btn btn-secondary" type="button" onClick={onCancel}>
            Review again
          </button>
          <button className="btn teacher-release-button" type="button" onClick={onConfirm}>
            Release now
          </button>
        </div>
      </div>
    </div>
  );
}

function Metric({ label, value, note }: { label: string; value: string | number; note: string }) {
  return (
    <div className="metric emphasis">
      <p className="micro-label">{label}</p>
      <p className="metric-value">{value}</p>
      <p className="metric-note">{note}</p>
    </div>
  );
}

function Segmented<T extends string>({
  value,
  options,
  onChange,
}: {
  value: T;
  options: Array<{ value: T; label: string }>;
  onChange: (value: T) => void;
}) {
  return (
    <div className="segmented">
      {options.map((option) => (
        <button
          key={option.value}
          type="button"
          className={`segment ${value === option.value ? "active" : ""}`}
          onClick={() => onChange(option.value)}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}

export function TeacherWorkspace({ screen }: { screen: TeacherScreen }) {
  const [state, setState] = useState<TeacherState>({ status: "loading" });
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [toast, setToast] = useState("");
  const [taskForm, setTaskForm] = useState<TaskForm>(() => createDefaultTaskForm());
  const [assignmentForm, setAssignmentForm] = useState({ task_id: "", class_id: "" });
  const [rubricForm, setRubricForm] = useState({ title: "P5 Narrative Writing Rubric", level: "P5" });
  const [taskFilter, setTaskFilter] = useState<"active" | "draft" | "closed">("active");
  const [markingTab, setMarkingTab] = useState<"suggestions" | "scores" | "release">("suggestions");
  const [selectedSubmissionId, setSelectedSubmissionId] = useState("");
  const [releaseTarget, setReleaseTarget] = useState<string | null>(null);
  const [acceptedSuggestionIds, setAcceptedSuggestionIds] = useState<Set<string>>(new Set());
  const [reviewDrafts, setReviewDrafts] = useState<Record<string, ReviewDraft>>({});
  const [promptDraft, setPromptDraft] = useState<{
    title: string;
    body: string;
    focus: string[];
    source?: PromptDraft;
  } | null>(null);
  const [promptBusy, setPromptBusy] = useState(false);
  const [teachingFocus, setTeachingFocus] = useState("Past tense verbs, event sequence, and reflection");
  const [composerOpen, setComposerOpen] = useState(false);
  const [aiAssistOpen, setAiAssistOpen] = useState(false);
  const [rubricFormOpen, setRubricFormOpen] = useState(false);
  const [publishConfirmOpen, setPublishConfirmOpen] = useState(false);
  const [openTaskMenuId, setOpenTaskMenuId] = useState<string | null>(null);
  const [previousInstruction, setPreviousInstruction] = useState<{ title: string; instruction: string } | null>(null);
  const [reportClassId, setReportClassId] = useState("");
  const [reportTaskId, setReportTaskId] = useState("");
  const [classReport, setClassReport] = useState<ClassReportPayload | null>(null);
  const [reportExports, setReportExports] = useState<ReportExportAudit[]>([]);
  const [reportBusy, setReportBusy] = useState(false);
  const [lastExport, setLastExport] = useState<{ format: string; filename: string; bytes: number } | null>(null);
  const [imageBusyTaskId, setImageBusyTaskId] = useState<string | null>(null);
  const [pupilBusy, setPupilBusy] = useState(false);
  const [pupilForm, setPupilForm] = useState({
    display_name: "",
    email: "",
    temporary_password: "",
    class_id: "",
    student_number: "",
  });

  function showToast(message: string) {
    setToast(message);
    window.setTimeout(() => setToast(""), 2600);
  }

  function updateReviewDraft(markingResultId: string, patch: Partial<ReviewDraft>) {
    setReviewDrafts((current) => {
      const existing = current[markingResultId];
      return {
        ...current,
        [markingResultId]: {
          content: existing?.content ?? "",
          language: existing?.language ?? "",
          organisation: existing?.organisation ?? "",
          notes: existing?.notes ?? "",
          ...patch,
        },
      };
    });
  }

  async function refresh(user?: AppShellUser) {
    const [classes, rubrics, tasks, markingItems, students, capabilities] = await Promise.all([
      listTeacherClasses(),
      listTeacherRubrics(),
      listTeacherTasks(),
      listTeacherMarkingSubmissions(),
      listTeacherStudents(),
      getAccountCapabilities(),
    ]);
    setState((current) => {
      const shellUser = user ?? (current.status === "ready" ? current.user : null);
      if (!shellUser) return current;
      return { status: "ready", user: shellUser, classes, rubrics, tasks, markingItems, students, capabilities };
    });
    setTaskForm((current) => ({ ...current, rubric_id: current.rubric_id || rubrics[0]?.id || "" }));
    setAssignmentForm((current) => ({
      task_id: current.task_id || tasks[0]?.id || "",
      class_id: current.class_id || classes.find((schoolClass) => schoolClass.name === "P5A")?.id || classes[0]?.id || "",
    }));
    setReportClassId((current) => current || classes.find((schoolClass) => schoolClass.name === "P5A")?.id || classes[0]?.id || "");
    setPupilForm((current) => ({
      ...current,
      class_id: current.class_id || classes.find((schoolClass) => schoolClass.name === "P5A")?.id || classes[0]?.id || "",
    }));
    setSelectedSubmissionId((current) => current || markingItems[0]?.submission.id || "");
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
        window.location.href = "/login";
        return;
      }
      if (user.role !== "TEACHER") {
        setState({ status: "denied", message: "Your role cannot access the teacher workspace." });
        return;
      }
      await refresh({ display_name: user.display_name, email: user.email, role: user.role });
    }
    void load().catch((err) => {
      setState({
        status: "denied",
        message: err instanceof Error ? err.message : "Unable to load teacher workspace.",
      });
    });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (screen !== "reports" || !reportClassId) return;
    let active = true;
    setReportBusy(true);
    setError("");
    Promise.all([
      getClassReport(reportClassId, reportTaskId || undefined),
      listClassReportExports(reportClassId),
    ])
      .then(([report, exports]) => {
        if (!active) return;
        setClassReport(report);
        setReportExports(exports);
      })
      .catch((err) => {
        if (!active) return;
        setError(err instanceof Error ? err.message : "Unable to load this class report.");
      })
      .finally(() => {
        if (active) setReportBusy(false);
      });
    return () => {
      active = false;
    };
  }, [screen, reportClassId, reportTaskId]);

  async function onLogout() {
    await logout();
    window.location.href = "/login";
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

  async function createTaskFromForm(status: "DRAFT" | "PUBLISHED"): Promise<boolean> {
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
        exam_duration_minutes: taskForm.mode === "EXAM" ? Number(taskForm.exam_duration_minutes || "30") : undefined,
        rubric_id: taskForm.rubric_id,
        status,
      });
      const targetClass = state.status === "ready"
        ? state.classes.find((schoolClass) => schoolClass.id === assignmentForm.class_id)
        : undefined;
      if (status === "PUBLISHED" && assignmentForm.class_id) {
        await assignTask(task.id, assignmentForm.class_id);
      }
      setTaskForm((current) => ({ ...current, status }));
      setNotice(
        status === "PUBLISHED"
          ? `Published “${task.title}” to ${targetClass?.name ?? "the selected class"}.`
          : `Draft saved: ${task.title}.`,
      );
      showToast(
        status === "PUBLISHED"
          ? `Pupils in ${targetClass?.name ?? "the selected class"} can now see this task.`
          : "Draft saved. You can return to it before publishing.",
      );
      await refresh();
      return true;
    } catch (err) {
      setError(err instanceof Error ? err.message : status === "PUBLISHED" ? "Unable to publish this task." : "Unable to save this draft.");
      return false;
    }
  }

  async function saveTaskAndClose(status: "DRAFT" | "PUBLISHED") {
    const saved = await createTaskFromForm(status);
    if (!saved) return;
    setComposerOpen(false);
    setAiAssistOpen(false);
    setRubricFormOpen(false);
    setPromptDraft(null);
    setPreviousInstruction(null);
  }

  async function onCreateRubricDirect() {
    setNotice("");
    setError("");
    try {
      const rubric = await createRubric({
        title: rubricForm.title,
        level: rubricForm.level,
        total_score: defaultDimensions.reduce((sum, dimension) => sum + dimension.max_score, 0),
        status: "ACTIVE",
        dimensions: defaultDimensions,
      });
      setTaskForm((current) => ({ ...current, rubric_id: rubric.id }));
      setRubricFormOpen(false);
      showToast(`Rubric “${rubric.title}” created and selected.`);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to create this rubric.");
    }
  }

  async function onChangeTaskStatus(task: WritingTask, status: "DRAFT" | "PUBLISHED" | "CLOSED" | "ARCHIVED") {
    setNotice("");
    setError("");
    try {
      await updateTask(task.id, { status });
      setNotice(`${task.title} is now ${status}.`);
      showToast(`Task status updated to ${status}.`);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to update task status.");
    }
  }

  async function onGenerateTaskImage(task: WritingTask) {
    setImageBusyTaskId(task.id);
    setError("");
    setNotice("");
    try {
      await generateTaskImage(task.id);
      setNotice(`A new prompt picture is ready for “${task.title}”.`);
      showToast("Prompt picture generated. Pupils will see it with the task.");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to generate a prompt picture.");
    } finally {
      setImageBusyTaskId(null);
    }
  }

  async function onCreatePupil(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPupilBusy(true);
    setError("");
    setNotice("");
    try {
      const student = await createTeacherStudent({
        display_name: pupilForm.display_name,
        email: pupilForm.email,
        temporary_password: pupilForm.temporary_password,
        class_id: pupilForm.class_id,
        student_number: pupilForm.student_number || undefined,
      });
      setNotice(`${student.display_name} can now sign in. Share the temporary password privately.`);
      showToast(`Pupil added to ${student.class_name}.`);
      setPupilForm((current) => ({ ...current, display_name: "", email: "", temporary_password: "", student_number: "" }));
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to create this pupil account.");
    } finally {
      setPupilBusy(false);
    }
  }

  async function onRunMarking(markingResultId: string) {
    setNotice("");
    setError("");
    try {
      const result = await runMarking(markingResultId);
      setNotice(`AI marking status: ${result.status}`);
      showToast("AI marking run queued.");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to run AI marking.");
    }
  }

  async function onReviewMarking(markingResultId: string) {
    if (state.status !== "ready") return;
    const draft = reviewDrafts[markingResultId];
    if (!draft) return;
    const reviewItem = state.markingItems.find(
      (item) => item.marking_result?.id === markingResultId,
    );
    if (!reviewItem) return;
    const scoreMaximum = (name: string) => reviewItem.task.rubric.dimensions.find(
      (dimension) => dimension.name.toLowerCase() === name.toLowerCase(),
    )?.max_score;
    const maxima = {
      content: scoreMaximum("Content"),
      language: scoreMaximum("Language"),
      organisation: scoreMaximum("Organisation"),
    };
    const content = Number(draft.content);
    const language = Number(draft.language);
    const organisation = Number(draft.organisation);
    setNotice("");
    setError("");
    const scores = [
      { label: "Content", value: content, maximum: maxima.content },
      { label: "Language", value: language, maximum: maxima.language },
      { label: "Organisation", value: organisation, maximum: maxima.organisation },
    ];
    const invalidScore = scores.find(
      ({ value, maximum }) => !Number.isInteger(value)
        || maximum === undefined
        || value < 0
        || value > maximum,
    );
    if (invalidScore) {
      setError(
        invalidScore.maximum === undefined
          ? "This task's rubric is missing a required score category."
          : `${invalidScore.label} score must be a whole number from 0 to ${invalidScore.maximum}.`,
      );
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
      setNotice(`Teacher review saved: total ${review.total_score ?? 0}.`);
      showToast("Review saved. Students cannot see it until release.");
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
      setReleaseTarget(null);
      setNotice(`Feedback released: ${review.feedback_released_at ?? "released"}.`);
      showToast("Feedback released. The student can now see the teacher's final comment.");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to release feedback.");
    }
  }

  async function onPreviewReport() {
    if (!reportClassId) return;
    setReportBusy(true);
    setNotice("");
    setError("");
    try {
      setClassReport(await getClassReport(reportClassId, reportTaskId || undefined));
      setReportExports(await listClassReportExports(reportClassId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to preview report.");
    } finally {
      setReportBusy(false);
    }
  }

  async function onGenerateReport() {
    if (!reportClassId) return;
    setReportBusy(true);
    setNotice("");
    setError("");
    showToast("Regenerating the class report.");
    try {
      setClassReport(await generateClassReport(reportClassId, reportTaskId || undefined));
      setReportExports(await listClassReportExports(reportClassId));
      setNotice("Class report regenerated.");
      showToast("Report updated. Export history keeps the last file.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to generate report.");
    } finally {
      setReportBusy(false);
    }
  }

  async function onDownloadReport(format: "csv" | "pdf") {
    if (!reportClassId) return;
    setNotice("");
    setError("");
    showToast(`${format.toUpperCase()} export has been queued.`);
    try {
      const downloaded = await downloadClassReport(reportClassId, format, reportTaskId || undefined);
      setLastExport({ format, filename: downloaded.filename, bytes: downloaded.bytes });
      setReportExports(await listClassReportExports(reportClassId));
      setNotice(`${format.toUpperCase()} export downloaded: ${downloaded.filename}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : `${format.toUpperCase()} export failed.`);
    }
  }

  async function onGeneratePromptDraft() {
    if (!taskForm.rubric_id) {
      setError("Select a rubric before generating a prompt.");
      return;
    }
    const minimumRaw = Number(taskForm.word_minimum);
    const maximumRaw = Number(taskForm.word_maximum);
    setPromptBusy(true);
    setError("");
    setNotice("");
    showToast("Generating prompt draft.");
    try {
      const draft = await generatePromptDraftApi({
        level: taskForm.level,
        mode: taskForm.mode,
        teaching_focus: teachingFocus,
        word_minimum: Number.isFinite(minimumRaw) && minimumRaw > 0 ? minimumRaw : null,
        word_maximum: Number.isFinite(maximumRaw) && maximumRaw > 0 ? maximumRaw : null,
        exam_duration_minutes: taskForm.mode === "EXAM" ? Number(taskForm.exam_duration_minutes) || 30 : null,
        rubric_id: taskForm.rubric_id,
      });
      setPreviousInstruction({ title: taskForm.title, instruction: taskForm.instruction });
      setPromptDraft({
        title: draft.title,
        body: draft.instruction,
        focus: draft.rubric_notes,
        source: draft,
      });
      setTaskForm((current) => ({ ...current, title: draft.title, instruction: draft.instruction }));
      setAiAssistOpen(false);
      showToast("Pip filled in the title and instruction. Edit anything before publishing.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to generate prompt draft.");
    } finally {
      setPromptBusy(false);
    }
  }

  async function copyPrompt() {
    if (!promptDraft) return;
    const text = `${promptDraft.title}\n\n${promptDraft.body}\n\n${promptDraft.focus.join("\n")}`;
    try {
      await navigator.clipboard.writeText(text);
      showToast("Content copied.");
    } catch {
      showToast("This browser blocked copying. Please select the content manually.");
    }
  }

  if (state.status === "loading") {
    return <main className="loading-state">Loading teacher workspace...</main>;
  }

  if (state.status === "denied") {
    return (
      <main className="centered-state">
        <div>
          <h1 className="screen-title">Access denied</h1>
          <p className="lead">{state.message}</p>
        </div>
      </main>
    );
  }

  const copy = screenCopy[screen];
  const publishedTasks = state.tasks.filter((task) => task.status === "PUBLISHED").length;
  const examTasks = state.tasks.filter((task) => task.mode === "EXAM").length;
  const pendingReview = state.markingItems.filter((item) => item.marking_result?.status !== "AI_MARKED").length;
  const unreleased = state.markingItems.filter((item) => item.marking_result?.status === "AI_MARKED").length;
  const selectedItem = state.markingItems.find((item) => item.submission.id === selectedSubmissionId) ?? state.markingItems[0];
  const selectedResult = selectedItem?.marking_result ?? null;
  const selectedDraft = selectedResult ? reviewDrafts[selectedResult.id] : undefined;
  const reportDistributionMax = classReport ? Math.max(1, ...Object.values(classReport.score_distribution)) : 1;
  const reportRubricRows = classReport
    ? [
        {
          label: "Content",
          value: classReport.rubric_breakdown.content_average,
          percentage: classReport.rubric_breakdown.content_average_percentage,
          maximum: classReport.rubric_breakdown.content_max_score,
          colour: "sage",
        },
        {
          label: "Language",
          value: classReport.rubric_breakdown.language_average,
          percentage: classReport.rubric_breakdown.language_average_percentage,
          maximum: classReport.rubric_breakdown.language_max_score,
          colour: "lavender",
        },
        {
          label: "Organisation",
          value: classReport.rubric_breakdown.organisation_average,
          percentage: classReport.rubric_breakdown.organisation_average_percentage,
          maximum: classReport.rubric_breakdown.organisation_max_score,
          colour: "amber",
        },
      ]
    : [];
  const reportRows = classReport?.completion_rows.slice(0, 12) ?? [];
  const reportTaskTitle = reportTaskId
    ? state.tasks.find((task) => task.id === reportTaskId)?.title ?? "Selected assignment"
    : "All assigned writing";
  const filteredTasks = state.tasks.filter((task) => {
    if (taskFilter === "draft") return task.status === "DRAFT";
    if (taskFilter === "closed") return task.status === "CLOSED" || task.status === "ARCHIVED";
    return task.status === "PUBLISHED";
  });
  const selectedClass = state.classes.find((schoolClass) => schoolClass.id === assignmentForm.class_id);
  const wordMinimum = Number(taskForm.word_minimum);
  const wordMaximum = Number(taskForm.word_maximum);
  const wordRangeError =
    !Number.isFinite(wordMinimum) || !Number.isFinite(wordMaximum) || wordMinimum < 1 || wordMaximum < 1
      ? "Enter a word range using whole numbers."
      : wordMinimum > wordMaximum
        ? "The minimum cannot be larger than the maximum."
        : "";
  const canPublishTask =
    Boolean(taskForm.rubric_id) &&
    Boolean(assignmentForm.class_id) &&
    Boolean(taskForm.title.trim()) &&
    Boolean(taskForm.instruction.trim()) &&
    !wordRangeError;
  const isPro = state.capabilities.plan_code === "SCHOOL_PRO" && state.capabilities.subscription_status === "ACTIVE";
  const markingReadyLabel = `${state.markingItems.length} ${state.markingItems.length === 1 ? "submission" : "submissions"} ready for teacher review`;

  if (String(screen) === "marking") {
    return (
      <AppShell
        title="Teacher Review Desk"
        subtitle={markingReadyLabel}
        user={state.user}
        onLogout={() => void onLogout()}
      >
        {notice ? <div className="notice-success">{notice}</div> : null}
        {error ? <div className="notice-error">{error}</div> : null}
        <TeacherReviewDesk
          items={state.markingItems}
          selectedItem={selectedItem}
          selectedResult={selectedResult}
          selectedDraft={selectedDraft}
          pendingReview={pendingReview}
          readyToRelease={unreleased}
          onSelectSubmission={setSelectedSubmissionId}
          onUpdateDraft={updateReviewDraft}
          onRunMarking={(markingResultId) => void onRunMarking(markingResultId)}
          onSaveReview={(markingResultId) => void onReviewMarking(markingResultId)}
          onRequestRelease={setReleaseTarget}
        />

        <ReleaseModal
          open={Boolean(releaseTarget)}
          onCancel={() => setReleaseTarget(null)}
          onConfirm={() => releaseTarget && void onReleaseFeedback(releaseTarget)}
        />
        <div className={`toast ${toast ? "show" : ""}`} role="status" aria-live="polite">{toast}</div>
      </AppShell>
    );
  }

  return (
    <AppShell
      title={screen === "marking" ? "Teacher Review Desk" : copy.title}
      subtitle={screen === "marking" ? markingReadyLabel : copy.subtitle}
      user={state.user}
      onLogout={() => void onLogout()}
    >
      {notice ? <div className="notice-success" data-testid="teacher-notice">{notice}</div> : null}
      {error ? <div className="notice-error">{error}</div> : null}

      <div className="plan-context" aria-label="School plan">
        <span className={isPro ? "badge-success" : "badge-soft"}>{isPro ? "School Pro" : "Free Sandbox"}</span>
        <span>{isPro ? "Voice, prompt pictures, AI review and reports are available." : "Grammar and basic AI assist are available."}</span>
      </div>

      {screen === "home" ? (
        <>
          <section className="teacher-home-hero">
            <div className="teacher-home-copy">
              <p className="micro-label">Your teaching day</p>
              <h2>One calm path from lesson idea to useful feedback.</h2>
              <p>
                Prepare a prompt, send it to a class, then return here when pupil writing is ready. AI helps with the first pass; you keep the final say.
              </p>
              <div className="teacher-home-actions">
                <Link className="btn btn-primary" href="/teacher/assignments">Prepare a writing lesson</Link>
                <Link className="btn btn-secondary" href="/teacher/marking">Review pupil writing</Link>
              </div>
            </div>
            <aside className="teacher-home-mascot" aria-label="Pip planning assistant">
              <img src="/ai-coach-fox.png" alt="Pip the fox writing coach" />
              <div>
                <p className="micro-label">Pip can help</p>
                <strong>Start with a teaching focus.</strong>
                <p>Try “past tense and stronger feeling words.” I’ll draft the prompt; you decide what pupils receive.</p>
              </div>
            </aside>
          </section>

          <section className="teacher-journey" aria-label="Teacher workflow">
            <article>
              <span>1</span>
              <div>
                <strong>Prepare</strong>
                <p>Draft or write a prompt, choose the rubric, and set the word range.</p>
              </div>
              <Link href="/teacher/assignments">Open lesson setup</Link>
            </article>
            <article>
              <span>2</span>
              <div>
                <strong>Review</strong>
                <p>{state.markingItems.length} submission{state.markingItems.length === 1 ? " is" : "s are"} waiting in the teacher desk.</p>
              </div>
              <Link href="/teacher/marking">Open review desk</Link>
            </article>
            <article>
              <span>3</span>
              <div>
                <strong>Respond</strong>
                <p>Use class patterns to plan the next mini-lesson and share a readable report.</p>
              </div>
              <Link href="/teacher/reports">View class insights</Link>
            </article>
          </section>

          <section className="teacher-home-metrics" aria-label="Teaching overview">
            <Metric label="Live tasks" value={publishedTasks} note={`${examTasks} in Exam Mode`} />
            <Metric label="Review queue" value={state.markingItems.length} note="Pupil submissions received" />
            <Metric label="Ready to release" value={unreleased} note="Teacher confirmation required" />
            <Metric label="Classes" value={state.classes.length} note="Available for assignment" />
          </section>

          <section className="teacher-home-columns">
            <article className="panel teacher-home-list">
              <div className="panel-header">
                <div>
                  <h2 className="panel-title">Live writing this week</h2>
                  <p className="panel-subtitle">The tasks pupils can work on now.</p>
                </div>
                <Link href="/teacher/assignments">Manage</Link>
              </div>
              {state.tasks.filter((task) => task.status === "PUBLISHED").slice(0, 3).map((task) => (
                <div className="teacher-home-row" key={task.id}>
                  <div>
                    <strong>{task.title}</strong>
                    <p>{task.assigned_classes.join(", ") || "Not assigned"} · {words(task)}</p>
                  </div>
                  <span className={task.mode === "EXAM" ? "badge-warning" : "badge-success"}>{task.mode === "EXAM" ? "Exam" : "Practice"}</span>
                </div>
              ))}
            </article>

            <article className="panel teacher-home-list">
              <div className="panel-header">
                <div>
                  <h2 className="panel-title">Next to review</h2>
                  <p className="panel-subtitle">AI evidence stays private until you release it.</p>
                </div>
                <Link href="/teacher/marking">Open queue</Link>
              </div>
              {state.markingItems.slice(0, 3).map((item, index) => (
                <div className="teacher-home-row" key={item.submission.id}>
                  <div>
                    <strong>{item.class_name} · Pupil {String(index + 1).padStart(2, "0")}</strong>
                    <p>{item.task.title} · {item.submission.word_count} words</p>
                  </div>
                  <span className={statusBadge(item.marking_result?.status)}>{item.marking_result?.status === "AI_MARKED" ? "Ready" : "Checking"}</span>
                </div>
              ))}
            </article>
          </section>
        </>
      ) : null}

      {screen === "marking" ? (
        <>
          <section className="grid-4">
            <Metric label="Submitted" value={state.markingItems.length} note="Writing in teacher queue" />
            <Metric label="Pending review" value={pendingReview} note="AI output not ready or not checked" />
            <Metric label="Ready to release" value={unreleased} note="Teacher can confirm feedback" />
            <Metric label="Published tasks" value={publishedTasks} note={`${examTasks} Exam Mode tasks`} />
          </section>

          <section className="editor-layout">
            <article className="document">
              {selectedItem ? (
                <>
                  <div className="task-meta" style={{ marginBottom: 22 }}>
                    <span className="badge-soft">{selectedItem.class_name}</span>
                    <span className="badge-soft">{selectedItem.task.title}</span>
                    <span className={statusBadge(selectedResult?.status)}>{selectedResult?.status ?? "NO JOB"}</span>
                  </div>
                  <h2>Student essay: {selectedItem.task.title}</h2>
                  {selectedItem.submission.content_text.split(/\n+/).slice(0, 8).map((paragraph, index) => (
                    <p key={`${selectedItem.submission.id}-${index}`}>{paragraph}</p>
                  ))}
                </>
              ) : (
                <div className="empty-state">No submitted writing yet.</div>
              )}
            </article>

            <aside className="panel">
              <div className="panel-header">
                <div>
                  <h2 className="panel-title">Suggestions and scoring</h2>
                  <p className="panel-subtitle">AI suggestions stay teacher-only until the final release action.</p>
                </div>
                <span className="badge-soft">{state.markingItems.length} items</span>
              </div>

              <div className="field" style={{ marginBottom: 16 }}>
                <label htmlFor="submission-select">Submission</label>
                <select
                  id="submission-select"
                  className="select"
                  value={selectedItem?.submission.id ?? ""}
                  onChange={(event) => setSelectedSubmissionId(event.target.value)}
                >
                  {state.markingItems.map((item) => (
                    <option key={item.submission.id} value={item.submission.id}>
                      {item.class_name} - {item.task.title} - {item.submission.word_count} words
                    </option>
                  ))}
                </select>
              </div>

              <Segmented
                value={markingTab}
                onChange={setMarkingTab}
                options={[
                  { value: "suggestions", label: "Suggestions" },
                  { value: "scores", label: "Scores" },
                  { value: "release", label: "Release" },
                ]}
              />

              {selectedResult && markingTab === "suggestions" ? (
                <div className="suggestion-list" style={{ marginTop: 18 }}>
                  <div className="suggestion-card">
                    <span className="badge-warning">AI confidence</span>
                    <h3 style={{ marginTop: 12 }}>{selectedResult.confidence_level ?? "Pending"}</h3>
                    <p>This raw AI confidence is only visible to teachers.</p>
                    <button
                      type="button"
                      onClick={() => void onRunMarking(selectedResult.id)}
                      className="btn btn-secondary"
                      style={{ marginTop: 14 }}
                    >
                      Run AI marking
                    </button>
                  </div>
                  {[
                    selectedResult.content_feedback,
                    selectedResult.language_feedback,
                    selectedResult.organisation_feedback,
                    ...selectedResult.sentence_level_comments.slice(0, 2).map((comment) => comment.comment),
                  ]
                    .filter(Boolean)
                    .map((message, index) => {
                      const id = `${selectedResult.id}-${index}`;
                      return (
                        <div
                          key={id}
                          className={`suggestion-card ${acceptedSuggestionIds.has(id) ? "accepted" : ""}`}
                        >
                          <span className={index === 0 ? "badge-warning" : "badge-soft"}>
                            {index === 0 ? "High impact" : "Suggestion"}
                          </span>
                          <h3 style={{ marginTop: 12 }}>{index === 0 ? "Teacher comment draft" : "Writing detail"}</h3>
                          <p>{message}</p>
                          <div className="row-actions" style={{ marginTop: 14 }}>
                            <button
                              type="button"
                              className="btn btn-primary"
                              disabled={acceptedSuggestionIds.has(id)}
                              onClick={() => {
                                setAcceptedSuggestionIds((current) => new Set(current).add(id));
                                showToast("Suggestion added to the teacher review draft.");
                              }}
                            >
                              {acceptedSuggestionIds.has(id) ? "Accepted" : "Accept into review"}
                            </button>
                            <button type="button" className="btn btn-ghost">
                              Ignore
                            </button>
                          </div>
                        </div>
                      );
                    })}
                  {selectedResult.warning_flags.length > 0 ? (
                    <div className="rubric-item">
                      <span className="badge-danger">Warning</span>
                      <p className="panel-subtitle">{selectedResult.warning_flags.join(", ")}</p>
                    </div>
                  ) : null}
                </div>
              ) : null}

              {selectedResult && markingTab === "scores" ? (
                <div style={{ marginTop: 18 }}>
                  <div className="score-grid">
                    {[
                      ["Content", selectedResult.content_score],
                      ["Language", selectedResult.language_score],
                      ["Organisation", selectedResult.organisation_score],
                    ].map(([label, value]) => (
                      <div key={label} className="score-row">
                        <span>{label}</span>
                        <span className="bar">
                          <span style={{ width: scorePercent(value as number | null, 5) }} />
                        </span>
                        <strong>{value ?? "-"}</strong>
                      </div>
                    ))}
                  </div>
                  <div className="form-grid" style={{ marginTop: 18 }}>
                    <div className="grid-3">
                      <input
                        value={selectedDraft?.content ?? ""}
                        onChange={(event) =>
                          setReviewDrafts((current) => ({
                            ...current,
                            [selectedResult.id]: {
                              ...(current[selectedResult.id] ?? {
                                language: "",
                                organisation: "",
                                notes: "",
                              }),
                              content: event.target.value,
                            },
                          }))
                        }
                        className="input"
                        placeholder="Content"
                      />
                      <input
                        value={selectedDraft?.language ?? ""}
                        onChange={(event) =>
                          setReviewDrafts((current) => ({
                            ...current,
                            [selectedResult.id]: {
                              ...(current[selectedResult.id] ?? {
                                content: "",
                                organisation: "",
                                notes: "",
                              }),
                              language: event.target.value,
                            },
                          }))
                        }
                        className="input"
                        placeholder="Language"
                      />
                      <input
                        value={selectedDraft?.organisation ?? ""}
                        onChange={(event) =>
                          setReviewDrafts((current) => ({
                            ...current,
                            [selectedResult.id]: {
                              ...(current[selectedResult.id] ?? {
                                content: "",
                                language: "",
                                notes: "",
                              }),
                              organisation: event.target.value,
                            },
                          }))
                        }
                        className="input"
                        placeholder="Organisation"
                      />
                    </div>
                    <textarea
                      value={selectedDraft?.notes ?? ""}
                      onChange={(event) =>
                        setReviewDrafts((current) => ({
                          ...current,
                          [selectedResult.id]: {
                            ...(current[selectedResult.id] ?? {
                              content: "",
                              language: "",
                              organisation: "",
                            }),
                            notes: event.target.value,
                          },
                        }))
                      }
                      className="textarea"
                      placeholder="Teacher final comment"
                    />
                    <button type="button" className="btn btn-secondary" onClick={() => void onReviewMarking(selectedResult.id)}>
                      Save review
                    </button>
                  </div>
                </div>
              ) : null}

              {selectedResult && markingTab === "release" ? (
                <div className="suggestion-list" style={{ marginTop: 18 }}>
                  <div className="rubric-item">
                    <span className={statusBadge(selectedResult.status)}>{selectedResult.status}</span>
                    <strong>Teacher release required</strong>
                    <p className="panel-subtitle">
                      Students cannot see AI suggestions, scores, or comments until you save a review and release feedback.
                    </p>
                  </div>
                  <button
                    type="button"
                    className="btn btn-primary"
                    disabled={selectedResult.status !== "AI_MARKED"}
                    onClick={() => setReleaseTarget(selectedResult.id)}
                  >
                    Release feedback
                  </button>
                </div>
              ) : null}
            </aside>
          </section>
        </>
      ) : null}

      {screen === "assignments" ? (
        <>
          <section className="composer-toolbar">
            <div>
              <h2 className="panel-title">Writing tasks</h2>
              <p className="panel-subtitle">Check what pupils are working on, or start a new task.</p>
            </div>
            <div className="row-actions" style={{ marginTop: 0 }}>
              <Segmented
                value={taskFilter}
                onChange={setTaskFilter}
                options={[
                  { value: "active", label: "Active" },
                  { value: "draft", label: "Drafts" },
                  { value: "closed", label: "Closed" },
                ]}
              />
              <button
                type="button"
                className="btn btn-primary"
                onClick={() => {
                  setComposerOpen((open) => !open);
                  setPromptDraft(null);
                  setPreviousInstruction(null);
                }}
              >
                {composerOpen ? "Close composer" : "New writing task"}
              </button>
            </div>
          </section>

          {composerOpen ? (
            <section className="task-composer">
              <form
                className="panel form-grid"
                onSubmit={(event) => {
                  event.preventDefault();
                  setPublishConfirmOpen(true);
                }}
              >
                <div className="panel-header">
                  <div>
                    <h2 className="panel-title">New writing task</h2>
                    <p className="panel-subtitle">Nothing reaches pupils until you publish it to a class.</p>
                  </div>
                  <span className="badge-soft">{taskForm.level}</span>
                </div>

                <fieldset className="composer-group">
                  <legend>What pupils write</legend>
                  <div className="field">
                    <label htmlFor="task-title">Title</label>
                    <div className="field-with-action">
                      <input
                        id="task-title"
                        className="input"
                        value={taskForm.title}
                        onChange={(event) => setTaskForm({ ...taskForm, title: event.target.value })}
                      />
                      <button
                        type="button"
                        className="btn btn-secondary"
                        disabled={promptBusy}
                        onClick={() => setAiAssistOpen((open) => !open)}
                      >
                        {promptBusy ? "Drafting…" : "Ask Pip to draft"}
                      </button>
                    </div>
                  </div>

                  {aiAssistOpen ? (
                    <div className="ai-assist-panel">
                      <div className="field">
                        <label htmlFor="teaching-focus">What should pupils practise?</label>
                        <textarea
                          id="teaching-focus"
                          className="textarea"
                          rows={2}
                          value={teachingFocus}
                          onChange={(event) => setTeachingFocus(event.target.value)}
                        />
                      </div>
                      <p className="panel-subtitle">
                        Pip uses the year level, mode, word range and rubric you set below.
                      </p>
                      <div className="row-actions" style={{ marginTop: 12 }}>
                        <button
                          type="button"
                          className="btn btn-dark"
                          disabled={promptBusy || !taskForm.rubric_id}
                          onClick={() => void onGeneratePromptDraft()}
                        >
                          {promptBusy ? "Drafting…" : "Draft it"}
                        </button>
                        <button type="button" className="btn btn-ghost" onClick={() => setAiAssistOpen(false)}>
                          Cancel
                        </button>
                      </div>
                      {!taskForm.rubric_id ? (
                        <p className="empty-state" style={{ marginTop: 12 }}>Choose a rubric below first.</p>
                      ) : null}
                    </div>
                  ) : null}

                  <div className="field">
                    <label htmlFor="task-instruction">Writing instruction</label>
                    <textarea
                      id="task-instruction"
                      className="textarea"
                      value={taskForm.instruction}
                      onChange={(event) => setTaskForm({ ...taskForm, instruction: event.target.value })}
                    />
                  </div>

                  {promptDraft && previousInstruction ? (
                    <div className="ai-draft-note">
                      <span className="badge-soft">Drafted by Pip</span>
                      <div className="lesson-focus-list">
                        {promptDraft.focus.map((item) => <span key={item}>{item}</span>)}
                      </div>
                      <button
                        type="button"
                        className="btn btn-ghost"
                        onClick={() => {
                          setTaskForm((current) => ({
                            ...current,
                            title: previousInstruction.title,
                            instruction: previousInstruction.instruction,
                          }));
                          setPromptDraft(null);
                          setPreviousInstruction(null);
                          showToast("Reverted to your previous wording.");
                        }}
                      >
                        Undo Pip’s draft
                      </button>
                    </div>
                  ) : null}
                </fieldset>

                <fieldset className="composer-group">
                  <legend>How it is marked</legend>
                  <div className="grid-2">
                    <div className="field">
                      <label htmlFor="task-rubric">Rubric</label>
                      <select
                        id="task-rubric"
                        className="select"
                        value={taskForm.rubric_id}
                        onChange={(event) => setTaskForm({ ...taskForm, rubric_id: event.target.value })}
                      >
                        <option value="">Select rubric</option>
                        {state.rubrics.map((rubric) => (
                          <option key={rubric.id} value={rubric.id}>{rubric.title}</option>
                        ))}
                      </select>
                      <button
                        type="button"
                        className="btn btn-ghost"
                        onClick={() => setRubricFormOpen((open) => !open)}
                      >
                        {rubricFormOpen ? "Cancel new rubric" : "+ New rubric"}
                      </button>
                    </div>
                    <div className="field">
                      <label htmlFor="word-min">Word range</label>
                      <div className="range-row">
                        <input
                          id="word-min"
                          className="input"
                          type="number"
                          min={1}
                          max={2000}
                          inputMode="numeric"
                          value={taskForm.word_minimum}
                          onChange={(event) => setTaskForm({ ...taskForm, word_minimum: event.target.value })}
                        />
                        <span aria-hidden="true">–</span>
                        <input
                          id="word-max"
                          className="input"
                          type="number"
                          min={1}
                          max={2000}
                          inputMode="numeric"
                          aria-label="Maximum words"
                          value={taskForm.word_maximum}
                          onChange={(event) => setTaskForm({ ...taskForm, word_maximum: event.target.value })}
                        />
                      </div>
                      {wordRangeError ? <p className="notice-error" style={{ marginTop: 8 }}>{wordRangeError}</p> : null}
                    </div>
                  </div>

                  {rubricFormOpen ? (
                    <div className="ai-assist-panel">
                      <div className="grid-2">
                        <div className="field">
                          <label htmlFor="rubric-title">New rubric name</label>
                          <input
                            id="rubric-title"
                            className="input"
                            value={rubricForm.title}
                            onChange={(event) => setRubricForm({ ...rubricForm, title: event.target.value })}
                          />
                        </div>
                        <div className="field">
                          <label htmlFor="rubric-level">Year level</label>
                          <select
                            id="rubric-level"
                            className="select"
                            value={rubricForm.level}
                            onChange={(event) => setRubricForm({ ...rubricForm, level: event.target.value })}
                          >
                            <option>P4</option>
                            <option>P5</option>
                            <option>P6</option>
                          </select>
                        </div>
                      </div>
                      <div className="grid-3">
                        {defaultDimensions.map((dimension) => (
                          <div key={dimension.name} className="rubric-item">
                            <strong>{dimension.name}</strong>
                            <p className="panel-subtitle">0-{dimension.max_score} points</p>
                          </div>
                        ))}
                      </div>
                      <button
                        type="button"
                        className="btn btn-secondary"
                        onClick={() => {
                          void onCreateRubricDirect();
                        }}
                      >
                        Create rubric
                      </button>
                    </div>
                  ) : null}
                </fieldset>

                <fieldset className="composer-group">
                  <legend>Who and when</legend>
                  <div className="grid-2">
                    <div className="field">
                      <label htmlFor="task-level">Year level</label>
                      <select
                        id="task-level"
                        className="select"
                        value={taskForm.level}
                        onChange={(event) => {
                          const level = event.target.value;
                          const matchingClass = state.classes.find((schoolClass) => schoolClass.level === level);
                          setTaskForm({ ...taskForm, level });
                          setAssignmentForm((current) => ({ ...current, class_id: matchingClass?.id ?? "" }));
                        }}
                      >
                        <option>P4</option>
                        <option>P5</option>
                        <option>P6</option>
                      </select>
                    </div>
                    <div className="field">
                      <label htmlFor="assignment-class">Publish to class</label>
                      <select
                        id="assignment-class"
                        className="select"
                        value={assignmentForm.class_id}
                        onChange={(event) => setAssignmentForm({ ...assignmentForm, class_id: event.target.value })}
                      >
                        <option value="">Select class</option>
                        {state.classes
                          .filter((schoolClass) => schoolClass.level === taskForm.level)
                          .map((schoolClass) => (
                            <option key={schoolClass.id} value={schoolClass.id}>{schoolClass.name}</option>
                          ))}
                      </select>
                    </div>
                    <div className="field">
                      <label htmlFor="task-mode">Mode</label>
                      <select
                        id="task-mode"
                        className="select"
                        value={taskForm.mode}
                        onChange={(event) => setTaskForm({ ...taskForm, mode: event.target.value as "PRACTICE" | "EXAM" })}
                      >
                        <option value="PRACTICE">Practice Mode</option>
                        <option value="EXAM">Exam Mode</option>
                      </select>
                    </div>
                    <div className="field">
                      <label htmlFor="task-due">Due date</label>
                      <input
                        id="task-due"
                        className="input"
                        type="datetime-local"
                        value={taskForm.due_at}
                        onChange={(event) => setTaskForm({ ...taskForm, due_at: event.target.value })}
                      />
                    </div>
                    {taskForm.mode === "EXAM" ? (
                      <div className="field">
                        <label htmlFor="exam-minutes">Exam duration (minutes)</label>
                        <input
                          id="exam-minutes"
                          className="input"
                          type="number"
                          min={5}
                          max={180}
                          inputMode="numeric"
                          value={taskForm.exam_duration_minutes}
                          onChange={(event) => setTaskForm({ ...taskForm, exam_duration_minutes: event.target.value })}
                        />
                      </div>
                    ) : null}
                  </div>
                </fieldset>

                <div className="row-actions" style={{ marginTop: 0 }}>
                  <button
                    className="btn btn-primary"
                    type="submit"
                    disabled={!canPublishTask}
                  >
                    Publish to {selectedClass?.name ?? "class"}
                  </button>
                  <button
                    type="button"
                    className="btn btn-secondary"
                    disabled={!taskForm.rubric_id || Boolean(wordRangeError)}
                    onClick={() => void saveTaskAndClose("DRAFT")}
                  >
                    Save draft
                  </button>
                </div>
                {!taskForm.rubric_id ? <p className="empty-state">Choose a rubric before publishing.</p> : null}
                {taskForm.rubric_id && !assignmentForm.class_id ? (
                  <p className="empty-state">Choose a class before publishing.</p>
                ) : null}
              </form>
            </section>
          ) : null}

          <section className="panel">
            <div className="panel-header">
              <div>
                <h2 className="panel-title">Current writing tasks</h2>
                <p className="panel-subtitle">Work by status instead of mixing drafts, live work, and closed tasks.</p>
              </div>
              <span className="badge-soft">{filteredTasks.length} of {state.tasks.length}</span>
            </div>
            <div className="task-grid">
              {filteredTasks.map((task) => (
                <article key={task.id} className={`task-card ${task.status === "PUBLISHED" ? "featured" : ""}`}>
                  {task.image_url ? <img className="task-card-image" src={authenticatedMediaUrl(task.image_url) ?? undefined} alt={`Illustration for ${task.title}`} /> : null}
                  <div className="task-meta">
                    <span className={task.mode === "EXAM" ? "badge-warning" : "badge"}>{task.mode === "EXAM" ? "Exam" : "Practice"}</span>
                    <span className={statusBadge(task.status)}>{task.status}</span>
                    <span className="badge-soft">{task.assigned_classes.join(", ") || "Unassigned"}</span>
                  </div>
                  <h3 className="panel-title">{task.title}</h3>
                  <p className="panel-subtitle">{task.level} - {words(task)} - {formatDate(task.due_at)}</p>
                  <div className="task-card-actions">
                    {task.status === "DRAFT" ? (
                      <button type="button" className="btn btn-dark" onClick={() => void onChangeTaskStatus(task, "PUBLISHED")}>
                        Publish
                      </button>
                    ) : state.capabilities.features.image_generation ? (
                      <button type="button" className="btn btn-secondary" disabled={imageBusyTaskId === task.id} onClick={() => void onGenerateTaskImage(task)}>
                        {imageBusyTaskId === task.id ? "Drawing…" : task.image_url ? "Regenerate picture" : "Generate picture"}
                      </button>
                    ) : (
                      <span className="feature-lock">◇ Prompt pictures · Pro</span>
                    )}

                    <div className="task-card-menu">
                      <button
                        type="button"
                        className="btn btn-ghost"
                        aria-haspopup="menu"
                        aria-expanded={openTaskMenuId === task.id}
                        aria-label={`More actions for ${task.title}`}
                        onClick={() => setOpenTaskMenuId((current) => (current === task.id ? null : task.id))}
                      >
                        ⋯
                      </button>
                      {openTaskMenuId === task.id ? (
                        <div className="task-card-menu-list" role="menu">
                          {task.status === "PUBLISHED" && state.capabilities.features.image_generation ? (
                            <button type="button" role="menuitem" disabled={imageBusyTaskId === task.id} onClick={() => { setOpenTaskMenuId(null); void onGenerateTaskImage(task); }}>
                              {task.image_url ? "Regenerate picture" : "Generate picture"}
                            </button>
                          ) : null}
                          {task.status === "PUBLISHED" ? (
                            <button type="button" role="menuitem" onClick={() => { setOpenTaskMenuId(null); void onChangeTaskStatus(task, "CLOSED"); }}>
                              Close to new submissions
                            </button>
                          ) : null}
                          {task.status !== "ARCHIVED" ? (
                            <button
                              type="button"
                              role="menuitem"
                              className="menu-danger"
                              onClick={() => {
                                setOpenTaskMenuId(null);
                                if (window.confirm(`Archive “${task.title}”? Pupils will no longer see it.`)) {
                                  void onChangeTaskStatus(task, "ARCHIVED");
                                }
                              }}
                            >
                              Archive
                            </button>
                          ) : null}
                        </div>
                      ) : null}
                    </div>
                  </div>
                </article>
              ))}
              {filteredTasks.length === 0 ? <p className="empty-state">No tasks match this status.</p> : null}
            </div>
          </section>

          <div className={`modal-backdrop ${publishConfirmOpen ? "open" : ""}`} role="dialog" aria-modal="true" aria-labelledby="publish-title">
            <div className="modal">
              <p className="eyebrow">Before pupils see it</p>
              <h2 className="panel-title" id="publish-title" style={{ fontSize: "var(--text-xl)", marginTop: 8 }}>
                Publish this task to {selectedClass?.name ?? "the class"}?
              </h2>
              <dl className="publish-summary">
                <div><dt>Task</dt><dd>{taskForm.title || "Untitled"}</dd></div>
                <div><dt>Class</dt><dd>{selectedClass?.name ?? "—"}</dd></div>
                <div><dt>Mode</dt><dd>{taskForm.mode === "EXAM" ? `Exam · ${taskForm.exam_duration_minutes || 30} min` : "Practice"}</dd></div>
                <div><dt>Words</dt><dd>{taskForm.word_minimum}–{taskForm.word_maximum}</dd></div>
                <div><dt>Due</dt><dd>{taskForm.due_at ? new Date(taskForm.due_at).toLocaleString() : "No due date"}</dd></div>
              </dl>
              <div className="row-actions">
                <button className="btn btn-secondary" type="button" onClick={() => setPublishConfirmOpen(false)}>
                  Keep editing
                </button>
                <button
                  className="btn btn-primary"
                  type="button"
                  onClick={() => {
                    setPublishConfirmOpen(false);
                    void saveTaskAndClose("PUBLISHED");
                  }}
                >
                  Publish now
                </button>
              </div>
            </div>
          </div>
        </>
      ) : null}

      {screen === "reports" ? (
        <div className="report-studio">
          <section className="report-heading">
            <div className="report-heading-copy">
              <p className="eyebrow">Class writing picture</p>
              <h2>See the class, then choose the next teaching move.</h2>
              <p>Completion, rubric scores, recurring needs, and student-level evidence are kept together in one readable report.</p>
            </div>
            <div className="report-filters" aria-label="Report scope">
              <div className="field">
                <label htmlFor="report-class">Class</label>
                <select id="report-class" className="select" value={reportClassId} onChange={(event) => {
                  setReportClassId(event.target.value);
                  setClassReport(null);
                  setReportExports([]);
                }}>
                  {state.classes.map((schoolClass) => (
                    <option key={schoolClass.id} value={schoolClass.id}>{schoolClass.name}</option>
                  ))}
                </select>
              </div>
              <div className="field">
                <label htmlFor="report-task">Writing task</label>
                <select id="report-task" className="select" value={reportTaskId} onChange={(event) => {
                  setReportTaskId(event.target.value);
                  setClassReport(null);
                }}>
                  <option value="">All assigned writing</option>
                  {state.tasks.map((task) => (
                    <option key={task.id} value={task.id}>{task.title}</option>
                  ))}
                </select>
              </div>
              <button className="btn btn-secondary" type="button" disabled={!reportClassId || reportBusy} onClick={() => void onPreviewReport()}>
                Refresh data
              </button>
              <button className="btn btn-dark" data-testid="report-generate" type="button" disabled={!reportClassId || reportBusy} onClick={() => void onGenerateReport()}>
                {reportBusy ? "Updating..." : "Save report"}
              </button>
            </div>
          </section>

          <section className="report-status-line" role="status" aria-live="polite">
            <span className={`state-dot ${reportBusy ? "loading" : classReport ? "ready" : "empty"}`} aria-hidden="true" />
            <span>
              <strong>{reportBusy ? "Building the class picture" : classReport ? `${classReport.class_report.class_name} report ready` : "Choose a class to begin"}</strong>
              {classReport?.class_report.generated_at
                ? ` · Saved ${new Date(classReport.class_report.generated_at).toLocaleString()}`
                : ` · ${reportTaskTitle}`}
            </span>
          </section>

          <section className="report-summary" aria-label="Report summary">
            <div className="report-primary-metric">
              <p className="micro-label">Completion</p>
              <strong>{classReport ? `${Math.round(classReport.summary.completion_rate * 100)}%` : "—"}</strong>
              <div className="report-completion-track"><span style={{ width: classReport ? `${Math.round(classReport.summary.completion_rate * 100)}%` : "0%" }} /></div>
              <p>{classReport ? `${classReport.summary.submitted_count} of ${classReport.summary.expected_submissions} expected submissions received` : "Load a report to see class progress"}</p>
            </div>
            <div className="report-summary-list">
              <Metric label="Pupils" value={classReport?.summary.student_count ?? "—"} note="In this class" />
              <Metric
                label="Average"
                value={classReport?.summary.average_total_score
                  ?? (classReport?.summary.average_total_percentage !== null
                    && classReport?.summary.average_total_percentage !== undefined
                    ? `${classReport.summary.average_total_percentage}%`
                    : "—")}
                note={classReport?.summary.maximum_total_score
                  ? `Out of ${classReport.summary.maximum_total_score}`
                  : "Normalised across rubrics"}
              />
              <Metric label="Reviewed" value={classReport?.summary.scored_submission_count ?? "—"} note="With a score" />
              <Metric label="Tasks" value={classReport?.summary.assigned_task_count ?? "—"} note={reportTaskId ? "Selected task" : "In report scope"} />
            </div>
          </section>

          <section className="report-analysis" data-testid={classReport ? "report-result" : undefined}>
            <article className="report-paper">
              <div className="report-section-heading">
                <div>
                  <p className="micro-label">Learning quality</p>
                  <h2>Rubric breakdown</h2>
                </div>
                <span>{reportTaskTitle}</span>
              </div>
              {classReport ? (
                <>
                  <div className="rubric-average-list">
                    {reportRubricRows.map((row) => (
                      <div key={row.label} className="rubric-average-row">
                        <div>
                          <strong>{row.label}</strong>
                          <span>
                            {row.value !== null && row.maximum !== null
                              ? `${row.value} / ${row.maximum}`
                              : row.percentage !== null
                                ? `${row.percentage}%`
                                : "—"}
                          </span>
                        </div>
                        <div className="rubric-average-track">
                          <span
                            className={row.colour}
                            style={{
                              width: row.value !== null && row.maximum !== null
                                ? scorePercent(row.value, row.maximum)
                                : scorePercent(row.percentage, 100),
                            }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                  <div className="report-section-heading report-section-heading-compact">
                    <div>
                      <p className="micro-label">Score spread</p>
                      <h3>How results are distributed</h3>
                    </div>
                  </div>
                  <div className="chart-bars">
                    {Object.entries(classReport.score_distribution).map(([bucket, count]) => (
                      <div key={bucket} className={bucket === "unscored" ? "chart-bar muted" : "chart-bar"}>
                        <strong>{count}</strong>
                        <span style={{ height: `${Math.max(12, Math.round((count / reportDistributionMax) * 100))}%` }} />
                        <small>{bucket}</small>
                      </div>
                    ))}
                  </div>
                </>
              ) : (
                <p className="empty-state">Select a class and refresh the report to see rubric patterns.</p>
              )}
            </article>

            <aside className="report-teaching-plan">
              <div className="report-section-heading">
                <div>
                  <p className="micro-label">Teacher action plan</p>
                  <h2>Common weaknesses</h2>
                </div>
              </div>
              <p className="report-intro">Turn the strongest class pattern into a whole-class mini-lesson, then use the others for small-group practice.</p>
              <div className="teaching-priority-list">
                {(classReport?.common_weaknesses ?? []).slice(0, 3).map((item, index) => (
                  <div key={item.weakness} className={index === 0 ? "teaching-priority primary" : "teaching-priority"}>
                    <span>{index + 1}</span>
                    <div>
                      <strong>{item.weakness}</strong>
                      <p>{item.count} {item.count === 1 ? "pupil" : "pupils"} showed this pattern.</p>
                      <small>{index === 0 ? "Whole-class mini-lesson" : "Small-group rewrite practice"}</small>
                    </div>
                  </div>
                ))}
                {classReport && classReport.common_weaknesses.length === 0 ? (
                  <div className="teaching-priority primary">
                    <span>1</span>
                    <div><strong>No repeated need yet</strong><p>More teacher-reviewed writing is needed before a class pattern is reliable.</p></div>
                  </div>
                ) : null}
                {!classReport ? <p className="empty-state">Teaching priorities appear after the class report loads.</p> : null}
              </div>
            </aside>
          </section>

          <section className="report-student-section">
            <div className="report-section-heading">
              <div>
                <p className="micro-label">Student evidence</p>
                <h2>Writing overview</h2>
                <p>Scan who has submitted, who needs follow-up, and which work is ready for feedback.</p>
              </div>
              <span>{classReport?.completion_rows.length ?? 0} records</span>
            </div>
            <div className="table-shell report-table-shell">
              <table className="table report-table">
                <thead><tr><th>Pupil</th><th>Writing task</th><th>Words</th><th>Score</th><th>Status</th></tr></thead>
                <tbody>
                  {reportRows.map((row) => (
                    <tr key={`${row.student_id}-${row.task_id}`}>
                      <td><strong>{row.student_name}</strong><br /><span>{row.student_number}</span></td>
                      <td>{row.task_title}<br /><span>{row.mode === "EXAM" ? "Exam" : "Practice"}</span></td>
                      <td>{row.word_count ?? "—"}</td>
                      <td>
                        <strong>{row.total_score ?? "—"}</strong>
                        {row.total_score !== null ? ` / ${row.total_max_score}` : ""}
                      </td>
                      <td><span className={row.submitted ? (row.review_status === "RELEASED" ? "badge-success" : "badge-warning") : "badge-soft"}>{row.submitted ? (row.review_status === "RELEASED" ? "Returned" : "In review") : "Not submitted"}</span></td>
                    </tr>
                  ))}
                  {reportRows.length === 0 ? <tr><td colSpan={5}>No student writing is available for this report scope.</td></tr> : null}
                </tbody>
              </table>
            </div>
          </section>

          <section className="report-export-panel">
            <div className="report-export-copy">
              <p className="micro-label">Ready to share</p>
              <h2>Export a report people can actually read.</h2>
              <p>PDF is designed for review meetings and school records. CSV keeps every student row ready for analysis.</p>
              {lastExport ? <p className="report-last-export"><strong>Downloaded:</strong> {lastExport.filename} · {Math.max(1, Math.ceil(lastExport.bytes / 1024))} KB</p> : null}
              <div className="report-export-actions">
                <button className="btn btn-secondary" data-testid="report-export-csv" type="button" disabled={!reportClassId || reportBusy} onClick={() => void onDownloadReport("csv")}>Download CSV</button>
                <button className="btn btn-primary" data-testid="report-export-pdf" type="button" disabled={!reportClassId || reportBusy} onClick={() => void onDownloadReport("pdf")}>Download presentation PDF</button>
              </div>
            </div>
            <div className="report-export-history">
              <div>
                <p className="micro-label">Recent exports</p>
                <h3>Audit trail</h3>
              </div>
              {reportExports.slice(0, 4).map((entry) => (
                <div key={entry.id} className="report-export-row">
                  <strong>{entry.format.toUpperCase()} report</strong>
                  <span>{new Date(entry.created_at).toLocaleString()}</span>
                </div>
              ))}
              {reportExports.length === 0 ? <p className="empty-state">Export history will appear here after the first download.</p> : null}
            </div>
          </section>
        </div>
      ) : null}

      {screen === "pupils" ? (
        <div className="pupil-roster-page">
          <section className="pupil-roster-intro">
            <div>
              <p className="micro-label">Teacher-managed access</p>
              <h2>Give each pupil one clear way in.</h2>
              <p>Create the account here, choose the class, then share the temporary password privately. There is no public pupil registration page.</p>
            </div>
            <aside>
              <span className="badge-soft">Next integration</span>
              <strong>Google Classroom import</strong>
              <p>Planned after the demo; it needs school Google approval and OAuth setup.</p>
            </aside>
          </section>

          <section className="pupil-roster-layout">
            <form className="panel form-grid pupil-create-card" onSubmit={onCreatePupil}>
              <div className="panel-header">
                <div>
                  <p className="micro-label">New pupil sign-in</p>
                  <h2 className="panel-title">Add a pupil</h2>
                  <p className="panel-subtitle">The password is sent only to the authentication service and is never shown again.</p>
                </div>
              </div>
              <div className="field">
                <label htmlFor="pupil-name">Pupil name</label>
                <input id="pupil-name" className="input" value={pupilForm.display_name} onChange={(event) => setPupilForm({ ...pupilForm, display_name: event.target.value })} required minLength={2} />
              </div>
              <div className="field">
                <label htmlFor="pupil-email">School email</label>
                <input id="pupil-email" className="input" type="email" value={pupilForm.email} onChange={(event) => setPupilForm({ ...pupilForm, email: event.target.value })} required />
              </div>
              <div className="grid-2">
                <div className="field">
                  <label htmlFor="pupil-class">Class</label>
                  <select id="pupil-class" className="select" value={pupilForm.class_id} onChange={(event) => setPupilForm({ ...pupilForm, class_id: event.target.value })} required>
                    {state.classes.map((schoolClass) => <option key={schoolClass.id} value={schoolClass.id}>{schoolClass.name}</option>)}
                  </select>
                </div>
                <div className="field">
                  <label htmlFor="pupil-number">Student number <span className="micro-label">optional</span></label>
                  <input id="pupil-number" className="input" value={pupilForm.student_number} onChange={(event) => setPupilForm({ ...pupilForm, student_number: event.target.value })} />
                </div>
              </div>
              <div className="field">
                <label htmlFor="pupil-password">Temporary password</label>
                <input id="pupil-password" className="input" type="password" autoComplete="new-password" value={pupilForm.temporary_password} onChange={(event) => setPupilForm({ ...pupilForm, temporary_password: event.target.value })} required minLength={8} />
                <small>Use at least 8 characters and share it privately with the pupil.</small>
              </div>
              <button className="btn btn-primary" type="submit" disabled={pupilBusy || !pupilForm.class_id}>{pupilBusy ? "Creating sign-in…" : "Create pupil sign-in"}</button>
            </form>

            <section className="panel pupil-roster-card">
              <div className="panel-header">
                <div><p className="micro-label">Your classes</p><h2 className="panel-title">Pupil roster</h2><p className="panel-subtitle">Accounts in classes assigned to you.</p></div>
                <span className="badge-soft">{state.students.length} {state.students.length === 1 ? "pupil" : "pupils"}</span>
              </div>
              <div className="pupil-roster-list">
                {state.students.map((student) => (
                  <article key={student.id}>
                    <span className="pupil-avatar">{student.display_name.split(/\s+/).map((part) => part[0]).join("").slice(0, 2).toUpperCase()}</span>
                    <div><strong>{student.display_name}</strong><p>{student.email}</p><small>{student.student_number}</small></div>
                    <span className="badge-soft">{student.class_name}</span>
                    <span className={statusBadge(student.status)}>{student.status === "ACTIVE" ? "Can sign in" : student.status}</span>
                  </article>
                ))}
                {state.students.length === 0 ? <p className="empty-state">No pupils are connected to your classes yet.</p> : null}
              </div>
            </section>
          </section>
        </div>
      ) : null}

      <ReleaseModal
        open={Boolean(releaseTarget)}
        onCancel={() => setReleaseTarget(null)}
        onConfirm={() => releaseTarget && void onReleaseFeedback(releaseTarget)}
      />
      <div className={`toast ${toast ? "show" : ""}`} role="status" aria-live="polite">{toast}</div>
    </AppShell>
  );
}

export function TeacherDashboard() {
  return <TeacherWorkspace screen="marking" />;
}
