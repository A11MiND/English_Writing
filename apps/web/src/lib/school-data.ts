import type {
  AdminUser,
  AccountCapabilities,
  AiSettings,
  AiServiceStatus,
  ApiResponse,
  ClassReportPayload,
  GrammarSuggestion,
  ImportRole,
  ImportUserRow,
  ImportUsersPayload,
  ReportExportAudit,
  Rubric,
  SchoolClass,
  StudentProfilePayload,
  TaskAssignment,
  Draft,
  ExamEventType,
  Submission,
  MarkingResult,
  PersonalPracticeFocus,
  PersonalPracticeGenre,
  PersonalPracticeResult,
  PersonalPracticeTask,
  ParagraphCheckPayload,
  PostWritingExercise,
  PromptDraft,
  StudentFeedback,
  StudentRewrite,
  StudentRewriteGoal,
  SuggestionCheckMode,
  SuggestionCheckPayload,
  TeacherDashboardSummary,
  TeacherSubmissionExamEvents,
  TeacherMarkingSubmission,
  TeacherReview,
  TeacherStudent,
  WritingTask,
  WritingWorkspace,
} from "@english-ai-writing/shared";

import { apiBaseUrl } from "./auth";

export type CsvParseResult = {
  rows: ImportUserRow[];
  errors: string[];
};

export type DownloadedReport = {
  filename: string;
  bytes: number;
  content_type: string;
};

const requiredHeaders = ["email", "display_name"];

async function parseApiResponse<T>(response: Response): Promise<ApiResponse<T>> {
  return (await response.json()) as ApiResponse<T>;
}

type ValidationDetail = { loc?: unknown[]; msg?: string };

async function parseApiError(response: Response, fallback: string): Promise<string> {
  try {
    const contentType = response.headers.get("content-type") ?? "";
    if (contentType.includes("application/json")) {
      const body = (await response.json()) as Partial<ApiResponse<unknown>> & { detail?: unknown };
      if (body && "success" in body && body.success === false && body.message) {
        return body.message;
      }
      // A gateway or an older API build can still answer in FastAPI's own shape.
      if (typeof body?.detail === "string") return body.detail;
      if (Array.isArray(body?.detail)) {
        const described = (body.detail as ValidationDetail[])
          .map((item) => {
            const field = (item.loc ?? [])
              .map(String)
              .filter((part) => !["body", "query", "path"].includes(part))
              .join(" → ");
            return field ? `${field}: ${item.msg ?? "is invalid"}` : item.msg ?? "";
          })
          .filter(Boolean);
        if (described.length) return described.slice(0, 5).join("; ");
      }
    }
  } catch {
    // Keep the fallback if the server returned a binary or malformed error body.
  }
  return fallback;
}

function parseCsvLine(line: string): { cells: string[]; error?: string } {
  const cells: string[] = [];
  let current = "";
  let inQuotes = false;

  for (let index = 0; index < line.length; index += 1) {
    const char = line[index];
    const next = line[index + 1];
    if (char === '"') {
      if (inQuotes && next === '"') {
        current += '"';
        index += 1;
        continue;
      }
      inQuotes = !inQuotes;
      continue;
    }
    if (char === "," && !inQuotes) {
      cells.push(current.trim());
      current = "";
      continue;
    }
    current += char;
  }

  if (inQuotes) {
    return { cells: [], error: "contains an unclosed quoted field." };
  }
  cells.push(current.trim());
  return { cells };
}

