export const roles = [
  "SYSTEM_ADMIN",
  "SCHOOL_ADMIN",
  "TEACHER",
  "STUDENT",
] as const;

export type Role = (typeof roles)[number];

export const errorCodes = [
  "AUTH_REQUIRED",
  "ACCESS_DENIED",
  "VALIDATION_ERROR",
  "NOT_FOUND",
  "DUPLICATE_RECORD",
  "TASK_CLOSED",
  "SUBMISSION_LOCKED",
  "AI_MARKING_FAILED",
  "EXPORT_FAILED",
  "SUPPORT_TICKET_NOT_FOUND",
  "HEALTH_CHECK_FAILED",
] as const;

export type ErrorCode = (typeof errorCodes)[number];

export type ApiSuccess<TData> = {
  success: true;
  data: TData;
  request_id: string;
};

export type ApiError = {
  success: false;
  error_code: ErrorCode;
  message: string;
  request_id: string;
};

export type ApiResponse<TData> = ApiSuccess<TData> | ApiError;

export type HealthPayload = {
  service: string;
  status: "ok" | "degraded";
  environment: string;
  checks: Record<string, string>;
};

export const accountStatuses = ["ACTIVE", "SUSPENDED", "ARCHIVED"] as const;

export type AccountStatus = (typeof accountStatuses)[number];

export type AuthenticatedUser = {
  id: string;
  email: string;
  display_name: string;
  role: Role;
  school_id: string | null;
  status: AccountStatus;
};

export type AuthPayload = {
  user: AuthenticatedUser;
};

export type AccountCapabilities = {
  plan_code: "FREE" | "SCHOOL_PRO" | string;
  subscription_status: string;
  subscription_renews_at: string | null;
  features: {
    grammar_check: boolean;
    ai_assist: boolean;
    read_aloud: boolean;
    image_generation: boolean;
    ai_marking: boolean;
    reports: boolean;
  };
};

export type SchoolClass = {
  id: string;
  name: string;
  level: "P4" | "P5" | "P6" | string;
  academic_year: string;
  status: string;
  teacher_count?: number;
  student_count?: number;
};

export type TeacherStudent = {
  id: string;
  display_name: string;
  email: string;
  status: AccountStatus;
  student_number: string;
  level: string;
  class_id: string;
  class_name: string;
};

export type AdminUser = {
  id: string;
  email: string;
  display_name: string;
  role: Role;
  status: AccountStatus;
  staff_code: string | null;
  student_number: string | null;
  level: string | null;
  class_name: string | null;
};

export type ImportRole = Extract<Role, "TEACHER" | "STUDENT">;

export type ImportUserRow = {
  external_user_id?: string;
  email: string;
  display_name: string;
  student_number?: string;
  level?: string;
  class_name?: string;
  staff_code?: string;
};

export type ImportRejectedRow = {
  row: number;
  email: string;
  reasons: string[];
};

export type ImportSuccessfulRow = {
  row: number;
  email: string;
  role: ImportRole;
};

export type ImportUsersPayload = {
  successful_rows: ImportSuccessfulRow[];
  rejected_rows: ImportRejectedRow[];
  successful_count: number;
  rejected_count: number;
};

export type AiServiceStatus = {
  provider: string;
  provider_display_name: string;
  model: string | null;
  configured: boolean;
  api_key_configured: boolean;
  base_url_configured: boolean;
  source?: "database" | "environment" | "invalid" | string;
  masked_api_key?: string | null;
  last_call_status: "SUCCESS" | "FAILED" | string | null;
  last_error_category: string | null;
  last_called_at: string | null;
};

export type AiSettings = {
  provider: string;
  provider_display_name: string;
  model: string | null;
  base_url: string | null;
  timeout_seconds: number;
  configured: boolean;
  api_key_configured: boolean;
  masked_api_key: string | null;
  source: "database" | "environment" | "invalid" | string;
};

export type StudentProfilePayload = {
  profile: {
    student_number: string;
    level: string;
    class_name: string | null;
  };
};

export type WritingMode = "PRACTICE" | "EXAM";

export type WritingTaskStatus = "DRAFT" | "PUBLISHED" | "CLOSED" | "ARCHIVED";

export type RubricStatus = "DRAFT" | "ACTIVE" | "ARCHIVED";

export type RubricDimension = {
  id: string;
  name: string;
  min_score: number;
  max_score: number;
  descriptor: string;
  sort_order: number;
};

export type Rubric = {
  id: string;
  title: string;
  level: string;
  total_score: number;
  status: RubricStatus;
  used_by_task_count: number;
  dimensions: RubricDimension[];
};

export type WritingTask = {
  id: string;
  title: string;
  level: string;
  instruction: string;
  genre: string | null;
  mode: WritingMode;
  word_minimum: number | null;
  word_maximum: number | null;
  due_at: string | null;
  exam_duration_minutes: number | null;
  rubric_id: string;
  rubric_title: string | null;
  rubric_total_score: number | null;
  status: WritingTaskStatus;
  assigned_classes: string[];
  draft_status?: "ACTIVE" | "SUBMITTED" | null;
  draft_saved_at?: string | null;
  submission_id?: string | null;
  submission_status?: "SUBMITTED" | null;
  submitted_at?: string | null;
  locked?: boolean;
  feedback_released?: boolean;
  image_url?: string | null;
};

