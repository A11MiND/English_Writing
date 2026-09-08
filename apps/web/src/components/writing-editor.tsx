"use client";

import type {
  GrammarSuggestion,
  ParagraphSuggestion,
  StudentRewrite,
  StudentRewriteGoal,
  SuggestionCheckMode,
  WritingMode,
  WritingWorkspace,
} from "@english-ai-writing/shared";
import { Extension } from "@tiptap/core";
import { Plugin, PluginKey, type EditorState } from "@tiptap/pm/state";
import { Decoration, DecorationSet } from "@tiptap/pm/view";
import { EditorContent, useEditor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";

import { currentUser, logout } from "@/lib/auth";
import {
  GrammarSuggestionPopover,
  type AnchoredGrammarSuggestion,
} from "@/components/grammar-suggestion-popover";
import { ReadAloudButton } from "@/components/read-aloud-button";
import { WritingLanguageSupport } from "@/components/writing-language-support";
import { SkeletonScreen } from "@/components/skeleton";
import { REWRITE_MAX_CHARS, locateCurrentRange, sentenceAroundOffset } from "@/lib/writing-editor-text";
import {
  checkParagraphSuggestions,
  checkWritingSuggestions,
  countWords,
  getWritingWorkspace,
  recordExamEvent,
  rewriteStudentText,
  saveDraft,
  submitWriting,
} from "@/lib/school-data";

type LoadState =
  | { status: "loading" }
  | { status: "denied"; message: string }
  | { status: "ready"; workspace: WritingWorkspace };

type SaveState = "idle" | "dirty" | "saving" | "saved" | "error" | "locked";

type SuggestionState = "idle" | "checking" | "ready" | "error";

type ParagraphState = "idle" | "waiting" | "checking" | "ready" | "error";

type RewriteState = "idle" | "loading" | "ready" | "error";

type DisplaySuggestion = GrammarSuggestion & {
  sourceText: string;
};

type WritingEditorProps = {
  taskId: string;
  expectedMode: WritingMode;
};

const grammarSuggestionPluginKey = new PluginKey("grammarSuggestions");

const rewriteGoals: Array<{ value: StudentRewriteGoal; label: string; hint: string }> = [
  { value: "CLEARER", label: "Clearer", hint: "Make the meaning easier to follow." },
  { value: "MORE_DESCRIPTIVE", label: "More descriptive", hint: "Show the scene with precise details." },
  { value: "FRIENDLIER", label: "Friendlier", hint: "Use a warm, natural voice." },
  { value: "MORE_FORMAL", label: "More formal", hint: "Use a careful school-writing voice." },
];

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
                    class: `grammar-highlight grammar-highlight-${suggestion.level.toLowerCase()}`,
                    "data-suggestion-id": suggestion.id,
                    "data-suggestion-level": suggestion.level,
                    role: "button",
                    tabindex: "0",
                    "aria-label": `${suggestion.level === "WORD" ? "Word" : "Sentence"} suggestion: ${suggestion.short_message}. Press Enter to review.`,
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

function formatReplacementLabel(value: string) {
  if (value === " ") return "single space";
  if (!value) return "(empty)";
  return value;
}

function canAnalyseParagraph(text: string) {
  const sentences = text.split(/[.!?]+(?:\s+|$)/).filter((sentence) => sentence.trim().length > 0);
  return sentences.length >= 3 && countWords(text) >= 20;
}

export function WritingEditor({ taskId, expectedMode }: WritingEditorProps) {
  const [state, setState] = useState<LoadState>({ status: "loading" });
  const [saveState, setSaveState] = useState<SaveState>("idle");
  const [wordCount, setWordCount] = useState(0);
  const [locked, setLocked] = useState(false);
  const lockedRef = useRef(false);
  const [submissionId, setSubmissionId] = useState<string | null>(null);
  const [remainingSeconds, setRemainingSeconds] = useState<number | null>(null);
  const [suggestions, setSuggestions] = useState<DisplaySuggestion[]>([]);
  const [suggestionState, setSuggestionState] = useState<SuggestionState>("idle");
  const [suggestionServiceStatus, setSuggestionServiceStatus] = useState<"ok" | "unavailable">("ok");
  const [overviewStale, setOverviewStale] = useState(false);
  const [dismissedSuggestionIds, setDismissedSuggestionIds] = useState<Set<string>>(new Set());
  const suggestionsRef = useRef<DisplaySuggestion[]>([]);
  const dismissedSuggestionIdsRef = useRef<Set<string>>(new Set());
  const [anchoredSuggestion, setAnchoredSuggestion] = useState<AnchoredGrammarSuggestion | null>(null);
  const suggestionPopoverCloseTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const autosaveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const suggestionTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const paragraphTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [paragraphSuggestions, setParagraphSuggestions] = useState<ParagraphSuggestion[]>([]);
  const [paragraphState, setParagraphState] = useState<ParagraphState>("idle");
  const [paragraphServiceStatus, setParagraphServiceStatus] = useState<"ok" | "fallback">("ok");
  const [paragraphEligible, setParagraphEligible] = useState(false);
  const [paragraphStale, setParagraphStale] = useState(false);
  const lastParagraphTextRef = useRef("");
  const dismissedParagraphIdsRef = useRef<Set<string>>(new Set());
  const submittedRef = useRef(false);
  const [submitModalOpen, setSubmitModalOpen] = useState(false);
  const [toast, setToast] = useState("");
  const [studentName, setStudentName] = useState("Student");
  const [polishOpen, setPolishOpen] = useState(false);
  const [rewriteGoal, setRewriteGoal] = useState<StudentRewriteGoal>("MORE_DESCRIPTIVE");
  const [rewriteState, setRewriteState] = useState<RewriteState>("idle");
  const [rewrite, setRewrite] = useState<StudentRewrite | null>(null);
  const [rewriteError, setRewriteError] = useState("");
  const rewriteRangeRef = useRef<{ from: number; to: number; text: string } | null>(null);

  function showToast(message: string) {
    setToast(message);
    window.setTimeout(() => setToast(""), 2600);
  }

  function clearSuggestionPopoverClose() {
    if (suggestionPopoverCloseTimer.current) {
      clearTimeout(suggestionPopoverCloseTimer.current);
      suggestionPopoverCloseTimer.current = null;
    }
  }

  function closeSuggestionPopover() {
    clearSuggestionPopoverClose();
    setAnchoredSuggestion(null);
  }

  function scheduleSuggestionPopoverClose() {
    clearSuggestionPopoverClose();
    suggestionPopoverCloseTimer.current = setTimeout(() => {
      setAnchoredSuggestion(null);
    }, 180);
  }

  function suggestionDecorationTarget(target: EventTarget | null) {
    if (!(target instanceof Element)) return null;
    return target.closest<HTMLElement>("[data-suggestion-id]");
  }

  function openSuggestionPopover(target: HTMLElement) {
    clearSuggestionPopoverClose();
    const suggestionId = target.dataset.suggestionId;
    const suggestion = suggestionsRef.current.find((item) => item.id === suggestionId);
    if (!suggestion) return;

    const rect = target.getBoundingClientRect();
    const width = Math.min(320, window.innerWidth - 24);
    const estimatedHeight = suggestion.replacements[0] ? 270 : 190;
    const preferredTop = rect.bottom + 10;
    const top = preferredTop + estimatedHeight <= window.innerHeight - 12
      ? preferredTop
      : Math.max(12, rect.top - estimatedHeight - 10);
    const left = Math.min(
      Math.max(12, rect.left + rect.width / 2 - width / 2),
      window.innerWidth - width - 12,
    );
    setAnchoredSuggestion({ suggestion, top, left });
  }

  useEffect(() => {
    if (!anchoredSuggestion) return;
    const closeOnViewportChange = () => closeSuggestionPopover();
    const closeOnOutsidePointer = (event: PointerEvent) => {
      if (!(event.target instanceof Element)) return;
      if (event.target.closest(".grammar-suggestion-popover, [data-suggestion-id]")) return;
      closeSuggestionPopover();
    };
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") closeSuggestionPopover();
    };
    window.addEventListener("resize", closeOnViewportChange);
    window.addEventListener("scroll", closeOnViewportChange, true);
    document.addEventListener("pointerdown", closeOnOutsidePointer);
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      window.removeEventListener("resize", closeOnViewportChange);
      window.removeEventListener("scroll", closeOnViewportChange, true);
      document.removeEventListener("pointerdown", closeOnOutsidePointer);
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, [anchoredSuggestion]);

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
        setState({ status: "denied", message: "Your role cannot access the writing editor." });
        return;
      }
      setStudentName(user.display_name);
      const workspace = await getWritingWorkspace(taskId);
      if (workspace.task.mode !== expectedMode) {
        setState({ status: "denied", message: `This task is not a ${expectedMode} task.` });
        return;
      }
      lockedRef.current = workspace.locked;
      setLocked(workspace.locked);
      if (workspace.locked) setSaveState("locked");
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
          class: expectedMode === "EXAM" ? "exam-editor-content" : "writing-document",
          role: "textbox",
          "aria-label": expectedMode === "EXAM" ? "Exam writing editor" : "Practice writing editor",
          "aria-multiline": "true",
        },
        handlePaste: () => {
          if (expectedMode === "EXAM") {
            void recordExamEvent(taskId, "PASTE_ATTEMPT", { source: "editor" }).catch(() => undefined);
            showToast("Paste is blocked in exam mode and recorded for teacher review.");
            return true;
          }
          return false;
        },
        handleDOMEvents: {
          mouseover: (_view, event) => {
            const target = suggestionDecorationTarget(event.target);
            if (target) openSuggestionPopover(target);
            return false;
          },
          mouseout: (_view, event) => {
            if (suggestionDecorationTarget(event.target)) scheduleSuggestionPopoverClose();
            return false;
          },
          click: (_view, event) => {
            const target = suggestionDecorationTarget(event.target);
            if (!target) return false;
            event.preventDefault();
            openSuggestionPopover(target);
            return true;
          },
          focusin: (_view, event) => {
            const target = suggestionDecorationTarget(event.target);
            if (target) openSuggestionPopover(target);
            return false;
          },
          keydown: (_view, event) => {
            const keyboardEvent = event as KeyboardEvent;
            const target = suggestionDecorationTarget(event.target);
            if (!target || !["Enter", " "].includes(keyboardEvent.key)) return false;
            keyboardEvent.preventDefault();
            openSuggestionPopover(target);
            return true;
          },
        },
      },
      onUpdate: ({ editor: updatedEditor }) => {
        const text = updatedEditor.getText();
        const words = countWords(text);
        setWordCount(words);
        if (!lockedRef.current) {
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

            const eligibleForParagraph = canAnalyseParagraph(text);
            setParagraphEligible(eligibleForParagraph);
            if (paragraphTimer.current) clearTimeout(paragraphTimer.current);
            if (eligibleForParagraph) {
              setParagraphStale(true);
              setParagraphState("waiting");
              paragraphTimer.current = setTimeout(() => {
                void runParagraphCheck(updatedEditor.getText());
              }, 2800);
            } else {
              setParagraphSuggestions([]);
              setParagraphState("idle");
              setParagraphStale(false);
              lastParagraphTextRef.current = "";
            }
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
    if (!editor || expectedMode !== "PRACTICE" || locked) return;
    const text = editor.getText();
    const eligibleForParagraph = canAnalyseParagraph(text);
    setParagraphEligible(eligibleForParagraph);
    if (!eligibleForParagraph || lastParagraphTextRef.current === text) return;
    setParagraphState("waiting");
    paragraphTimer.current = setTimeout(() => {
      void runParagraphCheck(text);
    }, 1400);
    return () => {
      if (paragraphTimer.current) clearTimeout(paragraphTimer.current);
    };
  }, [editor, expectedMode, locked]);

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
        void onSubmit("TIMER");
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
      if (paragraphTimer.current) clearTimeout(paragraphTimer.current);
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
    if (!editor || lockedRef.current) return;
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

  async function runParagraphCheck(text = editor?.getText() ?? "") {
    if (locked || expectedMode !== "PRACTICE") return;
    if (!canAnalyseParagraph(text)) {
      setParagraphEligible(false);
      setParagraphSuggestions([]);
      setParagraphState("idle");
      setParagraphStale(false);
      return;
    }

    setParagraphEligible(true);
    setParagraphState("checking");
    try {
      const result = await checkParagraphSuggestions(taskId, text);
      setParagraphSuggestions(
        result.suggestions.filter((suggestion) => !dismissedParagraphIdsRef.current.has(suggestion.id)),
      );
      setParagraphServiceStatus(result.service_status);
      setParagraphState("ready");
      setParagraphStale(false);
      lastParagraphTextRef.current = text;
    } catch {
      setParagraphState("error");
      setParagraphStale(false);
    }
  }

  function dismissParagraphSuggestion(suggestionId: string) {
    dismissedParagraphIdsRef.current = new Set(dismissedParagraphIdsRef.current).add(suggestionId);
    setParagraphSuggestions((current) => current.filter((suggestion) => suggestion.id !== suggestionId));
  }

  function checkAllLanguage() {
    const text = editor?.getText() ?? "";
    void runSuggestionCheck("FULL", text);
    if (canAnalyseParagraph(text)) void runParagraphCheck(text);
  }

  function removeSuggestion(suggestionId: string) {
    updateSuggestions(suggestionsRef.current.filter((suggestion) => suggestion.id !== suggestionId));
    setAnchoredSuggestion((current) => current?.suggestion.id === suggestionId ? null : current);
  }

  function dismissSuggestion(suggestion: DisplaySuggestion) {
    const nextDismissed = new Set(dismissedSuggestionIdsRef.current).add(suggestion.id);
    dismissedSuggestionIdsRef.current = nextDismissed;
    setDismissedSuggestionIds(nextDismissed);
    removeSuggestion(suggestion.id);
  }

  function acceptSuggestion(suggestion: DisplaySuggestion, replacement: string) {
    if (!editor || locked) return;
    const expectedFrom = suggestion.offset + 1;
    const expectedTo = suggestion.offset + suggestion.length + 1;
    const located = locateCurrentRange(editor.state.doc, expectedFrom, expectedTo, suggestion.sourceText);
    if (!located) {
      removeSuggestion(suggestion.id);
      showToast("That suggestion is out of date. Checking your writing again…");
      checkAllLanguage();
      return;
    }
    editor.commands.insertContentAt(located, replacement);
    removeSuggestion(suggestion.id);
    setOverviewStale(true);
  }

  function applyAnchoredSuggestion(replacement: string) {
    if (!anchoredSuggestion) return;
    acceptSuggestion(anchoredSuggestion.suggestion, replacement);
    closeSuggestionPopover();
    showToast(`Changed “${anchoredSuggestion.suggestion.sourceText}” to “${replacement}”.`);
  }

  function dismissAnchoredSuggestion() {
    if (!anchoredSuggestion) return;
    dismissSuggestion(anchoredSuggestion.suggestion);
    closeSuggestionPopover();
  }

  function selectedWriting() {
    if (!editor) return null;
    const { from, to, $from } = editor.state.selection;
    if (from !== to) {
      const text = editor.state.doc.textBetween(from, to, " ").trim();
      return text ? { text, from, to } : null;
    }
    // No selection: use the sentence under the cursor, not the whole paragraph.
    // A "rewrite" is meant to cover a sentence or two - handing the model an
    // entire draft asked it to rewrite an essay as if it were one sentence,
    // and it answered with an analysis instead, which then got inserted
    // verbatim in place of the draft.
    const paragraphFrom = $from.start();
    const paragraphTo = $from.end();
    const paragraph = editor.state.doc.textBetween(paragraphFrom, paragraphTo, " ");
    const sentence = sentenceAroundOffset(paragraph, $from.pos - paragraphFrom);
    if (!sentence) return null;
    return { text: sentence.text, from: paragraphFrom + sentence.start, to: paragraphFrom + sentence.end };
  }

  async function runRewrite() {
    if (!editor || locked) return;
    const target = selectedWriting();
    if (!target) {
      showToast("Write a sentence first, or select the words you want Pip to help with.");
      editor.commands.focus();
      return;
    }
    if (target.text.length > REWRITE_MAX_CHARS) {
      showToast("That's too long for Pip to rewrite at once. Select one sentence instead.");
      return;
    }
    setRewriteState("loading");
    setRewriteError("");
    setRewrite(null);
    rewriteRangeRef.current = { from: target.from, to: target.to, text: target.text };
    try {
      const result = await rewriteStudentText({ task_id: taskId, text: target.text, goal: rewriteGoal });
      setRewrite(result);
      setRewriteState("ready");
    } catch (error) {
      setRewriteError(error instanceof Error ? error.message : "Pip could not make a suggestion yet.");
      setRewriteState("error");
    }
  }

  function applyRewrite() {
    if (!editor || !rewrite || !rewriteRangeRef.current || locked) return;
    const { from, to, text } = rewriteRangeRef.current;
    // Same staleness guard as accepting a grammar suggestion: the draft can have
    // changed while Pip's rewrite was loading (kept typing, tried another goal,
    // undid something). Refuse rather than splice the rewrite into the wrong text.
    const located = locateCurrentRange(editor.state.doc, from, to, text);
    if (!located) {
      setRewrite(null);
      setRewriteState("idle");
      rewriteRangeRef.current = null;
      showToast("Your draft changed since this suggestion was made, so it was not applied.");
      return;
    }
    editor.commands.insertContentAt(located, rewrite.revised);
    setRewrite(null);
    setRewriteState("idle");
    rewriteRangeRef.current = null;
    showToast("Pip's suggestion was added. You can undo it any time.");
  }

  function undoRewrite() {
    if (!editor) return;
    editor.commands.undo();
    showToast("Last change undone.");
  }

  async function onSubmit(submissionTrigger: "MANUAL" | "TIMER" = "MANUAL") {
    if (!editor || locked || submittedRef.current) return;
    submittedRef.current = true;
    if (autosaveTimer.current) clearTimeout(autosaveTimer.current);
    if (suggestionTimer.current) clearTimeout(suggestionTimer.current);
    if (paragraphTimer.current) clearTimeout(paragraphTimer.current);
    setSaveState("saving");
    try {
      const submission = await submitWriting(taskId, {
        content_html: editor.getHTML(),
        content_text: editor.getText(),
        word_count: countWords(editor.getText()),
        submission_trigger: submissionTrigger,
      });
      setSubmissionId(submission.id);
      setLocked(true);
      lockedRef.current = true;
      updateSuggestions([], editor);
      setSaveState("locked");
      setSubmitModalOpen(false);
      showToast("Writing submitted and locked.");
    } catch (error) {
      submittedRef.current = false;
      setSaveState("error");
      showToast(error instanceof Error ? error.message : "Submission failed. Please try again.");
    }
  }

  async function onLogout() {
    await logout();
    window.location.href = "/login";
  }

  if (state.status === "loading") {
    return <SkeletonScreen label="Loading editor..." variant="page" />;
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

  if (expectedMode === "EXAM") {
    return (
      <main className="exam-page" data-testid="writing-editor-page">
        <section className="exam-shell">
          <section className="exam-main">
            <header className="exam-header">
              <div>
                <p className="micro-label">Exam Mode</p>
                <h1 className="screen-title" style={{ color: "var(--bg)" }}>{task.title}</h1>
                <div className="task-meta" style={{ marginTop: 12 }}>
                  <span className="badge-soft">{task.rubric_title ?? "School rubric"}</span>
                  {locked ? <span className="badge-success">Submitted and locked</span> : null}
                </div>
              </div>
              {remainingSeconds !== null ? (
                <div className="timer" data-testid="exam-timer">{formatTimer(remainingSeconds)}</div>
              ) : null}
            </header>

            <EditorContent editor={editor} />

            <footer className="exam-footer">
              <div className="task-meta">
                <span className="badge-soft">{wordCount} {wordCount === 1 ? "word" : "words"}</span>
                <span className="badge-soft">{saveState === "locked" ? "Submitted safely" : `Autosave ${saveState}`}</span>
                <span className="badge-danger">Suggestions off</span>
              </div>
              <button
                className="btn btn-primary"
                type="button"
                disabled={locked}
                onClick={() => setSubmitModalOpen(true)}
                data-testid="submit-writing"
              >
                Submit writing
              </button>
            </footer>
          </section>

          <aside className="exam-rail">
            <Link className="brand" href="/student/writing">
              <img className="brand-mark brand-mark-fox" src="/brand-fox.png" alt="" />
              <span className="brand-text">
                <span className="brand-title">English AI Writing</span>
                <span className="brand-subtitle">Exam safeguards active</span>
              </span>
            </Link>
            <div className="exam-rule" style={{ marginTop: 24 }}>
              <p className="micro-label">Writing prompt</p>
              <p style={{ margin: "10px 0 0" }}>{task.instruction}</p>
              <p className="panel-subtitle" style={{ marginTop: 12 }}>
                {task.word_minimum ?? "-"}-{task.word_maximum ?? "-"} words
              </p>
            </div>
            <div className="suggestion-list" style={{ marginTop: 16 }}>
              <div className="exam-rule">AI suggestions and rewrite support are disabled.</div>
              <div className="exam-rule">Paste attempts are blocked and logged for teacher review.</div>
              <div className="exam-rule">Window focus changes are recorded during the writing session.</div>
              <Link
                className="btn btn-secondary"
                href="/student/writing"
                style={{ background: "rgba(255,255,255,0.10)", color: "var(--bg)", borderColor: "rgba(255,255,255,0.15)" }}
              >
                Back to my writing
              </Link>
              {locked && submissionId ? (
                <Link
                  href={`/student/feedback/${submissionId}`}
                  className="btn btn-primary"
                  data-testid="view-feedback"
                >
                  View released feedback
                </Link>
              ) : null}
            </div>
          </aside>
        </section>

        <div className={`modal-backdrop ${submitModalOpen ? "open" : ""}`} role="dialog" aria-modal="true" aria-labelledby="submit-title">
          <div className="modal">
            <p className="eyebrow">Final submission</p>
            <h2 className="panel-title" id="submit-title" style={{ fontSize: "var(--text-xl)", marginTop: 8 }}>
              Submit this exam writing?
            </h2>
            <p className="panel-subtitle" style={{ marginTop: 12 }}>
              Your writing will be locked and sent to your teacher. You cannot edit it after submission.
            </p>
            <div className="row-actions">
              <button className="btn btn-secondary" type="button" onClick={() => setSubmitModalOpen(false)}>
                Keep checking
              </button>
              <button className="btn btn-primary" type="button" onClick={() => void onSubmit()}>
                Submit now
              </button>
            </div>
          </div>
        </div>
        <div className={`toast ${toast ? "show" : ""}`} role="status" aria-live="polite">{toast}</div>
      </main>
    );
  }

  const hasWordTarget = task.word_minimum != null || task.word_maximum != null;
  const minimumWords = task.word_minimum ?? 120;
  const maximumWords = task.word_maximum ?? 180;
  const goalProgress = Math.min(100, Math.round((wordCount / Math.max(1, minimumWords)) * 100));
  const leadSuggestion = suggestions[0];
  const isPersonalPractice = task.assigned_classes.includes("My Practice");

  return (
    <main className="story-writer" data-testid="writing-editor-page">
      <header className="story-writer-header">
        <Link className="story-brand" href="/student/writing" aria-label="Back to my writing">
          <img className="story-brand-mark" src="/brand-fox.png" alt="" />
          <span>
            <strong>English AI Writing</strong>
            <small>A writing studio for young learners</small>
          </span>
        </Link>

        <ol className="writing-steps" aria-label="Writing progress">
          {(["Draft", "Polish", "Share"] as const).map((label, index) => {
            const stage = locked ? 2 : (hasWordTarget ? wordCount >= minimumWords : wordCount > 0) ? 1 : 0;
            return (
              <li
                key={label}
                className={index === stage ? "active" : index < stage ? "done" : ""}
                aria-current={index === stage ? "step" : undefined}
              >
                <span>{index + 1}</span>
                {label}
              </li>
            );
          })}
        </ol>

        <div className="story-profile">
          <span className="story-profile-name">{studentName}</span>
          <button type="button" onClick={onLogout} className="story-text-button">Logout</button>
        </div>
      </header>

      <section className="story-prompt" aria-labelledby="story-task-title">
        {task.image_url ? <img className="story-prompt-image" src={task.image_url} alt="Illustration for this writing prompt" /> : null}
        <div className="story-prompt-copy">
          <p>{isPersonalPractice ? "My personal practice" : "Writing task"}</p>
          <h1 id="story-task-title">{task.title}</h1>
          <div>{task.instruction}</div>
          <ReadAloudButton taskId={task.id} text={task.instruction} context="PROMPT" label="Listen to the prompt" />
        </div>
        <span className="story-word-target">{hasWordTarget ? `${minimumWords}-${maximumWords} words` : "No word limit"}</span>
      </section>

      <section className="story-workspace">
        <section className="story-paper" aria-label="Writing canvas">
          <div className="story-paper-heading">
            <div>
              <p>Practice draft</p>
              <h2>My first draft</h2>
            </div>
            <span>{hasWordTarget ? `${wordCount} of ${minimumWords}-${maximumWords} words` : `${wordCount} words written`}</span>
          </div>

          <div className="story-editor-frame" data-testid="editor-content">
            <EditorContent editor={editor} />
          </div>

          <footer className="story-paper-footer">
            <p aria-live="polite">
              {saveState === "locked" ? <strong>Submitted safely</strong> : <>Autosave: <strong>{saveState}</strong></>}
            </p>
            <div className="story-paper-actions">
              <ReadAloudButton taskId={task.id} text={editor?.getText() ?? ""} context="WRITING" label="Listen to my writing" />
              {locked && submissionId ? (
                <Link href={isPersonalPractice ? `/student/practice/${task.id}` : `/student/feedback/${submissionId}`} className="btn btn-secondary" data-testid="view-feedback">
                  {isPersonalPractice ? "View AI feedback" : "View feedback"}
                </Link>
              ) : null}
              <button
                type="button"
                onClick={() => setSubmitModalOpen(true)}
                disabled={locked}
                className="btn btn-secondary"
                data-testid="submit-writing"
              >
                {locked ? "Submitted" : isPersonalPractice ? "Finish for AI feedback" : "Submit to teacher"}
              </button>
            </div>
          </footer>
        </section>

        <aside className="story-coach-rail" aria-label="Writing support">
          <section className="story-goal-card">
            {hasWordTarget ? (
              <>
                <div>
                  <p>Today&apos;s writing goal</p>
                  <strong>{wordCount} / {minimumWords} words</strong>
                </div>
                <div className="story-progress" role="progressbar" aria-valuemin={0} aria-valuemax={minimumWords} aria-valuenow={wordCount}>
                  <span style={{ width: `${goalProgress}%` }} />
                </div>
              </>
            ) : (
              <div>
                <p>Free writing</p>
                <strong>{wordCount} {wordCount === 1 ? "word" : "words"} so far</strong>
              </div>
            )}
          </section>

          {!polishOpen ? <section className="story-coach-card">
            <div className="story-coach-heading">
              <img className="story-coach-fox" src="/ai-coach-fox.png" alt="AI Coach fox" />
              <div>
                <h2>AI Coach</h2>
                <p>One helpful idea at a time</p>
              </div>
            </div>
            <blockquote>
              {leadSuggestion ? leadSuggestion.short_message : "Your ideas are taking shape."}
            </blockquote>
            <p>
              {leadSuggestion
                ? leadSuggestion.message
                : "Keep writing. I will check your language after a short pause."}
            </p>
            {leadSuggestion?.replacements[0] ? (
              <button
                type="button"
                className="story-coach-action"
                onClick={() => acceptSuggestion(leadSuggestion, leadSuggestion.replacements[0])}
                data-testid="accept-suggestion"
              >
                Use {formatReplacementLabel(leadSuggestion.replacements[0])}
              </button>
            ) : null}
          </section> : null}

          {!polishOpen ? <WritingLanguageSupport
            suggestions={suggestions}
            suggestionState={suggestionState}
            suggestionServiceStatus={suggestionServiceStatus}
            overviewStale={overviewStale}
            paragraphSuggestions={paragraphSuggestions}
            paragraphState={paragraphState}
            paragraphServiceStatus={paragraphServiceStatus}
            paragraphEligible={paragraphEligible}
            paragraphStale={paragraphStale}
            locked={locked}
            onCheckAll={checkAllLanguage}
            onAccept={acceptSuggestion}
            onDismiss={dismissSuggestion}
            onDismissParagraph={dismissParagraphSuggestion}
          /> : (
            <section className="story-polish-lab" aria-label="AI Polish Lab">
              <div className="story-polish-lab-heading">
                <button type="button" className="story-text-button" onClick={() => setPolishOpen(false)}>← Language support</button>
                <div className="story-polish-title">
                  <img src="/ai-coach-fox.png" alt="" />
                  <div><p className="micro-label">AI writing coach</p><h2>Polish Lab</h2></div>
                </div>
                <p>Select words in your draft, or place the cursor in a paragraph. Pip will suggest one change—not write the story for you.</p>
              </div>

              <div className="story-rewrite-goals" aria-label="Rewrite goal">
                {rewriteGoals.map((goal) => (
                  <button
                    type="button"
                    key={goal.value}
                    className={rewriteGoal === goal.value ? "selected" : ""}
                    aria-pressed={rewriteGoal === goal.value}
                    onClick={() => {
                      setRewriteGoal(goal.value);
                      setRewrite(null);
                      setRewriteState("idle");
                    }}
                  >
                    <strong>{goal.label}</strong>
                    <span>{goal.hint}</span>
                  </button>
                ))}
              </div>

              {rewrite ? (
                <div className="story-rewrite-result">
                  <div><span>Your words</span><p>{rewrite.original}</p></div>
                  <div className="suggested"><span>Pip&apos;s suggestion</span><p>{rewrite.revised}</p></div>
                  <p className="story-rewrite-why"><strong>Why:</strong> {rewrite.explanation}</p>
                  <div className="story-rewrite-actions">
                    <button type="button" className="btn btn-secondary" onClick={() => void runRewrite()}>Try another</button>
                    <button type="button" className="btn btn-coral" onClick={applyRewrite}>Use this change</button>
                  </div>
                </div>
              ) : (
                <button type="button" className="story-rewrite-generate" onClick={() => void runRewrite()} disabled={rewriteState === "loading" || locked}>
                  <span aria-hidden="true">✦</span>
                  <strong>{rewriteState === "loading" ? "Pip is thinking..." : "Suggest one change"}</strong>
                  <small>Uses the selected words or current paragraph</small>
                </button>
              )}

              {rewriteState === "error" ? <p className="story-rewrite-error" role="alert">{rewriteError}</p> : null}
              <div className="story-polish-safety"><span>✓</span><p><strong>Your ideas stay yours.</strong> Pip preserves your meaning and never writes the rest of the story.</p></div>
              <button type="button" className="story-undo-button" onClick={undoRewrite} disabled={!editor?.can().undo()}>Undo last edit</button>
            </section>
          )}

          <button
            type="button"
            className="story-polish-button"
            onClick={() => setPolishOpen((open) => !open)}
            disabled={locked}
          >
            {polishOpen ? "Back to language support" : "✦ Polish my story"}
          </button>
        </aside>
      </section>

      <GrammarSuggestionPopover
        anchor={anchoredSuggestion}
        onApply={applyAnchoredSuggestion}
        onDismiss={dismissAnchoredSuggestion}
        onClose={closeSuggestionPopover}
        onPointerEnter={clearSuggestionPopoverClose}
        onPointerLeave={scheduleSuggestionPopoverClose}
      />

      <div className={`modal-backdrop ${submitModalOpen ? "open" : ""}`} role="dialog" aria-modal="true" aria-labelledby="practice-submit-title">
        <div className="modal">
          <p className="eyebrow">Ready to share</p>
          <h2 className="panel-title" id="practice-submit-title" style={{ fontSize: "var(--text-xl)", marginTop: 8 }}>
            {isPersonalPractice ? "Finish this personal practice?" : "Submit this writing to your teacher?"}
          </h2>
          <p className="panel-subtitle" style={{ marginTop: 12 }}>
            {isPersonalPractice
              ? "Your draft will be locked and the AI marker will prepare scores and learning advice. This is practice feedback, not a teacher grade."
              : "Your draft will be locked after submission. You can read feedback when your teacher releases it."}
          </p>
          <div className="row-actions">
            <button className="btn btn-secondary" type="button" onClick={() => setSubmitModalOpen(false)}>Keep writing</button>
            <button className="btn btn-primary" type="button" onClick={() => void onSubmit()}>{isPersonalPractice ? "Finish and mark" : "Submit now"}</button>
          </div>
        </div>
      </div>
      <div className={`toast ${toast ? "show" : ""}`} role="status" aria-live="polite">{toast}</div>
    </main>
  );
}