export function parseUserCsv(csv: string): CsvParseResult {
  const lines = csv
    .split(/\r?\n/)
    .map((line) => line.trimEnd())
    .filter(Boolean);
  if (lines.length < 2) {
    return { rows: [], errors: ["CSV must include a header row and at least one data row."] };
  }

  const headerParse = parseCsvLine(lines[0]);
  if (headerParse.error) {
    return { rows: [], errors: [`Header row ${headerParse.error}`] };
  }
  const headers = headerParse.cells.map((header) => header.trim());
  const missingHeaders = requiredHeaders.filter((header) => !headers.includes(header));
  if (missingHeaders.length > 0) {
    return { rows: [], errors: [`Missing required headers: ${missingHeaders.join(", ")}.`] };
  }

  const rows: ImportUserRow[] = [];
  const errors: string[] = [];
  for (const [offset, line] of lines.slice(1).entries()) {
    const rowNumber = offset + 2;
    const parsedLine = parseCsvLine(line);
    if (parsedLine.error) {
      errors.push(`Row ${rowNumber} ${parsedLine.error}`);
      continue;
    }
    const cells = parsedLine.cells;
    if (cells.length > headers.length) {
      errors.push(`Row ${rowNumber} has ${cells.length} columns but header has ${headers.length}.`);
      continue;
    }
    const row = Object.fromEntries(headers.map((header, index) => [header, cells[index] || ""]));
    if (!row.email || !row.display_name) {
      errors.push(`Row ${rowNumber} requires email and display_name.`);
      continue;
    }
    rows.push({
      external_user_id: row.external_user_id || undefined,
      email: row.email,
      display_name: row.display_name,
      student_number: row.student_number || undefined,
      level: row.level || undefined,
      class_name: row.class_name || undefined,
      staff_code: row.staff_code || undefined,
    });
  }

  return { rows, errors };
}

export async function listClasses(): Promise<SchoolClass[]> {
  const response = await fetch(`${apiBaseUrl}/api/admin/classes`, {
    credentials: "include",
    cache: "no-store",
  });
  const body = await parseApiResponse<{ classes: SchoolClass[] }>(response);
  if (!body.success) throw new Error(body.message);
  return body.data.classes;
}

export async function createClass(payload: {
  name: string;
  level: string;
  academic_year: string;
}): Promise<SchoolClass> {
  const response = await fetch(`${apiBaseUrl}/api/admin/classes`, {
    method: "POST",
    credentials: "include",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(payload),
  });
  const body = await parseApiResponse<{ class: SchoolClass }>(response);
  if (!body.success) throw new Error(body.message);
  return body.data.class;
}

export async function listUsers(): Promise<AdminUser[]> {
  const response = await fetch(`${apiBaseUrl}/api/admin/users`, {
    credentials: "include",
    cache: "no-store",
  });
  const body = await parseApiResponse<{ users: AdminUser[] }>(response);
  if (!body.success) throw new Error(body.message);
  return body.data.users;
}

export async function getAiServiceStatus(): Promise<AiServiceStatus> {
  const response = await fetch(`${apiBaseUrl}/api/admin/ai/status`, {
    credentials: "include",
    cache: "no-store",
  });
  const body = await parseApiResponse<AiServiceStatus>(response);
  if (!body.success) throw new Error(body.message);
  return body.data;
}

export async function getAiSettings(): Promise<AiSettings> {
  const response = await fetch(`${apiBaseUrl}/api/admin/ai/settings`, {
    credentials: "include",
    cache: "no-store",
  });
  const body = await parseApiResponse<AiSettings>(response);
  if (!body.success) throw new Error(body.message);
  return body.data;
}

export async function updateAiSettings(payload: {
  provider: string;
  model?: string | null;
  base_url?: string | null;
  api_key?: string | null;
  clear_api_key?: boolean;
  timeout_seconds: number;
}): Promise<AiSettings> {
  const response = await fetch(`${apiBaseUrl}/api/admin/ai/settings`, {
    method: "PATCH",
    credentials: "include",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(payload),
  });
  const body = await parseApiResponse<AiSettings>(response);
  if (!body.success) throw new Error(body.message);
  return body.data;
}

export async function testAiConnection(): Promise<{
  ok: boolean;
  provider: string;
  model: string;
  message: string;
}> {
  const response = await fetch(`${apiBaseUrl}/api/admin/ai/test`, {
    method: "POST",
    credentials: "include",
  });
  const body = await parseApiResponse<{
    ok: boolean;
    provider: string;
    model: string;
    message: string;
  }>(response);
  if (!body.success) throw new Error(body.message);
  return body.data;
}

export async function updateUserStatus(
  userId: string,
  status: "ACTIVE" | "SUSPENDED" | "ARCHIVED",
): Promise<Pick<AdminUser, "id" | "email" | "display_name" | "role" | "status">> {
  const response = await fetch(`${apiBaseUrl}/api/admin/users/${userId}/status`, {
    method: "PATCH",
    credentials: "include",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ status }),
  });
  const body = await parseApiResponse<{
    user: Pick<AdminUser, "id" | "email" | "display_name" | "role" | "status">;
  }>(response);
  if (!body.success) throw new Error(body.message);
  return body.data.user;
}

