"use client";

import type {
  PersonalPracticeFocus,
  PersonalPracticeGenre,
  PersonalPracticeTask,
} from "@english-ai-writing/shared";
import Link from "next/link";
import { useEffect, useState } from "react";

import { ProductTopNav, studentNavigation, type AppShellUser } from "@/components/app-shell";
import { MascotGuide } from "@/components/student-mascot";
import { currentUser, logout } from "@/lib/auth";
import { generatePersonalPractice, listPersonalPractice, startFreeWriting } from "@/lib/school-data";
import { SkeletonScreen } from "@/components/skeleton";

const focusOptions: Array<{
  value: PersonalPracticeFocus;
  title: string;
  body: string;
  icon: string;
}> = [
  { value: "PAST_TENSE", title: "Past tense", body: "Keep story verbs in the right time.", icon: "↶" },
  { value: "STRONGER_FEELINGS", title: "Stronger feelings", body: "Show feelings with actions and details.", icon: "♡" },
  { value: "STORY_ORDER", title: "Story order", body: "Build a clear beginning, middle and ending.", icon: "≡" },
  { value: "BETTER_DESCRIPTIONS", title: "Better descriptions", body: "Help the reader picture the scene.", icon: "✦" },
];

const genreOptions: Array<{ value: PersonalPracticeGenre; label: string }> = [
  { value: "NARRATIVE", label: "Narrative" },
  { value: "DESCRIPTION", label: "Description" },
  { value: "LETTER", label: "Letter" },
];

type LoadState =
  | { status: "loading" }
  | { status: "denied"; message: string }
  | { status: "ready"; user: AppShellUser; items: PersonalPracticeTask[] };

function practiceHref(item: PersonalPracticeTask) {
  if (item.submission_id) return `/student/practice/${item.id}`;
  return `/student/tasks/${item.id}/practice`;
}

function practiceAction(item: PersonalPracticeTask) {
  if (!item.submission_id) return item.draft_saved_at ? "Continue writing" : "Start writing";
  if (item.marking_result?.status === "AI_MARKED") return "Read AI feedback";
  return "See marking progress";
}

function wordRangeLabel(item: Pick<PersonalPracticeTask, "word_minimum" | "word_maximum">) {
  if (item.word_minimum == null && item.word_maximum == null) return "No word limit";
  return `${item.word_minimum ?? "-"}-${item.word_maximum ?? "-"} words`;
}

