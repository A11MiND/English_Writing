"use client";

import type { WritingTask } from "@english-ai-writing/shared";
import Link from "next/link";
import { useEffect, useState } from "react";

import { AppShell, type AppShellUser } from "@/components/app-shell";
import { currentUser, logout } from "@/lib/auth";
import { getStudentProfile, listStudentTasks } from "@/lib/school-data";

type StudentProfile = {
  student_number: string;
  level: string;
  class_name: string | null;
};

type StudentState =
  | { status: "loading" }
  | { status: "denied"; message: string }
  | { status: "ready"; user: AppShellUser; profile: StudentProfile; tasks: WritingTask[] };

type StudentTaskView = "next" | "feedback" | "history";

export function StudentHome() {
  const [state, setState] = useState<StudentState>({ status: "loading" });
  const [taskView, setTaskView] = useState<StudentTaskView>("next");
  const [showAllTasks, setShowAllTasks] = useState(false);

  useEffect(() => {
    let active = true;
    async function load() {
      const user = await currentUser();
      if (!active) return;
      if (!user) {
        window.location.href = "/";
        return;
      }
      if (user.role !== "STUDENT") {
        setState({ status: "denied", message: "Your role cannot access student home." });
        return;
      }
      const [profile, tasks] = await Promise.all([getStudentProfile(), listStudentTasks()]);
      setState({
        status: "ready",
        user: { display_name: user.display_name, email: user.email, role: user.role },
        profile,
        tasks,
      });
    }
    void load().catch((error) => {
      setState({ status: "denied", message: error instanceof Error ? error.message : "Unable to load profile." });
    });
    return () => {
      active = false;
    };
  }, []);

  async function onLogout() {
    await logout();
    window.location.href = "/";
  }

  if (state.status === "loading") {
    return <main className="loading-state">Loading student home...</main>;
  }

  if (state.status === "denied") {
    return (
      <main className="centered-state">
        <h1 className="text-4xl font-semibold">Access denied</h1>
        <p className="mt-4 text-ink/65">{state.message}</p>
      </main>
    );
  }

  const toWriteCount = state.tasks.filter((task) => !task.locked && !task.submission_id).length;
  const submittedCount = state.tasks.filter((task) => task.locked || task.submission_id).length;
  const feedbackReadyCount = state.tasks.filter((task) => task.feedback_released).length;
  const toWriteTasks = state.tasks.filter((task) => !task.locked && !task.submission_id);
  const feedbackTasks = state.tasks.filter((task) => task.feedback_released);
  const submittedTasks = state.tasks.filter((task) => task.locked || task.submission_id);
  const currentTasks = taskView === "next"
    ? toWriteTasks
    : taskView === "feedback"
      ? feedbackTasks
      : submittedTasks.slice(0, 12);
  const displayLimit = taskView === "history" ? 6 : 3;
  const visibleTasks = showAllTasks ? currentTasks : currentTasks.slice(0, displayLimit);
  const hiddenTaskCount = Math.max(0, currentTasks.length - visibleTasks.length);
  const selectedEmptyMessage = taskView === "next"
    ? "You have no writing to do right now."
    : taskView === "feedback"
      ? "No teacher feedback is ready yet."
      : "No finished writing yet.";

  function taskActionLabel(task: WritingTask) {
    if (task.feedback_released) return "View feedback";
    if (task.submission_id || task.locked) return "Open my writing";
    return task.mode === "EXAM" ? "Start exam" : "Start writing";
  }

  return (
    <AppShell title="Student home" user={state.user} onLogout={() => void onLogout()} maxWidth="standard">
      <section id="profile" className="section-anchor grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="metric-card">
          <p className="metric-label">Student number</p>
          <p className="metric-value">{state.profile.student_number}</p>
          <p className="metric-hint">{state.profile.class_name ?? "No class assigned"}</p>
        </div>
        <div className="metric-card">
          <p className="metric-label">To do</p>
          <p className="metric-value">{toWriteCount}</p>
          <p className="metric-hint">Writing not finished</p>
        </div>
        <div className="metric-card">
          <p className="metric-label">Done</p>
          <p className="metric-value">{submittedCount}</p>
          <p className="metric-hint">Sent to teacher</p>
        </div>
        <div className="metric-card">
          <p className="metric-label">Teacher feedback</p>
          <p className="metric-value">{feedbackReadyCount}</p>
          <p className="metric-hint">Ready to read</p>
        </div>
      </section>

      <section id="tasks" className="section-anchor section-card">
        <div className="panel-header">
          <div>
            <h2 className="panel-title">What should I do?</h2>
            <p className="panel-subtitle">
              Start with one task. Finished writing is kept in Done work.
            </p>
          </div>
          <span className="status-pill-muted">{state.profile.level}</span>
        </div>
        <div className="mt-4 flex flex-wrap gap-2" aria-label="Task views">
          {([
            ["next", `To do (${toWriteCount})`],
            ["feedback", `Teacher feedback (${feedbackReadyCount})`],
            ["history", `Done work (${submittedCount})`],
          ] as const).map(([view, label]) => (
            <button
              key={view}
              type="button"
              onClick={() => {
                setTaskView(view);
                setShowAllTasks(false);
              }}
              className={`btn ${taskView === view ? "btn-primary" : "btn-secondary"}`}
            >
              {label}
            </button>
          ))}
        </div>
        <div className="mt-4 grid gap-4">
          {visibleTasks.map((task) => (
            <div
              key={task.id}
              className="muted-panel"
              data-testid={`student-task-${task.mode.toLowerCase()}`}
            >
              <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <p className="font-semibold text-ink">{task.title}</p>
                  <p className="mt-1 text-sm text-ink/65">
                    {task.level} · {task.rubric_title ?? "School rubric"} · {task.word_minimum ?? "-"}-{task.word_maximum ?? "-"} words
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <span className={task.mode === "EXAM" ? "status-pill-warning" : "status-pill"}>
                    {task.mode === "PRACTICE" ? "Practice Mode" : "Exam Mode"}
                  </span>
                  {task.locked || task.submission_id ? (
                    <span className="status-pill-muted">Submitted</span>
                  ) : null}
                  {task.feedback_released ? <span className="status-pill">Feedback ready</span> : null}
                </div>
              </div>
              <p className="mt-3 text-sm leading-6 text-ink/70">{task.instruction}</p>
              <div className="mt-4 flex flex-wrap items-center gap-3">
                <Link
                  href={`/student/tasks/${task.id}/${task.mode === "PRACTICE" ? "practice" : "exam"}`}
                  className="btn btn-secondary"
                  data-testid={`open-${task.mode.toLowerCase()}-task`}
                >
                  {taskActionLabel(task)}
                </Link>
                {task.submitted_at ? (
                  <span className="text-sm text-ink/55">
                    Submitted {new Date(task.submitted_at).toLocaleDateString()}
                  </span>
                ) : null}
              </div>
            </div>
          ))}
          {hiddenTaskCount > 0 ? (
            <button
              type="button"
              className="btn btn-secondary justify-self-start"
              onClick={() => setShowAllTasks(true)}
              data-testid="student-show-all-tasks"
            >
              Show all {currentTasks.length} tasks
            </button>
          ) : showAllTasks && currentTasks.length > displayLimit ? (
            <button
              type="button"
              className="btn btn-secondary justify-self-start"
              onClick={() => setShowAllTasks(false)}
            >
              Show fewer tasks
            </button>
          ) : null}
          {currentTasks.length === 0 ? (
            <p className="muted-panel text-sm text-ink/60">{selectedEmptyMessage}</p>
          ) : null}
        </div>
      </section>
    </AppShell>
  );
}