export async function importUsers(
  role: ImportRole,
  rows: ImportUserRow[],
): Promise<ImportUsersPayload> {
  const response = await fetch(`${apiBaseUrl}/api/admin/import/users`, {
    method: "POST",
    credentials: "include",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ role, rows }),
  });
  const body = await parseApiResponse<ImportUsersPayload>(response);
  if (!body.success) throw new Error(body.message);
  return body.data;
}

export async function listTeacherClasses(): Promise<SchoolClass[]> {
  const response = await fetch(`${apiBaseUrl}/api/teacher/classes`, {
    credentials: "include",
    cache: "no-store",
  });
  const body = await parseApiResponse<{ classes: SchoolClass[] }>(response);
  if (!body.success) throw new Error(body.message);
  return body.data.classes;
}

export async function getAccountCapabilities(): Promise<AccountCapabilities> {
  const response = await fetch(`${apiBaseUrl}/api/account/capabilities`, {
    credentials: "include",
    cache: "no-store",
  });
  const body = await parseApiResponse<AccountCapabilities>(response);
  if (!body.success) throw new Error(body.message);
  return body.data;
}

export async function listTeacherStudents(): Promise<TeacherStudent[]> {
  const response = await fetch(`${apiBaseUrl}/api/teacher/students`, {
    credentials: "include",
    cache: "no-store",
  });
  const body = await parseApiResponse<{ students: TeacherStudent[] }>(response);
  if (!body.success) throw new Error(body.message);
  return body.data.students;
}

export async function createTeacherStudent(payload: {
  display_name: string;
  email: string;
  temporary_password: string;
  class_id: string;
  student_number?: string;
}): Promise<TeacherStudent> {
  const response = await fetch(`${apiBaseUrl}/api/teacher/students`, {
    method: "POST",
    credentials: "include",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(payload),
  });
  const body = await parseApiResponse<{ student: TeacherStudent }>(response);
  if (!body.success) throw new Error(body.message);
  return body.data.student;
}

export async function getStudentProfile(): Promise<StudentProfilePayload["profile"]> {
  const response = await fetch(`${apiBaseUrl}/api/student/profile`, {
    credentials: "include",
    cache: "no-store",
  });
  const body = await parseApiResponse<StudentProfilePayload>(response);
  if (!body.success) throw new Error(body.message);
  return body.data.profile;
}

export type CreateRubricPayload = {
  title: string;
  level: string;
  total_score: number;
  status: "DRAFT" | "ACTIVE";
  dimensions: {
    name: string;
    min_score: number;
    max_score: number;
    descriptor: string;
    sort_order: number;
  }[];
};

export type CreateTaskPayload = {
  title: string;
  level: string;
  instruction: string;
  genre?: string;
  mode: "PRACTICE" | "EXAM";
  word_minimum?: number;
  word_maximum?: number;
  due_at?: string;
  exam_duration_minutes?: number;
  rubric_id: string;
  status: "DRAFT" | "PUBLISHED";
};

export type UpdateRubricPayload = {
  title?: string;
  level?: string;
  total_score?: number;
  status?: "DRAFT" | "ACTIVE" | "ARCHIVED";
  dimensions?: CreateRubricPayload["dimensions"];
};

export type UpdateTaskPayload = Partial<Omit<CreateTaskPayload, "status">> & {
  status?: "DRAFT" | "PUBLISHED" | "CLOSED" | "ARCHIVED";
};

export async function listTeacherRubrics(): Promise<Rubric[]> {
  const response = await fetch(`${apiBaseUrl}/api/teacher/rubrics`, {
    credentials: "include",
    cache: "no-store",
  });
  const body = await parseApiResponse<{ rubrics: Rubric[] }>(response);
  if (!body.success) throw new Error(body.message);
  return body.data.rubrics;
}

