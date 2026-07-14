"use client";

import type { StudentFeedback as StudentFeedbackPayload } from "@english-ai-writing/shared";
import Link from "next/link";
import { useEffect, useState } from "react";

import { ProductTopNav } from "@/components/app-shell";
import { MascotGuide } from "@/components/student-mascot";
import { ReadAloudButton } from "@/components/read-aloud-button";
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
  const [toast, setToast] = useState("");

  function showToast(message: string) {
    setToast(message);
    window.setTimeout(() => setToast(""), 2600);
  }

  async function load() {
    const user = await currentUser();
    if (!user) {
      window.location.href = "/login";
      return;
    }
    if (user.role !== "STUDENT") {
      setState({ status: "denied", message: "Your role cannot access student feedback." });
      return;
    }
    const feedback = await getStudentFeedback(submissionId);
    setState({ status: "ready", feedback });
    setResponses(Object.fromEntries(feedback.exercises.map((exercise) => [exercise.id, exercise.response_text ?? ""])));
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
    setNotice("Saving exercise...");
    await completeExercise(exerciseId, responses[exerciseId] ?? "");
    setNotice("Exercise saved.");
    showToast("Practice task saved.");
    void load().catch(() => undefined);
  }

  async function onLogout() {
    await logout();
    window.location.href = "/login";
  }

  if (state.status === "loading") {
    return <main className="loading-state">Loading feedback...</main>;
  }

  if (state.status === "denied") {
    return (
      <main className="centered-state">
        <div>
          <h1 className="screen-title">Feedback unavailable</h1>
          <p className="lead">{state.message}</p>
          <Link className="btn btn-primary" href="/student/writing" style={{ marginTop: 24 }}>
            Back to my writing
          </Link>
        </div>
      </main>
    );
  }

  const { feedback } = state;
  const review = feedback.review;
  const marking = feedback.marking_result;
  const scoreRows = [
    ["Content", review.content_score ?? marking.content_score],
    ["Language", review.language_score ?? marking.language_score],
    ["Organisation", review.organisation_score ?? marking.organisation_score],
    ["Total", review.total_score ?? marking.total_score],
  ] as const;

  return (
    <ProductTopNav
      active="Feedback"
      links={[
        { href: "/student/writing", label: "My Writing" },
        { href: `/student/feedback/${submissionId}`, label: "Feedback" },
      ]}
      onLogout={() => void onLogout()}
    >
      <main className="container" data-testid="released-feedback">
        <section className="hero student-feedback-hero">
          <div className="hero-copy">
            <p className="eyebrow">Your teacher has returned this story</p>
            <h1>Celebrate the progress. Then try one next step.</h1>
            <p className="lead">
              Read what worked, notice one pattern to improve, and practise it while the story is still fresh in your mind.
            </p>
          </div>
          <MascotGuide
            variant="feedback"
            title="Pip’s reflection tip"
            body={marking.weaknesses?.[0]
              ? `Your next focus is ${marking.weaknesses[0].toLowerCase()}. Read the teacher note, then try the short practice below.`
              : "Read your teacher’s note once for what went well, then again for the one change to try next time."}
          >
            <div className="feedback-score-strip" aria-label="Released scores">
              {scoreRows.map(([label, value]) => (
                <span key={label}><small>{label}</small><strong>{value ?? "-"}</strong></span>
              ))}
            </div>
          </MascotGuide>
        </section>

        {notice ? <p className="notice-success">{notice}</p> : null}

        <section className="editor-layout" style={{ marginBlock: 20 }}>
          <article className="document">
            <div className="task-meta" style={{ marginBottom: 22 }}>
              <span className="badge-success">Teacher released</span>
              <span className="badge-soft">{feedback.task.level}</span>
              <span className="badge-soft">{feedback.task.mode}</span>
            </div>
            <h2>{feedback.task.title}</h2>
            <ReadAloudButton taskId={feedback.task.id} text={feedback.submission.content_text} context="WRITING" label="Listen to my story" />
            {feedback.submission.content_text.split(/\n+/).slice(0, 8).map((paragraph, index) => (
              <p key={`${feedback.submission.id}-${index}`}>{paragraph}</p>
            ))}
          </article>

          <aside className="panel">
            <div className="panel-header">
              <div>
                <h2 className="panel-title">Teacher feedback</h2>
                <p className="panel-subtitle">Your teacher’s final comments, organised into three useful parts.</p>
              </div>
            </div>
            <div className="suggestion-list">
              <div className="rubric-item">
                <strong>Content</strong>
                <p className="panel-subtitle">{marking.content_feedback ?? "No content comment released."}</p>
              </div>
              <div className="rubric-item">
                <strong>Language</strong>
                <p className="panel-subtitle">{marking.language_feedback ?? "No language comment released."}</p>
              </div>
              <div className="rubric-item">
                <strong>Organisation</strong>
                <p className="panel-subtitle">{marking.organisation_feedback ?? "No organisation comment released."}</p>
              </div>
              {review.review_notes ? (
                <div className="rubric-item">
                  <span className="badge-success">Teacher note</span>
                  <p className="panel-subtitle">{review.review_notes}</p>
                </div>
              ) : null}
            </div>

            <div className="panel-header" style={{ marginTop: 24 }}>
              <div>
                <h2 className="panel-title">Practice tasks</h2>
                <p className="panel-subtitle">Short follow-up practice turns feedback into a stronger writing habit.</p>
              </div>
              <span className="badge-soft">{feedback.exercises.length} tasks</span>
            </div>
            <div className="suggestion-list">
              {feedback.exercises.map((exercise) => (
                <div key={exercise.id} className="task-card">
                  <div className="task-meta">
                    <span className={exercise.status === "COMPLETED" ? "badge-success" : "badge-soft"}>{exercise.status}</span>
                    <span className="badge-soft">{exercise.focus_area}</span>
                  </div>
                  <h3 className="panel-title">{exercise.title}</h3>
                  <p className="panel-subtitle">{exercise.prompt}</p>
                  <textarea
                    value={responses[exercise.id] ?? ""}
                    onChange={(event) => setResponses((current) => ({ ...current, [exercise.id]: event.target.value }))}
                    className="textarea"
                    placeholder="Write your answer"
                    rows={3}
                  />
                  <button type="button" className="btn btn-primary" onClick={() => void onCompleteExercise(exercise.id)}>
                    Save practice task
                  </button>
                </div>
              ))}
              {feedback.exercises.length === 0 ? <p className="empty-state">No practice tasks assigned.</p> : null}
            </div>
          </aside>
        </section>
      </main>
      <div className={`toast ${toast ? "show" : ""}`} role="status" aria-live="polite">{toast}</div>
    </ProductTopNav>
  );
}