export type TaskAssignment = {
  id: string;
  task_id: string;
  class_id: string;
  class_name: string;
};

export type Draft = {
  id: string;
  content_html: string;
  content_text: string;
  word_count: number;
  version: number;
  status: "ACTIVE" | "SUBMITTED";
  saved_at: string;
};

export type Submission = {
  id: string;
  content_html: string;
  content_text: string;
  word_count: number;
  status: "SUBMITTED";
  submitted_at: string;
};

export type WritingWorkspace = {
  task: WritingTask;
  draft: Draft | null;
  submission: Submission | null;
  locked: boolean;
};

export type PersonalPracticeFocus =
  | "PAST_TENSE"
  | "STRONGER_FEELINGS"
  | "STORY_ORDER"
  | "BETTER_DESCRIPTIONS";

export type PersonalPracticeGenre = "NARRATIVE" | "DESCRIPTION" | "LETTER";

export type PersonalPracticeTask = WritingTask & {
  personal_practice: true;
  practice_focus: string;
  practice_genre?: string;
  duration_minutes?: number;
  structure?: string[];
  marking_result?: PersonalPracticeMarking | null;
};

export type PersonalPracticeMarking = {
  id: string;
  status: MarkingStatus;
  dimension_scores: DimensionScore[];
  total_score: number | null;
  strengths: string[];
  weaknesses: string[];
  sentence_level_comments: AiMarkingOutput["sentence_level_comments"];
  recommended_exercises: AiMarkingOutput["recommended_exercises"];
  marked_at: string | null;
};

export type PersonalPracticeResult = {
  task: {
    id: string;
    title: string;
    instruction: string;
    level: string;
    practice_focus: string;
    rubric_total_score: number;
    rubric_dimensions: Array<Pick<RubricDimension, "name" | "min_score" | "max_score">>;
  };
  submission: {
    id: string;
    content_text: string;
    word_count: number;
    submitted_at: string;
  } | null;
  marking_result: PersonalPracticeMarking | null;
};

export type StudentRewriteGoal = "CLEARER" | "MORE_DESCRIPTIVE" | "FRIENDLIER" | "MORE_FORMAL";

export type StudentRewrite = {
  original: string;
  revised: string;
  explanation: string;
  goal: StudentRewriteGoal;
};

export type GrammarSuggestion = {
  id: string;
  rule_id: string;
  category: string;
  message: string;
  short_message: string;
  offset: number;
  length: number;
  replacements: string[];
  severity: "INFO" | "WARNING" | "ERROR";
  level: "WORD" | "SENTENCE";
};

export type ParagraphSuggestion = {
  id: string;
  level: "PARAGRAPH";
  focus: "FOCUS" | "FLOW" | "ORDER" | "REPETITION" | "LINKING";
  title: string;
  message: string;
  evidence: string;
  action: string;
};

export type SuggestionCheckMode = "CHANGED" | "FULL";

export type SuggestionCheckPayload = {
  suggestions: GrammarSuggestion[];
  cached: boolean;
  service_status: "ok" | "unavailable";
  check_mode: SuggestionCheckMode;
};

export type ParagraphCheckPayload = {
  suggestions: ParagraphSuggestion[];
  cached: boolean;
  service_status: "ok" | "fallback";
};

export type ExamEventType =
  | "PASTE_ATTEMPT"
  | "WINDOW_BLUR"
  | "WINDOW_FOCUS"
  | "FULLSCREEN_EXIT"
  | "SUBMISSION";

export type TeacherExamEventRecord = {
  id: string;
  event_type: ExamEventType;
  metadata: Record<string, unknown>;
  occurred_at: string;
};

export type TeacherSubmissionExamEvents = {
  submission_id: string;
  task_id: string;
  mode: WritingMode;
  class_name: string;
  events: TeacherExamEventRecord[];
};

export type PromptDraft = {
  id: string;
  level: string;
  mode: WritingMode;
  teaching_focus: string;
  word_minimum: number | null;
  word_maximum: number | null;
  exam_duration_minutes: number | null;
  rubric_id: string;
  title: string;
  instruction: string;
  rubric_notes: string[];
  provider: string;
  model: string;
  status: "DRAFT" | "USED" | "ARCHIVED" | string;
  created_at: string;
};

export const llmProviders = [
  "openai_compatible",
  "deepseek",
  "qwen",
  "doubao",
  "minimax",
] as const;

export type LlmProvider = (typeof llmProviders)[number];

export type LlmConfidenceLevel = "LOW" | "MEDIUM" | "HIGH";

/** One score per rubric dimension, so a school can name and weight its own. */
export type DimensionScore = {
  name: string;
  score: number | null;
  max_score: number | null;
  feedback?: string | null;
};