export async function createRubric(payload: CreateRubricPayload): Promise<Rubric> {
  const response = await fetch(`${apiBaseUrl}/api/teacher/rubrics`, {
    method: "POST",
    credentials: "include",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(payload),
  });
  const body = await parseApiResponse<{ rubric: Rubric }>(response);
  if (!body.success) throw new Error(body.message);
  return body.data.rubric;
}

export async function updateRubric(
  rubricId: string,
  payload: UpdateRubricPayload,
): Promise<Rubric> {
  const response = await fetch(`${apiBaseUrl}/api/teacher/rubrics/${rubricId}`, {
    method: "PATCH",
    credentials: "include",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(payload),
  });
  const body = await parseApiResponse<{ rubric: Rubric }>(response);
  if (!body.success) throw new Error(body.message);
  return body.data.rubric;
}

export async function duplicateRubric(rubricId: string, title?: string): Promise<Rubric> {
  const response = await fetch(`${apiBaseUrl}/api/teacher/rubrics/${rubricId}/duplicate`, {
    method: "POST",
    credentials: "include",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ title }),
  });
  const body = await parseApiResponse<{ rubric: Rubric }>(response);
  if (!body.success) throw new Error(body.message);
  return body.data.rubric;
}

export async function listTeacherTasks(): Promise<WritingTask[]> {
  const response = await fetch(`${apiBaseUrl}/api/teacher/tasks`, {
    credentials: "include",
    cache: "no-store",
  });
  const body = await parseApiResponse<{ tasks: WritingTask[] }>(response);
  if (!body.success) throw new Error(body.message);
  return body.data.tasks;
}

export async function getTeacherTask(taskId: string): Promise<WritingTask> {
  const response = await fetch(`${apiBaseUrl}/api/teacher/tasks/${taskId}`, {
    credentials: "include",
    cache: "no-store",
  });
  const body = await parseApiResponse<{ task: WritingTask }>(response);
  if (!body.success) throw new Error(body.message);
  return body.data.task;
}

export async function createTask(payload: CreateTaskPayload): Promise<WritingTask> {
  const response = await fetch(`${apiBaseUrl}/api/teacher/tasks`, {
    method: "POST",
    credentials: "include",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(payload),
  });
  const body = await parseApiResponse<{ task: WritingTask }>(response);
  if (!body.success) throw new Error(body.message);
  return body.data.task;
}

export async function updateTask(
  taskId: string,
  payload: UpdateTaskPayload,
): Promise<WritingTask> {
  const response = await fetch(`${apiBaseUrl}/api/teacher/tasks/${taskId}`, {
    method: "PATCH",
    credentials: "include",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(payload),
  });
  const body = await parseApiResponse<{ task: WritingTask }>(response);
  if (!body.success) throw new Error(body.message);
  return body.data.task;
}

export async function generateTaskImage(taskId: string): Promise<string> {
  const response = await fetch(`${apiBaseUrl}/api/teacher/tasks/${taskId}/image`, {
    method: "POST",
    credentials: "include",
  });
  const body = await parseApiResponse<{ image_url: string }>(response);
  if (!body.success) throw new Error(body.message);
  return body.data.image_url;
}

export function authenticatedMediaUrl(path: string | null | undefined): string | null {
  return path ? `${apiBaseUrl}${path}` : null;
}

export async function assignTask(taskId: string, classId: string): Promise<TaskAssignment> {
  const response = await fetch(`${apiBaseUrl}/api/teacher/tasks/${taskId}/assignments`, {
    method: "POST",
    credentials: "include",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ class_id: classId }),
  });
  const body = await parseApiResponse<{ assignment: TaskAssignment }>(response);
  if (!body.success) throw new Error(body.message);
  return body.data.assignment;
}

export async function generatePromptDraft(payload: {
  level: string;
  mode: "PRACTICE" | "EXAM";
  teaching_focus: string;
  word_minimum?: number | null;
  word_maximum?: number | null;
  exam_duration_minutes?: number | null;
  rubric_id: string;
}): Promise<PromptDraft> {
  const response = await fetch(`${apiBaseUrl}/api/teacher/questions/generate`, {
    method: "POST",
    credentials: "include",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(payload),
  });
  const body = await parseApiResponse<{ prompt_draft: PromptDraft }>(response);
  if (!body.success) throw new Error(body.message);
  return body.data.prompt_draft;
}

