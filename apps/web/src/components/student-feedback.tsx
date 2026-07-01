"use client";

import type { StudentFeedback as StudentFeedbackPayload } from "@english-ai-writing/shared";
import { useEffect, useState } from "react";

import { currentUser, logout } from "@/lib/auth";
import { completeExercise, getStudentFeedback } from "@/lib/school-data";

type FeedbackState =
  | { status: "loading" }
  | { status: "denied"; message: string }
  | { status: "ready"; feedback: StudentFeedbackPayload };

export function StudentFeedback({ submissionId }: { submissionId: string }) {
  const [state, setState] = useState<FeedbackState>({ status: "loading" });
  const [responses, setResponses] = useState<Record<string, string>>({});
  const [notice, setNotice] = useState("");

  async function load() {
    const user = await currentUser();
    if (!user) {
      window.location.href = "/";
      return;
    }
    if (user.role !== "STUDENT") {
      setState({ status: "denied", message: "Your role cannot access student feedback." });
      return;
    }
    const feedback = await getStudentFeedback(submissionId);
    setState({ status: "ready", feedback });
    setResponses(
      Object.fromEntries(feedback.exercises.map((exercise) => [exercise.id, exercise.response_text ?? ""])),
    );
  }

  useEffect(() => {
    void load().catch((error) => {
      setState({
        status: "denied",
        message: error instanceof Error ? error.message : "Feedback has not been released yet.",
      });
    });
  }, [submissionId]);

  async function onCompleteExercise(exerciseId: string) {
    setNotice("");
    await completeExercise(exerciseId, responses[exerciseId] ?? "");
    setNotice("Exercise saved.");
    await load();
  }

  async function onLogout() {
    await logout();
    window.location.href = "/";
  }

  if (state.status === "loading") {
    return <main className="loading-state">Loading feedback...</main>;
  }

  if (state.status === "denied") {
    return (
      <main className="centered-state">
        <h1 className="text-4xl font-semibold">Feedback unavailable</h1>
        <p className="mt-4 text-ink/65">{state.message}</p>
      </main>
    );
  }

  const { feedback } = state;
  const review = feedback.review;
  const marking = feedback.marking_result;

  return (
    <main className="feedback-shell" data-testid="released-feedback">
      <header className="portal-topbar">
        <div>
          <p className="page-kicker">W F Joseph Lee Primary School</p>
          <h1 className="page-title">{feedback.task.title}</h1>
          <div className="mt-3 flex flex-wrap gap-2">
            <span className="status-pill">Released feedback</span>
            <span className="status-pill-muted">{feedback.task.mode}</span>
          </div>
        </div>
        <div className="topbar-actions">
          <button type="button" onClick={onLogout} className="btn btn-secondary w-fit">
            Logout
          </button>
        </div>
      </header>

      {notice ? <div className="mt-5 notice-success">{notice}</div> : null}

      <section className="grid gap-4 py-5 md:grid-cols-4">
        {[
          ["Content", review.content_score ?? marking.content_score],
          ["Language", review.language_score ?? marking.language_score],
          ["Organisation", review.organisation_score ?? marking.organisation_score],
          ["Total", review.total_score ?? marking.total_score],
        ].map(([label, value]) => (
          <div key={label} className="metric-card">
            <p className="metric-label">{label}</p>
            <p className="metric-value">{value ?? "-"}</p>
            <p className="metric-hint">Teacher-released result</p>
          </div>
        ))}
      </section>

      <section className="grid gap-5 lg:grid-cols-[1fr_0.9fr]">
        <div className="section-card">
          <div className="panel-header">
            <div>
              <h2 className="panel-title">Feedback</h2>
              <p className="panel-subtitle">Teacher-controlled feedback from AI marking and review.</p>
            </div>
          </div>
          <div className="mt-4 grid gap-4 text-sm leading-6 text-ink/75">
            <p>{marking.content_feedback}</p>
            <p>{marking.language_feedback}</p>
            <p>{marking.organisation_feedback}</p>
            {review.review_notes ? <p className="font-semibold text-moss">{review.review_notes}</p> : null}
          </div>
        </div>

        <div className="section-card">
          <div className="panel-header">
            <div>
              <h2 className="panel-title">Post-writing exercises</h2>
              <p className="panel-subtitle">Complete focused follow-up practice after teacher release.</p>
            </div>
            <span className="status-pill-muted">{feedback.exercises.length} exercises</span>
          </div>
          <div className="mt-4 grid gap-4">
            {feedback.exercises.map((exercise) => (
              <div key={exercise.id} className="muted-panel" data-testid="exercise-card">
                <div className="flex items-center justify-between gap-3">
                  <p className="font-semibold text-ink">{exercise.title}</p>
                  <span className="text-xs font-semibold text-moss">{exercise.status}</span>
                </div>
                <p className="mt-2 text-sm text-ink/65">{exercise.focus_area}</p>
                <p className="mt-3 text-sm leading-6 text-ink/75">{exercise.prompt}</p>
                <textarea
                  value={responses[exercise.id] ?? ""}
                  onChange={(event) => setResponses((current) => ({ ...current, [exercise.id]: event.target.value }))}
                  rows={3}
                  className="mt-3 w-full form-control"
                  placeholder="Write your answer"
                  data-testid="exercise-response"
                />
                <button
                  type="button"
                  onClick={() => void onCompleteExercise(exercise.id)}
                  className="mt-3 btn btn-primary"
                  data-testid="complete-exercise"
                >
                  Save exercise
                </button>
              </div>
            ))}
            {feedback.exercises.length === 0 ? <p className="text-sm text-ink/60">No exercises assigned.</p> : null}
          </div>
        </div>
      </section>
    </main>
  );
}
