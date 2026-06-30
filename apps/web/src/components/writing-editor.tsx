"use client";

import type { GrammarSuggestion, SuggestionCheckMode, WritingMode, WritingWorkspace } from "@english-ai-writing/shared";
import { Extension } from "@tiptap/core";
import { Plugin, PluginKey, type EditorState } from "@tiptap/pm/state";
import { Decoration, DecorationSet } from "@tiptap/pm/view";
import { EditorContent, useEditor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";

import { currentUser, logout } from "@/lib/auth";
import {
  checkWritingSuggestions,
  countWords,
  getWritingWorkspace,
  recordExamEvent,
  saveDraft,
  submitWriting,
} from "@/lib/school-data";

type LoadState =
  | { status: "loading" }
  | { status: "denied"; message: string }
  | { status: "ready"; workspace: WritingWorkspace };

type SaveState = "idle" | "dirty" | "saving" | "saved" | "error" | "locked";

type SuggestionState = "idle" | "checking" | "ready" | "error";

type DisplaySuggestion = GrammarSuggestion & {
  sourceText: string;
};

type WritingEditorProps = {
  taskId: string;
  expectedMode: WritingMode;
};

const grammarSuggestionPluginKey = new PluginKey("grammarSuggestions");

const GrammarSuggestionHighlight = Extension.create({
  name: "grammarSuggestionHighlight",
  addProseMirrorPlugins() {
    const plugin: Plugin<DecorationSet> = new Plugin<DecorationSet>({
      key: grammarSuggestionPluginKey,
      state: {
        init: () => DecorationSet.empty,
        apply(transaction, oldDecorationSet, _oldState, newState) {
          const meta = transaction.getMeta(grammarSuggestionPluginKey) as
            | { suggestions?: GrammarSuggestion[] }
            | undefined;
          if (meta?.suggestions) {
            return DecorationSet.create(
              newState.doc,
              meta.suggestions.map((suggestion) =>
                Decoration.inline(
                  suggestion.offset + 1,
                  suggestion.offset + suggestion.length + 1,
                  {
                    class: "grammar-highlight",
                    "data-suggestion-id": suggestion.id,
                  },
                ),
              ),
            );
          }
          return oldDecorationSet.map(transaction.mapping, transaction.doc);
        },
      },
      props: {
        decorations(state: EditorState): DecorationSet {
          return plugin.getState(state) ?? DecorationSet.empty;
        },
      },
    });
    return [
      plugin,
    ];
  },
});

function formatTimer(seconds: number) {
  const minutes = Math.floor(seconds / 60).toString().padStart(2, "0");
  const remainder = Math.max(0, seconds % 60).toString().padStart(2, "0");
  return `${minutes}:${remainder}`;
}

function formatSuggestionSpan(value: string) {
  if (!value) return "(empty)";
  return value.replaceAll(" ", "<space>");
}

function formatReplacementLabel(value: string) {
  if (value === " ") return "single space";
  if (!value) return "(empty)";
  return value;
}

export function WritingEditor({ taskId, expectedMode }: WritingEditorProps) {
  const [state, setState] = useState<LoadState>({ status: "loading" });
  const [saveState, setSaveState] = useState<SaveState>("idle");
  const [wordCount, setWordCount] = useState(0);
  const [locked, setLocked] = useState(false);
  const [submissionId, setSubmissionId] = useState<string | null>(null);
  const [remainingSeconds, setRemainingSeconds] = useState<number | null>(null);
  const [suggestions, setSuggestions] = useState<DisplaySuggestion[]>([]);
  const [suggestionState, setSuggestionState] = useState<SuggestionState>("idle");
  const [suggestionServiceStatus, setSuggestionServiceStatus] = useState<"ok" | "unavailable">("ok");
  const [overviewStale, setOverviewStale] = useState(false);
  const [dismissedSuggestionIds, setDismissedSuggestionIds] = useState<Set<string>>(new Set());
  const suggestionsRef = useRef<DisplaySuggestion[]>([]);
  const dismissedSuggestionIdsRef = useRef<Set<string>>(new Set());
  const autosaveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const suggestionTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const submittedRef = useRef(false);

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
        setState({ status: "denied", message: "Your role cannot access the writing editor." });
        return;
      }
      const workspace = await getWritingWorkspace(taskId);
      if (workspace.task.mode !== expectedMode) {
        setState({ status: "denied", message: `This task is not a ${expectedMode} task.` });
        return;
      }
      setLocked(workspace.locked);
      setSubmissionId(workspace.submission?.id ?? null);
      setWordCount(workspace.submission?.word_count ?? workspace.draft?.word_count ?? 0);
      if (workspace.task.mode === "EXAM" && workspace.task.exam_duration_minutes) {
        setRemainingSeconds(workspace.task.exam_duration_minutes * 60);
      }
      setState({ status: "ready", workspace });
    }
    void load().catch((error) => {
      setState({
        status: "denied",
        message: error instanceof Error ? error.message : "Unable to load writing workspace.",
      });
    });
    return () => {
      active = false;
    };
  }, [expectedMode, taskId]);

  const initialContent = useMemo(() => {
    if (state.status !== "ready") return "";
    return (
      state.workspace.submission?.content_html ||
      state.workspace.draft?.content_html ||
      "<p></p>"
    );
  }, [state]);

  const editor = useEditor(
    {
      extensions: [StarterKit, GrammarSuggestionHighlight],
      content: initialContent,
      editable: !locked,
      immediatelyRender: false,
      editorProps: {
        attributes: {
          class:
            "min-h-[360px] rounded-md border border-ink/10 bg-paper px-4 py-4 text-base leading-7 text-ink outline-none",
        },
        handlePaste: () => {
          if (expectedMode === "EXAM") {
            void recordExamEvent(taskId, "PASTE_ATTEMPT", { source: "editor" }).catch(() => undefined);
            return true;
          }
          return false;
        },
      },
      onUpdate: ({ editor: updatedEditor }) => {
        const text = updatedEditor.getText();
        const words = countWords(text);
        setWordCount(words);
        if (!locked) {
          setSaveState("dirty");
          if (autosaveTimer.current) clearTimeout(autosaveTimer.current);
          autosaveTimer.current = setTimeout(() => {
            void autosave();
          }, 1200);
          if (expectedMode === "PRACTICE") {
            const retainedSuggestions = suggestionsRef.current.filter(
              (suggestion) =>
                text.slice(suggestion.offset, suggestion.offset + suggestion.length) ===
                suggestion.sourceText,
            );
            updateSuggestions(retainedSuggestions, updatedEditor);
            setOverviewStale(true);
            if (suggestionTimer.current) clearTimeout(suggestionTimer.current);
            suggestionTimer.current = setTimeout(() => {
              void runSuggestionCheck("CHANGED", updatedEditor.getText(), updatedEditor);
            }, 900);
          }
        }
      },
    },
    [initialContent, locked, expectedMode, taskId],
  );

  useEffect(() => {
    editor?.setEditable(!locked);
  }, [editor, locked]);

  useEffect(() => {
    if (expectedMode === "EXAM") {
      updateSuggestions([]);
    }
  }, [editor, expectedMode]);

  useEffect(() => {
    if (expectedMode !== "EXAM" || state.status !== "ready") return;
    const onBlur = () => {
      void recordExamEvent(taskId, "WINDOW_BLUR", { visibility_state: document.visibilityState }).catch(() => undefined);
    };
    const onFocus = () => {
      void recordExamEvent(taskId, "WINDOW_FOCUS", { visibility_state: document.visibilityState }).catch(() => undefined);
    };
    window.addEventListener("blur", onBlur);
    window.addEventListener("focus", onFocus);
    return () => {
      window.removeEventListener("blur", onBlur);
      window.removeEventListener("focus", onFocus);
    };
  }, [expectedMode, state.status, taskId]);

  useEffect(() => {
    if (remainingSeconds === null || locked) return;
    if (remainingSeconds <= 0) {
      if (!submittedRef.current) {
        void onSubmit();
      }
      return;
    }
    const timer = setTimeout(() => setRemainingSeconds((seconds) => (seconds === null ? null : seconds - 1)), 1000);
    return () => clearTimeout(timer);
  }, [remainingSeconds, locked]);

  useEffect(() => {
    return () => {
      if (autosaveTimer.current) clearTimeout(autosaveTimer.current);
      if (suggestionTimer.current) clearTimeout(suggestionTimer.current);
    };
  }, []);

  function applySuggestionDecorations(
    targetEditor: NonNullable<typeof editor>,
    nextSuggestions: GrammarSuggestion[],
  ) {
    targetEditor.view.dispatch(
      targetEditor.state.tr.setMeta(grammarSuggestionPluginKey, { suggestions: nextSuggestions }),
    );
  }

  function updateSuggestions(
    nextSuggestions: DisplaySuggestion[],
    targetEditor = editor,
  ) {
    suggestionsRef.current = nextSuggestions;
    setSuggestions(nextSuggestions);
    if (targetEditor) applySuggestionDecorations(targetEditor, nextSuggestions);
  }

  async function autosave() {
    if (!editor || locked) return;
    setSaveState("saving");
    try {
      await saveDraft(taskId, {
        content_html: editor.getHTML(),
        content_text: editor.getText(),
        word_count: countWords(editor.getText()),
      });
      setSaveState("saved");
    } catch {
      setSaveState("error");
    }
  }

  async function runSuggestionCheck(
    checkMode: SuggestionCheckMode,
    text = editor?.getText() ?? "",
    targetEditor = editor,
  ) {
    if (!targetEditor || locked || expectedMode !== "PRACTICE") return;
    if (!text.trim()) {
      updateSuggestions([], targetEditor);
      setSuggestionState("idle");
      return;
    }

    setSuggestionState("checking");
    try {
      const result = await checkWritingSuggestions(taskId, text, checkMode);
      const activeSuggestions = result.suggestions
        .filter((suggestion) => !dismissedSuggestionIdsRef.current.has(suggestion.id))
        .map((suggestion) => ({
          ...suggestion,
          sourceText: text.slice(suggestion.offset, suggestion.offset + suggestion.length),
        }));
      updateSuggestions(activeSuggestions, targetEditor);
      setSuggestionServiceStatus(result.service_status);
      setOverviewStale(false);
      setSuggestionState("ready");
    } catch {
      setSuggestionState("error");
      setSuggestionServiceStatus("unavailable");
    }
  }

  function removeSuggestion(suggestionId: string) {
    updateSuggestions(suggestionsRef.current.filter((suggestion) => suggestion.id !== suggestionId));
  }

  function dismissSuggestion(suggestion: DisplaySuggestion) {
    const nextDismissed = new Set(dismissedSuggestionIdsRef.current).add(suggestion.id);
    dismissedSuggestionIdsRef.current = nextDismissed;
    setDismissedSuggestionIds(nextDismissed);
    removeSuggestion(suggestion.id);
  }

  function acceptSuggestion(suggestion: DisplaySuggestion, replacement: string) {
    if (!editor || locked) return;
    editor.commands.insertContentAt(
      {
        from: suggestion.offset + 1,
        to: suggestion.offset + suggestion.length + 1,
      },
      replacement,
    );
    removeSuggestion(suggestion.id);
    setOverviewStale(true);
  }

  async function onSubmit() {
    if (!editor || locked || submittedRef.current) return;
    submittedRef.current = true;
    if (autosaveTimer.current) clearTimeout(autosaveTimer.current);
    if (suggestionTimer.current) clearTimeout(suggestionTimer.current);
    setSaveState("saving");
    try {
      const submission = await submitWriting(taskId, {
        content_html: editor.getHTML(),
        content_text: editor.getText(),
        word_count: countWords(editor.getText()),
      });
      setSubmissionId(submission.id);
      setLocked(true);
      updateSuggestions([], editor);
      setSaveState("locked");
    } catch {
      submittedRef.current = false;
      setSaveState("error");
    }
  }

  async function onLogout() {
    await logout();
    window.location.href = "/";
  }

  if (state.status === "loading") {
    return <main className="loading-state">Loading editor...</main>;
  }

  if (state.status === "denied") {
    return (
      <main className="centered-state">
        <h1 className="text-4xl font-semibold">Access denied</h1>
        <p className="mt-4 text-ink/65">{state.message}</p>
      </main>
    );
  }

  const { task } = state.workspace;
  const modeLabel = expectedMode === "PRACTICE" ? "Practice Mode" : "Exam Mode";

  return (
    <main className="app-shell" data-testid="writing-editor-page">
      <header className="app-header">
        <div>
          <p className="eyebrow">W F Joseph Lee Primary School</p>
          <h1 className="page-title">{task.title}</h1>
          <p className="mt-2 text-sm font-semibold text-coral">{modeLabel}</p>
        </div>
        <div className="flex items-center gap-3">
          {remainingSeconds !== null ? (
            <span
              className="rounded-md border border-coral/30 bg-paper px-4 py-2 text-sm font-semibold text-coral"
              data-testid="exam-timer"
            >
              {formatTimer(remainingSeconds)}
            </span>
          ) : null}
          <button type="button" onClick={onLogout} className="btn btn-secondary">
            Logout
          </button>
        </div>
      </header>

      <section className="grid gap-5 py-6 lg:grid-cols-[1fr_320px]">
        <div>
          <div className="mb-3 flex flex-wrap items-center gap-3 text-sm text-ink/65">
            <span>{wordCount} words</span>
            <span>Autosave: {saveState}</span>
            {locked ? <span className="font-semibold text-moss">Submitted and locked</span> : null}
          </div>
          {expectedMode === "EXAM" ? (
            <div
              className="mb-4 rounded-md border border-coral/20 bg-paper px-4 py-3 text-sm font-semibold text-coral"
              data-testid="exam-mode-notice"
            >
              This is Exam Mode. AI writing suggestions are disabled. Paste is blocked.
            </div>
          ) : null}
          <div data-testid="editor-content">
            <EditorContent editor={editor} />
          </div>
          <button
            type="button"
            onClick={() => void onSubmit()}
            disabled={locked}
            className="mt-4 btn btn-primary btn-lg disabled:cursor-not-allowed disabled:bg-ink/25"
            data-testid="submit-writing"
          >
            Submit writing
          </button>
          {locked && submissionId ? (
            <Link
              href={`/student/submissions/${submissionId}/feedback`}
              className="ml-3 mt-4 inline-flex btn btn-outline btn-lg"
              data-testid="view-feedback"
            >
              View released feedback
            </Link>
          ) : null}
        </div>

        <aside className="section-card">
          <h2 className="text-lg font-semibold text-ink">Writing instruction</h2>
          <p className="mt-3 text-sm leading-6 text-ink/70">{task.instruction}</p>
          <div className="mt-5 rounded-md bg-chalk p-3 text-sm text-ink/65">
            {task.word_minimum ?? "-"}-{task.word_maximum ?? "-"} words · {task.rubric_title ?? "School rubric"}
          </div>
          {expectedMode === "PRACTICE" ? (
            <div className="mt-5">
              <div className="flex items-center justify-between gap-3">
                <h3 className="text-base font-semibold text-ink">Suggestions</h3>
                <button
                  type="button"
                  onClick={() => void runSuggestionCheck("FULL")}
                  disabled={locked || suggestionState === "checking"}
                  className="rounded-md border border-moss/30 px-3 py-2 text-xs font-semibold text-moss disabled:cursor-not-allowed disabled:opacity-50"
                  data-testid="full-check-button"
                >
                  Full Check
                </button>
              </div>
              <div className="mt-2 flex items-center gap-2 text-xs font-semibold text-ink/55" data-testid="suggestion-status">
                <span>
                  {suggestionState === "checking"
                    ? "Checking..."
                    : suggestionState === "error"
                      ? "Unavailable"
                      : `${suggestions.length} active`}
                </span>
                {overviewStale ? <span className="text-coral">Overview stale</span> : null}
              </div>
              {suggestionServiceStatus === "unavailable" ? (
                <div className="mt-3 rounded-md border border-coral/25 bg-coral/5 p-3 text-sm text-coral">
                  Grammar service is unavailable. Writing and autosave continue.
                </div>
              ) : null}
              <div className="mt-3 space-y-3">
                {suggestions.length === 0 && suggestionState !== "checking" ? (
                  <div className="rounded-md border border-dashed border-ink/15 p-3 text-sm text-ink/55">
                    No active suggestions.
                  </div>
                ) : null}
                {suggestions.map((suggestion) => (
                  <article
                    key={suggestion.id}
                    className="rounded-md border border-ink/10 bg-chalk p-3"
                    data-testid="suggestion-card"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="text-sm font-semibold text-ink">{suggestion.short_message}</p>
                        <p className="mt-1 text-xs font-semibold uppercase tracking-[0.12em] text-moss">
                          {suggestion.category}
                        </p>
                      </div>
                      <button
                        type="button"
                        onClick={() => dismissSuggestion(suggestion)}
                        className="rounded-md border border-ink/10 px-2 py-1 text-xs font-semibold text-ink/55"
                        data-testid="dismiss-suggestion"
                      >
                        Dismiss
                      </button>
                    </div>
                    <p className="mt-3 text-sm leading-5 text-ink/70">{suggestion.message}</p>
                    <div className="mt-3 rounded-md bg-paper px-3 py-2 text-sm font-semibold text-coral">
                      {formatSuggestionSpan(suggestion.sourceText)}
                    </div>
                    <div className="mt-3 flex flex-wrap gap-2">
                      {suggestion.replacements.slice(0, 3).map((replacement) => (
                        <button
                          key={`${suggestion.id}-${replacement}`}
                          type="button"
                          onClick={() => acceptSuggestion(suggestion, replacement)}
                          className="btn btn-primary px-3 py-2 text-xs"
                          data-testid="accept-suggestion"
                        >
                          Accept: {formatReplacementLabel(replacement)}
                        </button>
                      ))}
                    </div>
                  </article>
                ))}
              </div>
            </div>
          ) : null}
        </aside>
      </section>
    </main>
  );
}