export async function listStudentTasks(): Promise<WritingTask[]> {
  const response = await fetch(`${apiBaseUrl}/api/student/tasks`, {
    credentials: "include",
    cache: "no-store",
  });
  const body = await parseApiResponse<{ tasks: WritingTask[] }>(response);
  if (!body.success) throw new Error(body.message);
  return body.data.tasks;
}

export async function generatePersonalPractice(payload: {
  focus: PersonalPracticeFocus;
  genre: PersonalPracticeGenre;
  duration_minutes: 10 | 15 | 20;
}): Promise<PersonalPracticeTask> {
  const response = await fetch(`${apiBaseUrl}/api/student/practice/generate`, {
    method: "POST",
    credentials: "include",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(payload),
  });
  const body = await parseApiResponse<{ practice: PersonalPracticeTask }>(response);
  if (!body.success) throw new Error(body.message);
  return body.data.practice;
}

export async function listPersonalPractice(): Promise<PersonalPracticeTask[]> {
  const response = await fetch(`${apiBaseUrl}/api/student/practice`, {
    credentials: "include",
    cache: "no-store",
  });
  const body = await parseApiResponse<{ items: PersonalPracticeTask[] }>(response);
  if (!body.success) throw new Error(body.message);
  return body.data.items;
}

export async function getPersonalPracticeResult(taskId: string): Promise<PersonalPracticeResult> {
  const response = await fetch(`${apiBaseUrl}/api/student/practice/${taskId}/result`, {
    credentials: "include",
    cache: "no-store",
  });
  const body = await parseApiResponse<PersonalPracticeResult>(response);
  if (!body.success) throw new Error(body.message);
  return body.data;
}

export async function rewriteStudentText(payload: {
  task_id: string;
  text: string;
  goal: StudentRewriteGoal;
}): Promise<StudentRewrite> {
  const response = await fetch(`${apiBaseUrl}/api/student/rewrite`, {
    method: "POST",
    credentials: "include",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(payload),
  });
  const body = await parseApiResponse<{ rewrite: StudentRewrite }>(response);
  if (!body.success) throw new Error(body.message);
  return body.data.rewrite;
}

export function countWords(text: string): number {
  return text.trim().split(/\s+/).filter(Boolean).length;
}

export async function getWritingWorkspace(taskId: string): Promise<WritingWorkspace> {
  const response = await fetch(`${apiBaseUrl}/api/student/tasks/${taskId}/writing`, {
    credentials: "include",
    cache: "no-store",
  });
  const body = await parseApiResponse<WritingWorkspace>(response);
  if (!body.success) throw new Error(body.message);
  return body.data;
}

export async function saveDraft(
  taskId: string,
  payload: { content_html: string; content_text: string; word_count: number },
): Promise<Draft> {
  const response = await fetch(`${apiBaseUrl}/api/student/tasks/${taskId}/draft`, {
    method: "PUT",
    credentials: "include",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(payload),
  });
  const body = await parseApiResponse<{ draft: Draft }>(response);
  if (!body.success) throw new Error(body.message);
  return body.data.draft;
}

export async function submitWriting(
  taskId: string,
  payload: {
    content_html: string;
    content_text: string;
    word_count: number;
    submission_trigger?: "MANUAL" | "TIMER";
  },
): Promise<Submission> {
  const response = await fetch(`${apiBaseUrl}/api/student/tasks/${taskId}/submit`, {
    method: "POST",
    credentials: "include",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(payload),
  });
  const body = await parseApiResponse<{ submission: Submission; locked: boolean }>(response);
  if (!body.success) throw new Error(body.message);
  return body.data.submission;
}

export async function recordExamEvent(
  taskId: string,
  eventType: ExamEventType,
  metadata: Record<string, unknown> = {},
): Promise<void> {
  const response = await fetch(`${apiBaseUrl}/api/student/tasks/${taskId}/exam-events`, {
    method: "POST",
    credentials: "include",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ event_type: eventType, metadata }),
  });
  const body = await parseApiResponse<{ event: { id: string } }>(response);
  if (!body.success) throw new Error(body.message);
}