export function StudentPractice() {
  const [state, setState] = useState<LoadState>({ status: "loading" });
  const [focus, setFocus] = useState<PersonalPracticeFocus>("STRONGER_FEELINGS");
  const [genre, setGenre] = useState<PersonalPracticeGenre>("NARRATIVE");
  const [duration, setDuration] = useState<10 | 15 | 20>(15);
  const [generated, setGenerated] = useState<PersonalPracticeTask | null>(null);
  const [generating, setGenerating] = useState(false);
  const [startingFreeWrite, setStartingFreeWrite] = useState(false);
  const [error, setError] = useState("");

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
        setState({ status: "denied", message: "Your role cannot access personal practice." });
        return;
      }
      const items = await listPersonalPractice();
      if (!active) return;
      setState({
        status: "ready",
        user: { display_name: user.display_name, email: user.email, role: user.role },
        items,
      });
    }
    void load().catch((loadError) => {
      setState({
        status: "denied",
        message: loadError instanceof Error ? loadError.message : "Unable to load personal practice.",
      });
    });
    return () => {
      active = false;
    };
  }, []);

  async function onGenerate() {
    setGenerating(true);
    setError("");
    try {
      const practice = await generatePersonalPractice({ focus, genre, duration_minutes: duration });
      setGenerated(practice);
      setState((current) => current.status === "ready"
        ? { ...current, items: [practice, ...current.items] }
        : current);
    } catch (generationError) {
      setError(generationError instanceof Error ? generationError.message : "Pip could not make a practice yet.");
    } finally {
      setGenerating(false);
    }
  }

  async function onStartFreeWriting() {
    setStartingFreeWrite(true);
    setError("");
    try {
      const practice = await startFreeWriting();
      window.location.href = `/student/tasks/${practice.id}/practice`;
    } catch (startError) {
      setError(startError instanceof Error ? startError.message : "Unable to open a blank page right now.");
      setStartingFreeWrite(false);
    }
  }

  async function onLogout() {
    await logout();
    window.location.href = "/login";
  }

  if (state.status === "loading") return <SkeletonScreen label="Preparing your practice desk..." variant="page" />;
  if (state.status === "denied") {
    return <main className="centered-state"><div><h1 className="screen-title">Unable to open practice</h1><p className="lead">{state.message}</p></div></main>;
  }

  return (
    <ProductTopNav
      active="My Practice"
      links={studentNavigation}
      onLogout={() => void onLogout()}
    >
      <main className="container personal-practice-page">
        <section className="practice-hero">
          <div>
            <p className="eyebrow">A practice made just for you</p>
            <h1>Choose one thing to practise today.</h1>
            <p className="lead">Pip will make one short writing challenge. You bring the ideas; AI helps you learn from the result.</p>
          </div>
          <MascotGuide
            title="Small practice makes strong writers."
            body="Pick one focus, one writing type, and the time you have. There are no streaks or leaderboards here—just useful practice."
            variant="compact"
          />
        </section>

        <section className="practice-freewrite" aria-label="Write freely without a prompt">
          <div>
            <strong>Just want to write?</strong>
            <span> Open a blank page with no topic, no word count, and no timer. Grammar checks and AI suggestions still work as you write.</span>
          </div>
          <button
            type="button"
            className="btn btn-secondary practice-freewrite-button"
            onClick={() => void onStartFreeWriting()}
            disabled={startingFreeWrite}
          >
            {startingFreeWrite ? "Opening…" : "Start writing freely"}
          </button>
        </section>

        <section className="practice-builder" aria-label="Build a personal practice">
          <div className="practice-step">
            <div className="practice-step-number">1</div>
            <div className="practice-step-copy">
              <h2>What would you like to practise?</h2>
              <p>Choose the skill you want Pip to focus on.</p>
            </div>
            <div className="practice-focus-grid">
              {focusOptions.map((option) => (
                <button
                  type="button"
                  key={option.value}
                  className={`practice-choice-card ${focus === option.value ? "selected" : ""}`}
                  aria-pressed={focus === option.value}
                  onClick={() => setFocus(option.value)}
                >
                  <span className="practice-choice-icon" aria-hidden="true">{option.icon}</span>
                  <strong>{option.title}</strong>
                  <small>{option.body}</small>
                </button>
              ))}
            </div>
          </div>

          <div className="practice-step practice-step-compact">
            <div className="practice-step-number">2</div>
            <div className="practice-step-copy">
              <h2>Choose a writing type</h2>
              <p>Keep it familiar or try something different.</p>
            </div>
            <div className="practice-pill-group" aria-label="Writing type">
              {genreOptions.map((option) => (
                <button type="button" key={option.value} className={genre === option.value ? "selected" : ""} onClick={() => setGenre(option.value)}>
                  {option.label}
                </button>
              ))}
            </div>
          </div>

          <div className="practice-step practice-step-compact">
            <div className="practice-step-number">3</div>
            <div className="practice-step-copy">
              <h2>How much time do you have?</h2>
              <p>This changes the suggested word target.</p>
            </div>
            <div className="practice-pill-group" aria-label="Practice time">
              {([10, 15, 20] as const).map((minutes) => (
                <button type="button" key={minutes} className={duration === minutes ? "selected" : ""} onClick={() => setDuration(minutes)}>
                  {minutes} min
                </button>
              ))}
            </div>
          </div>

          <div className="practice-generate-row">
            <div>
              <strong>Ready when you are.</strong>
              <span> AI will create the prompt; your story stays yours.</span>
            </div>
            <button type="button" className="btn btn-coral practice-generate-button" onClick={() => void onGenerate()} disabled={generating}>
              {generating ? "Pip is making it..." : "Make my practice"}
            </button>
          </div>
          {error ? <p className="practice-error" role="alert">{error}</p> : null}
        </section>

        {generated ? (
          <section className="generated-practice" aria-live="polite">
            <div className="generated-practice-badge">Your new challenge</div>
            <div className="generated-practice-main">
              <div>
                <p className="micro-label">{generated.practice_focus} · {wordRangeLabel(generated)}</p>
                <h2>{generated.title}</h2>
                <p>{generated.instruction}</p>
              </div>
              <Link className="btn btn-coral" href={`/student/tasks/${generated.id}/practice`}>Start writing</Link>
            </div>
            {generated.structure?.length ? (
              <ol className="generated-practice-steps">
                {generated.structure.map((step, index) => <li key={step}><span>{index + 1}</span>{step}</li>)}
              </ol>
            ) : null}
          </section>
        ) : null}

        <section className="practice-history">
          <div className="panel-header">
            <div><h2 className="panel-title">My recent practice</h2><p className="panel-subtitle">Continue a draft or read what the AI marker noticed.</p></div>
            <span className="badge-soft">{state.items.length} total</span>
          </div>
          <div className="practice-history-list">
            {state.items.map((item) => (
              <article key={item.id}>
                <div className="practice-history-icon" aria-hidden="true">✎</div>
                <div className="practice-history-copy">
                  <div className="task-meta"><span className="badge">{item.practice_focus}</span><span>{wordRangeLabel(item)}</span></div>
                  <h3>{item.title}</h3>
                  <p>{item.submission_id ? `Submitted ${item.submitted_at ? new Date(item.submitted_at).toLocaleDateString() : ""}` : item.draft_saved_at ? "Draft saved" : "Ready to start"}</p>
                </div>
                {item.marking_result?.status === "AI_MARKED" ? (
                  <strong className="practice-score">
                    {item.marking_result.total_score}
                    <small>/{item.rubric_total_score ?? "-"}</small>
                  </strong>
                ) : null}
                <Link className="btn btn-secondary" href={practiceHref(item)}>{practiceAction(item)}</Link>
              </article>
            ))}
            {state.items.length === 0 ? <div className="practice-empty">Your first personal practice will appear here.</div> : null}
          </div>
        </section>
      </main>
    </ProductTopNav>
  );
}
