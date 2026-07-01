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

export function StudentHome() {
  const [state, setState] = useState<StudentState>({ status: "loading" });

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

  return (
    <AppShell title="Student home" user={state.user} onLogout={() => void onLogout()} maxWidth="standard">
      <section id="profile" className="section-anchor grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="metric-card">
          <p className="metric-label">Student number</p>
          <p className="metric-value">{state.profile.student_number}</p>
          <p className="metric-hint">{state.profile.class_name ?? "No class assigned"}</p>
        </div>
        <div className="metric-card">
          <p className="metric-label">To write</p>
          <p className="metric-value">{toWriteCount}</p>
          <p className="metric-hint">Practice or Exam tasks open</p>
        </div>
        <div className="metric-card">
          <p className="metric-label">Submitted</p>
          <p className="metric-value">{submittedCount}</p>
          <p className="metric-hint">Locked final writing</p>
        </div>
        <div className="metric-card">
          <p className="metric-label">Feedback ready</p>
          <p className="metric-value">{feedbackReadyCount}</p>
          <p className="metric-hint">Released by teacher</p>
        </div>
      </section>

      <section id="tasks" className="section-anchor section-card">
        <div className="panel-header">
          <div>
            <h2 className="panel-title">Assigned writing tasks</h2>
            <p className="panel-subtitle">
              Open Practice Mode for suggestions, or Exam Mode for timed writing without real-time help.
            </p>
          </div>
          <span className="status-pill-muted">{state.profile.level}</span>
        </div>
        <div className="mt-4 grid gap-4">
          {state.tasks.map((task) => (
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
                  Open writing editor
                </Link>
                {task.submitted_at ? (
                  <span className="text-sm text-ink/55">
                    Submitted {new Date(task.submitted_at).toLocaleDateString()}
                  </span>
                ) : null}
              </div>
            </div>
          ))}
          {state.tasks.length === 0 ? (
            <p className="muted-panel text-sm text-ink/60">No published tasks assigned to your class yet.</p>
          ) : null}
        </div>
      </section>
    </AppShell>
  );
}
