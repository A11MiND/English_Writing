"use client";

import type { WritingTask } from "@english-ai-writing/shared";
import Link from "next/link";
import { useEffect, useState } from "react";

import { ProductTopNav, type AppShellUser } from "@/components/app-shell";
import { MascotGuide } from "@/components/student-mascot";
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

function taskHref(task: WritingTask) {
  if (task.feedback_released && task.submission_id) return `/student/feedback/${task.submission_id}`;
  if (task.mode === "EXAM") return `/student/exam/${task.id}`;
  return `/student/tasks/${task.id}/practice`;
}

function taskActionLabel(task: WritingTask) {
  if (task.feedback_released) return "View feedback";
  if (task.submission_id || task.locked) return "Open my writing";
  return task.mode === "EXAM" ? "Start exam" : "Start writing";
}

function dueLabel(task: WritingTask) {
  return task.due_at ? `Due ${new Date(task.due_at).toLocaleDateString()}` : "No due date";
}

function modeBadge(task: WritingTask) {
  return task.mode === "EXAM" ? "badge-warning" : "badge";
}

function statusBadge(task: WritingTask) {
  if (task.feedback_released) return <span className="badge-success">Returned</span>;
  if (task.locked || task.submission_id) return <span className="badge-soft">Submitted</span>;
  if (task.status === "CLOSED" || task.status === "ARCHIVED") return <span className="badge-danger">{task.status}</span>;
  return <span className="badge-soft">To write</span>;
}

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
        window.location.href = "/login";
        return;
      }
      if (user.role !== "STUDENT") {
        setState({ status: "denied", message: "Your role cannot access student writing." });
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
      setState({ status: "denied", message: error instanceof Error ? error.message : "Unable to load writing tasks." });
    });
    return () => {
      active = false;
    };
  }, []);

  async function onLogout() {
    await logout();
    window.location.href = "/login";
  }

  if (state.status === "loading") {
    return <main className="loading-state">Loading student writing...</main>;
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

  const toWriteTasks = state.tasks.filter((task) => !task.locked && !task.submission_id && task.status === "PUBLISHED");
  const feedbackTasks = state.tasks.filter((task) => task.feedback_released && task.submission_id);
  const submittedTasks = state.tasks.filter((task) => task.locked || task.submission_id);
  const currentTasks = taskView === "next" ? toWriteTasks : taskView === "feedback" ? feedbackTasks : submittedTasks;
  const displayLimit = taskView === "history" ? 6 : 3;
  const visibleTasks = showAllTasks ? currentTasks : currentTasks.slice(0, displayLimit);
  const selectedEmptyMessage =
    taskView === "next"
      ? "You have no writing to do right now."
      : taskView === "feedback"
        ? "No teacher feedback has been released yet."
        : "No finished writing yet.";

  const latestFeedback = feedbackTasks[0];

  return (
    <ProductTopNav
      active="My Writing"
      links={[
        { href: "/student/writing", label: "My Writing" },
        { href: "/student/practice", label: "My Practice" },
        { href: latestFeedback ? `/student/feedback/${latestFeedback.submission_id}` : "/student/writing", label: "Feedback" },
      ]}
      onLogout={() => void onLogout()}
    >
      <main className="container">
        <section className="hero student-home-hero">
          <div className="hero-copy">
            <p className="eyebrow">Welcome back, {state.user.display_name.split(" ")[0]}</p>
            <h1>Your next story starts here.</h1>
            <p className="lead">
              Pick up your next writing task, read a teacher’s feedback, or look back at how far your writing has come.
            </p>
            <div className="hero-actions">
              <Link className="btn btn-primary" href={toWriteTasks[0] ? taskHref(toWriteTasks[0]) : "/student/writing"} aria-disabled={!toWriteTasks[0]}>
                {toWriteTasks[0] ? "Continue my next task" : "View my writing"}
              </Link>
              <Link className="btn btn-secondary" href={latestFeedback ? `/student/feedback/${latestFeedback.submission_id}` : "/student/writing"} aria-disabled={!latestFeedback}>
                Read latest feedback
              </Link>
              <Link className="btn btn-secondary" href="/student/practice">
                Make my own practice
              </Link>
            </div>
          </div>
          <MascotGuide
            variant="home"
            title={toWriteTasks.length ? "Let’s take one small step." : "You’re all caught up."}
            body={toWriteTasks.length
              ? `${toWriteTasks.length} writing ${toWriteTasks.length === 1 ? "task is" : "tasks are"} waiting. Start with the first one and focus on getting your ideas down.`
              : "There is no new writing right now. You can read returned feedback or revisit a finished story."}
          >
            <div className="mascot-stat-row">
              <span><strong>{toWriteTasks.length}</strong> to write</span>
              <span><strong>{feedbackTasks.length}</strong> returned</span>
              <span>{state.profile.class_name ?? state.profile.level}</span>
            </div>
          </MascotGuide>
        </section>

        <section className="panel">
          <div className="panel-header">
            <div>
              <h2 className="panel-title">Assigned writing</h2>
              <p className="panel-subtitle">Choose one clear next step. Your newest work appears first.</p>
            </div>
            <span className="badge-soft">{state.profile.level}</span>
          </div>
          <div className="segmented" aria-label="Task views">
            {([
              ["next", `To do (${toWriteTasks.length})`],
              ["feedback", `Teacher feedback (${feedbackTasks.length})`],
              ["history", `Done work (${submittedTasks.length})`],
            ] as const).map(([view, label]) => (
              <button
                key={view}
                type="button"
                className={`segment ${taskView === view ? "active" : ""}`}
                onClick={() => {
                  setTaskView(view);
                  setShowAllTasks(false);
                }}
              >
                {label}
              </button>
            ))}
          </div>

          <div className="suggestion-list" style={{ marginTop: 18 }}>
            {visibleTasks.map((task) => (
              <article key={task.id} className={`task-card ${task.mode === "EXAM" && !task.submission_id ? "featured" : ""}`}>
                <div className="task-meta">
                  <span className={modeBadge(task)}>{task.mode === "EXAM" ? "Exam" : "Practice"}</span>
                  <span className="badge-soft">{task.word_minimum ?? "-"}-{task.word_maximum ?? "-"} words</span>
                  <span className="badge-soft">{dueLabel(task)}</span>
                  {statusBadge(task)}
                </div>
                <h3 className="panel-title">{task.title}</h3>
                <p className="panel-subtitle">{task.instruction}</p>
                <div className="row-actions" style={{ marginTop: 8 }}>
                  <Link className={task.feedback_released ? "btn btn-dark" : "btn btn-primary"} href={taskHref(task)}>
                    {taskActionLabel(task)}
                  </Link>
                  {task.submitted_at ? (
                    <span className="panel-subtitle">Submitted {new Date(task.submitted_at).toLocaleDateString()}</span>
                  ) : null}
                </div>
              </article>
            ))}
            {currentTasks.length === 0 ? <p className="empty-state">{selectedEmptyMessage}</p> : null}
            {currentTasks.length > visibleTasks.length ? (
              <button type="button" className="btn btn-secondary" onClick={() => setShowAllTasks(true)}>
                Show all {currentTasks.length} tasks
              </button>
            ) : showAllTasks && currentTasks.length > displayLimit ? (
              <button type="button" className="btn btn-secondary" onClick={() => setShowAllTasks(false)}>
                Show fewer tasks
              </button>
            ) : null}
          </div>
        </section>

        <section className="panel" style={{ marginBlock: 20 }}>
          <div className="panel-header">
            <div>
              <h2 className="panel-title">How writing support works</h2>
              <p className="panel-subtitle">Pip can coach during practice. In an exam, the ideas and words must be completely your own.</p>
            </div>
          </div>
          <div className="grid-3">
            <div className="state-card">
              <span className="state-dot ready" aria-hidden="true" />
              <strong>Practice Mode</strong>
              <p className="panel-subtitle">Get gentle prompts for grammar, vocabulary, and reflection while you draft.</p>
            </div>
            <div className="state-card error">
              <span className="state-dot error" aria-hidden="true" />
              <strong>Exam Mode</strong>
              <p className="panel-subtitle">Coaching is switched off, paste is blocked, and your work stays focused.</p>
            </div>
            <div className="state-card">
              <span className="state-dot empty" aria-hidden="true" />
              <strong>Pending feedback</strong>
              <p className="panel-subtitle">Only comments and scores approved by your teacher appear in feedback.</p>
            </div>
          </div>
        </section>
      </main>
    </ProductTopNav>
  );
}
