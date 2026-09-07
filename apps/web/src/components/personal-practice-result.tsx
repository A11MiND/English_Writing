"use client";

import type { PersonalPracticeResult } from "@english-ai-writing/shared";
import Link from "next/link";
import { useEffect, useState } from "react";

import { ProductTopNav, studentNavigation } from "@/components/app-shell";
import { MascotGuide } from "@/components/student-mascot";
import { ReadAloudButton } from "@/components/read-aloud-button";
import { currentUser, logout } from "@/lib/auth";
import { getPersonalPracticeResult } from "@/lib/school-data";
import { SkeletonScreen } from "@/components/skeleton";

type ResultState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; result: PersonalPracticeResult };

export function PersonalPracticeResultPage({ taskId }: { taskId: string }) {
  const [state, setState] = useState<ResultState>({ status: "loading" });

  useEffect(() => {
    let active = true;
    let timer: ReturnType<typeof setTimeout> | null = null;
    async function load() {
      const user = await currentUser();
      if (!user) {
        window.location.href = "/login";
        return;
      }
      if (user.role !== "STUDENT") throw new Error("Your role cannot open this practice result.");
      const result = await getPersonalPracticeResult(taskId);
      if (!active) return;
      setState({ status: "ready", result });
      if (result.marking_result?.status === "QUEUED" || result.marking_result?.status === "PROCESSING") {
        timer = setTimeout(() => void load(), 2500);
      }
    }
    void load().catch((error) => {
      if (active) setState({ status: "error", message: error instanceof Error ? error.message : "Unable to load feedback." });
    });
    return () => {
      active = false;
      if (timer) clearTimeout(timer);
    };
  }, [taskId]);

  async function onLogout() {
    await logout();
    window.location.href = "/login";
  }

  if (state.status === "loading") return <SkeletonScreen label="Opening your practice feedback..." variant="page" />;
  if (state.status === "error") return <main className="centered-state"><div><h1 className="screen-title">Feedback unavailable</h1><p className="lead">{state.message}</p></div></main>;

  const { task, submission, marking_result: marking } = state.result;
  const waiting = marking?.status === "QUEUED" || marking?.status === "PROCESSING";
  const failed = marking?.status === "AI_MARKING_FAILED";
  const scoreMaximum = (label: string) => task.rubric_dimensions.find(
    (dimension) => dimension.name.toLowerCase() === label.toLowerCase(),
  )?.max_score;

  return (
    <ProductTopNav
      active="My Practice"
      links={studentNavigation}
      onLogout={() => void onLogout()}
    >
      <main className="container practice-result-page">
        <section className="practice-result-heading">
          <div>
            <Link href="/student/practice" className="story-text-button">← Back to my practice</Link>
            <p className="eyebrow">Personal practice feedback</p>
            <h1>{task.title}</h1>
            <p className="lead">Focus: {task.practice_focus} · {submission?.word_count ?? 0} words</p>
          </div>
          {marking?.status === "AI_MARKED" ? (
            <div className="practice-total-score">
              <strong>{marking.total_score}</strong><span>out of {task.rubric_total_score}</span>
            </div>
          ) : null}
        </section>

        {waiting ? (
          <MascotGuide title="Pip is reading your writing." body="This normally takes a short moment. The page will update by itself when your feedback is ready." variant="feedback" />
        ) : failed ? (
          <section className="panel"><h2 className="panel-title">Marking needs another try</h2><p className="panel-subtitle">Your writing is safe. Please ask a teacher or try again later.</p></section>
        ) : !submission ? (
          <section className="panel"><h2 className="panel-title">This practice is not submitted yet.</h2><Link className="btn btn-primary" href={`/student/tasks/${task.id}/practice`}>Continue writing</Link></section>
        ) : marking?.status === "AI_MARKED" ? (
          <>
            <section className="practice-score-grid">
              {[
                ["Content", marking.content_score, marking.content_feedback, "sage"],
                ["Language", marking.language_score, marking.language_feedback, "lavender"],
                ["Organisation", marking.organisation_score, marking.organisation_feedback, "gold"],
              ].map(([label, score, feedback, tone]) => (
                <article className={`practice-score-card ${tone}`} key={String(label)}>
                  <div>
                    <span>{label}</span>
                    <strong>{score as number}<small>/{scoreMaximum(String(label)) ?? "-"}</small></strong>
                  </div>
                  <p>{feedback as string}</p>
                </article>
              ))}
            </section>

            <section className="practice-feedback-grid">
              <article className="panel practice-feedback-card">
                <p className="micro-label">What worked well</p>
                <h2>Keep doing these things</h2>
                <ul>{marking.strengths.map((item) => <li key={item}>{item}</li>)}</ul>
              </article>
              <article className="panel practice-feedback-card focus">
                <p className="micro-label">Your next step</p>
                <h2>Try this in your next story</h2>
                <ul>{marking.weaknesses.map((item) => <li key={item}>{item}</li>)}</ul>
              </article>
            </section>

            <section className="panel practice-writing-evidence">
              <div className="panel-header"><div><p className="micro-label">Your writing</p><h2 className="panel-title">Evidence from this practice</h2></div><ReadAloudButton taskId={task.id} text={submission.content_text} context="WRITING" label="Listen to my story" /></div>
              <div className="practice-writing-copy">{submission.content_text}</div>
              {marking.sentence_level_comments.length ? (
                <div className="practice-comment-list">
                  {marking.sentence_level_comments.slice(0, 4).map((comment, index) => (
                    <article key={`${comment.sentence}-${index}`}><span>{index + 1}</span><div><strong>{comment.category.toLowerCase()}</strong><q>{comment.sentence}</q><p>{comment.comment}</p></div></article>
                  ))}
                </div>
              ) : null}
            </section>

            <section className="practice-next-row">
              <MascotGuide title="One useful next step beats ten vague tips." body={marking.recommended_exercises[0]?.prompt ?? "Make another practice and focus on one thing at a time."} variant="compact" />
              <Link className="btn btn-coral" href="/student/practice">Make another practice</Link>
            </section>
          </>
        ) : null}
      </main>
    </ProductTopNav>
  );
}
