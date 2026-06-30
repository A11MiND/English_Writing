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

  return (
    <AppShell title="Student home" user={state.user} onLogout={() => void onLogout()} maxWidth="standard">
      <section className="grid gap-5 sm:grid-cols-3">
        <div className="section-card">
          <p className="text-sm font-semibold text-ink/55">Student number</p>
          <p className="mt-2 text-2xl font-semibold">{state.profile.student_number}</p>
        </div>
        <div className="section-card">
          <p className="text-sm font-semibold text-ink/55">Level</p>
          <p className="mt-2 text-2xl font-semibold">{state.profile.level}</p>
        </div>
        <div className="section-card">
          <p className="text-sm font-semibold text-ink/55">Class</p>
          <p className="mt-2 text-2xl font-semibold">{state.profile.class_name ?? "-"}</p>
        </div>
      </section>

      <section className="mt-5 section-card">
        <h2 className="text-xl font-semibold text-ink">Assigned writing tasks</h2>
        <div className="mt-4 grid gap-4">
          {state.tasks.map((task) => (
            <div
              key={task.id}
              className="muted-panel border border-ink/10"
              data-testid={`student-task-${task.mode.toLowerCase()}`}
            >
              <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <p className="font-semibold text-ink">{task.title}</p>
                  <p className="mt-1 text-sm text-ink/65">
                    {task.level} · {task.rubric_title ?? "School rubric"} · {task.word_minimum ?? "-"}-{task.word_maximum ?? "-"} words
                  </p>
                </div>
                <span className="status-pill">
                  {task.mode === "PRACTICE" ? "Practice Mode" : "Exam Mode"}
                </span>
              </div>
              <p className="mt-3 text-sm leading-6 text-ink/70">{task.instruction}</p>
              <Link
                href={`/student/tasks/${task.id}/${task.mode === "PRACTICE" ? "practice" : "exam"}`}
                className="btn btn-secondary mt-4"
                data-testid={`open-${task.mode.toLowerCase()}-task`}
              >
                Open writing editor
              </Link>
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