export async function listTeacherSubmissionExamEvents(
  submissionId: string,
): Promise<TeacherSubmissionExamEvents> {
  const response = await fetch(`${apiBaseUrl}/api/teacher/submissions/${submissionId}/exam-events`, {
    credentials: "include",
    cache: "no-store",
  });
  const body = await parseApiResponse<TeacherSubmissionExamEvents>(response);
  if (!body.success) throw new Error(body.message);
  return body.data;
}

export async function checkWritingSuggestions(
  taskId: string,
  text: string,
  checkMode: SuggestionCheckMode = "CHANGED",
): Promise<SuggestionCheckPayload> {
  const response = await fetch(`${apiBaseUrl}/api/suggestions/check`, {
    method: "POST",
    credentials: "include",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ task_id: taskId, text, check_mode: checkMode }),
  });
  const body = await parseApiResponse<SuggestionCheckPayload>(response);
  if (!body.success) throw new Error(body.message);
  return body.data;
}

export async function checkParagraphSuggestions(
  taskId: string,
  text: string,
): Promise<ParagraphCheckPayload> {
  const response = await fetch(`${apiBaseUrl}/api/suggestions/paragraph`, {
    method: "POST",
    credentials: "include",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ task_id: taskId, text }),
  });
  const body = await parseApiResponse<ParagraphCheckPayload>(response);
  if (!body.success) throw new Error(body.message);
  return body.data;
}

export function applySuggestionToText(
  text: string,
  suggestion: GrammarSuggestion,
  replacement: string,
): string {
  return `${text.slice(0, suggestion.offset)}${replacement}${text.slice(
    suggestion.offset + suggestion.length,
  )}`;
}

export async function listTeacherMarkingSubmissions(filters: {
  class_id?: string;
  task_id?: string;
  status?: MarkingResult["status"];
} = {}): Promise<TeacherMarkingSubmission[]> {
  const query = new URLSearchParams();
  if (filters.class_id) query.set("class_id", filters.class_id);
  if (filters.task_id) query.set("task_id", filters.task_id);
  if (filters.status) query.set("status", filters.status);
  const suffix = query.size > 0 ? `?${query.toString()}` : "";
  const response = await fetch(`${apiBaseUrl}/api/teacher/marking/submissions${suffix}`, {
    credentials: "include",
    cache: "no-store",
  });
  const body = await parseApiResponse<{ items: TeacherMarkingSubmission[] }>(response);
  if (!body.success) throw new Error(body.message);
  return body.data.items;
}

export async function getTeacherDashboardSummary(filters: {
  class_id?: string;
  task_id?: string;
} = {}): Promise<TeacherDashboardSummary> {
  const query = new URLSearchParams();
  if (filters.class_id) query.set("class_id", filters.class_id);
  if (filters.task_id) query.set("task_id", filters.task_id);
  const suffix = query.size > 0 ? `?${query.toString()}` : "";
  const response = await fetch(`${apiBaseUrl}/api/teacher/dashboard-summary${suffix}`, {
    credentials: "include",
    cache: "no-store",
  });
  const body = await parseApiResponse<{ summary: TeacherDashboardSummary }>(response);
  if (!body.success) throw new Error(body.message);
  return body.data.summary;
}

export async function runMarking(markingResultId: string): Promise<MarkingResult> {
  const response = await fetch(`${apiBaseUrl}/api/teacher/marking-results/${markingResultId}/run`, {
    method: "POST",
    credentials: "include",
  });
  const body = await parseApiResponse<{ marking_result: MarkingResult }>(response);
  if (!body.success) throw new Error(body.message);
  return body.data.marking_result;
}

export async function reviewMarking(
  markingResultId: string,
  payload: {
    content_score: number;
    language_score: number;
    organisation_score: number;
    total_score: number;
    review_notes?: string;
    status?: "DRAFT" | "REVIEWED" | "RELEASE_READY";
  },
): Promise<TeacherReview> {
  const response = await fetch(`${apiBaseUrl}/api/teacher/marking-results/${markingResultId}/review`, {
    method: "POST",
    credentials: "include",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(payload),
  });
  const body = await parseApiResponse<{ review: TeacherReview }>(response);
  if (!body.success) throw new Error(body.message);
  return body.data.review;
}