export type AiMarkingOutput = {
  dimension_scores: DimensionScore[];
  total_score: number;
  confidence_level: LlmConfidenceLevel;
  strengths: string[];
  weaknesses: string[];
  sentence_level_comments: Array<{
    sentence: string;
    comment: string;
    category: "CONTENT" | "LANGUAGE" | "ORGANISATION" | "MECHANICS" | "OTHER";
  }>;
  recommended_exercises: Array<{
    title: string;
    exercise_type: string;
    focus_area: string;
    prompt: string;
  }>;
  warning_flags: string[];
  model_metadata: Record<string, unknown>;
};

export type MarkingStatus = "QUEUED" | "PROCESSING" | "AI_MARKED" | "AI_MARKING_FAILED";

export type MarkingResult = Omit<
  AiMarkingOutput,
  "dimension_scores" | "total_score" | "confidence_level"
> & {
  id: string;
  submission_id: string;
  task_id: string;
  student_id: string;
  status: MarkingStatus;
  dimension_scores: DimensionScore[];
  total_score: number | null;
  confidence_level: LlmConfidenceLevel | null;
  attempts: number;
  last_error: string | null;
  queued_at: string;
  marked_at: string | null;
};

export type ReleasedStudentMarking = {
  id: string;
  submission_id: string;
  task_id: string;
  student_id: string;
  status: MarkingStatus;
  dimension_scores: DimensionScore[];
  total_score: number | null;
  strengths: string[];
  weaknesses: string[];
  sentence_level_comments: AiMarkingOutput["sentence_level_comments"];
  recommended_exercises: AiMarkingOutput["recommended_exercises"];
  marked_at: string | null;
};

export type TeacherMarkingSubmission = {
  submission: Submission & {
    task_id: string;
    student_id: string;
  };
  task: {
    id: string;
    title: string;
    mode: WritingMode;
    level: string;
    rubric: {
      id: string;
      title: string;
      total_score: number;
      dimensions: RubricDimension[];
    };
  };
  class_name: string;
  marking_result: MarkingResult | null;
};

export type TeacherDashboardSummary = {
  assigned_class_count: number;
  active_task_count: number;
  submitted_count: number;
  pending_marking_count: number;
  unreleased_feedback_count: number;
  marking_status_counts: Record<MarkingStatus, number>;
};

export type TeacherReview = {
  id: string;
  marking_result_id: string;
  submission_id: string;
  dimension_scores: DimensionScore[];
  total_score: number | null;
  review_notes: string | null;
  status: "DRAFT" | "REVIEWED" | "RELEASE_READY" | "RELEASED";
  feedback_released_at: string | null;
};

export type PostWritingExercise = {
  id: string;
  marking_result_id: string;
  submission_id: string;
  title: string;
  exercise_type: string;
  focus_area: string;
  prompt: string;
  response_text: string | null;
  status: "ASSIGNED" | "COMPLETED";
  assigned_at: string;
  completed_at: string | null;
};

export type StudentFeedback = {
  task: {
    id: string;
    title: string;
    mode: WritingMode;
    level: string;
  };
  submission: {
    id: string;
    content_text: string;
    word_count: number;
    submitted_at: string;
  };
  marking_result: ReleasedStudentMarking;
  review: TeacherReview;
  exercises: PostWritingExercise[];
};

export type ClassReportSummary = {
  student_count: number;
  assigned_task_count: number;
  expected_submissions: number;
  submitted_count: number;
  completion_rate: number;
  scored_submission_count: number;
  average_total_score: number | null;
  average_total_percentage: number | null;
  maximum_total_score: number | null;
};

export type ClassReportPayload = {
  class_report: {
    id: string | null;
    school_name: string;
    class_id: string;
    class_name: string;
    level: string;
    task_id: string | null;
    generated_at: string | null;
    status: "LIVE_PREVIEW" | "READY" | string;
  };
  summary: ClassReportSummary;
  rubric_breakdown: Array<{
    name: string;
    average: number | null;
    average_percentage: number | null;
    max_score: number | null;
  }>;
  score_distribution: Record<string, number>;
  common_weaknesses: Array<{
    weakness: string;
    count: number;
  }>;
  completion_rows: Array<{
    student_id: string;
    student_name: string;
    student_number: string;
    task_id: string;
    task_title: string;
    mode: WritingMode;
    submitted: boolean;
    submitted_at: string | null;
    word_count: number | null;
    dimension_scores: DimensionScore[];
    total_score: number | null;
    total_max_score: number;
    rubric_id: string;
    rubric_title: string;
    review_status: string | null;
    marking_status: string | null;
  }>;
};

export type ReportExportAudit = {
  id: string;
  action: "CLASS_REPORT_EXPORTED" | string;
  class_id: string;
  task_id: string | null;
  format: "csv" | "pdf" | string;
  actor_user_id: string | null;
  actor_role: string | null;
  created_at: string;
};