export async function releaseFeedback(markingResultId: string): Promise<TeacherReview> {
  const response = await fetch(`${apiBaseUrl}/api/teacher/marking-results/${markingResultId}/release`, {
    method: "POST",
    credentials: "include",
  });
  const body = await parseApiResponse<{ review: TeacherReview }>(response);
  if (!body.success) throw new Error(body.message);
  return body.data.review;
}

export async function getStudentFeedback(submissionId: string): Promise<StudentFeedback> {
  const response = await fetch(`${apiBaseUrl}/api/student/submissions/${submissionId}/feedback`, {
    credentials: "include",
    cache: "no-store",
  });
  const body = await parseApiResponse<StudentFeedback>(response);
  if (!body.success) throw new Error(body.message);
  return body.data;
}

export async function completeExercise(
  exerciseId: string,
  responseText: string,
): Promise<PostWritingExercise> {
  const response = await fetch(`${apiBaseUrl}/api/student/exercises/${exerciseId}/complete`, {
    method: "POST",
    credentials: "include",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ response_text: responseText }),
  });
  const body = await parseApiResponse<{ exercise: PostWritingExercise }>(response);
  if (!body.success) throw new Error(body.message);
  return body.data.exercise;
}

export async function getClassReport(
  classId: string,
  taskId?: string,
): Promise<ClassReportPayload> {
  const query = taskId ? `?task_id=${encodeURIComponent(taskId)}` : "";
  const response = await fetch(`${apiBaseUrl}/api/teacher/reports/classes/${classId}${query}`, {
    credentials: "include",
    cache: "no-store",
  });
  const body = await parseApiResponse<ClassReportPayload>(response);
  if (!body.success) throw new Error(body.message);
  return body.data;
}

export async function generateClassReport(
  classId: string,
  taskId?: string,
): Promise<ClassReportPayload> {
  const query = taskId ? `?task_id=${encodeURIComponent(taskId)}` : "";
  const response = await fetch(`${apiBaseUrl}/api/teacher/reports/classes/${classId}/generate${query}`, {
    method: "POST",
    credentials: "include",
  });
  const body = await parseApiResponse<ClassReportPayload>(response);
  if (!body.success) throw new Error(body.message);
  return body.data;
}

export async function listClassReportExports(classId: string): Promise<ReportExportAudit[]> {
  const response = await fetch(`${apiBaseUrl}/api/teacher/reports/classes/${classId}/exports`, {
    credentials: "include",
    cache: "no-store",
  });
  const body = await parseApiResponse<{ exports: ReportExportAudit[] }>(response);
  if (!body.success) throw new Error(body.message);
  return body.data.exports;
}

export async function downloadClassReport(
  classId: string,
  format: "csv" | "pdf",
  taskId?: string,
): Promise<DownloadedReport> {
  const query = taskId ? `?task_id=${encodeURIComponent(taskId)}` : "";
  const response = await fetch(
    `${apiBaseUrl}/api/teacher/reports/classes/${classId}/export.${format}${query}`,
    { credentials: "include" },
  );
  if (!response.ok) {
    throw new Error(await parseApiError(response, `${format.toUpperCase()} export failed.`));
  }
  const blob = await response.blob();
  const disposition = response.headers.get("content-disposition") ?? "";
  const filenameMatch = disposition.match(/filename="?([^";]+)"?/i);
  const filename = filenameMatch?.[1] ?? `class-report-${classId}.${format}`;
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
  return {
    filename,
    bytes: blob.size,
    content_type: blob.type || response.headers.get("content-type") || "",
  };
}

export async function changeOwnPassword(currentPassword: string, newPassword: string): Promise<void> {
  const response = await fetch(`${apiBaseUrl}/api/account/password`, {
    method: "POST",
    credentials: "include",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
  });
  if (!response.ok) throw new Error(await parseApiError(response, "Unable to change your password."));
}

export async function resetUserPassword(userId: string, temporaryPassword: string): Promise<void> {
  const response = await fetch(`${apiBaseUrl}/api/admin/users/${userId}/password`, {
    method: "POST",
    credentials: "include",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ temporary_password: temporaryPassword }),
  });
  if (!response.ok) throw new Error(await parseApiError(response, "Unable to reset this password."));
}
