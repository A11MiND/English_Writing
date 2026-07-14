"use client";

import type { GrammarSuggestion, ParagraphSuggestion } from "@english-ai-writing/shared";

type DisplaySuggestion = GrammarSuggestion & { sourceText: string };

type WritingLanguageSupportProps = {
  suggestions: DisplaySuggestion[];
  suggestionState: "idle" | "checking" | "ready" | "error";
  suggestionServiceStatus: "ok" | "unavailable";
  overviewStale: boolean;
  paragraphSuggestions: ParagraphSuggestion[];
  paragraphState: "idle" | "waiting" | "checking" | "ready" | "error";
  paragraphServiceStatus: "ok" | "fallback";
  paragraphEligible: boolean;
  paragraphStale: boolean;
  locked: boolean;
  onCheckAll: () => void;
  onAccept: (suggestion: DisplaySuggestion, replacement: string) => void;
  onDismiss: (suggestion: DisplaySuggestion) => void;
  onDismissParagraph: (suggestionId: string) => void;
};

function formatSuggestionSpan(value: string) {
  if (!value) return "(empty)";
  return value.replaceAll(" ", "<space>");
}

function levelStatus(count: number, label: string) {
  if (count === 0) return `${label} clear`;
  return `${count} ${label.toLowerCase()} ${count === 1 ? "note" : "notes"}`;
}

function GrammarLevelSection({
  level,
  title,
  description,
  suggestions,
  onAccept,
  onDismiss,
}: {
  level: "WORD" | "SENTENCE";
  title: string;
  description: string;
  suggestions: DisplaySuggestion[];
  onAccept: WritingLanguageSupportProps["onAccept"];
  onDismiss: WritingLanguageSupportProps["onDismiss"];
}) {
  const tone = level.toLowerCase();
  return (
    <section className={`language-level language-level-${tone}`} aria-labelledby={`language-${tone}-title`}>
      <div className="language-level-heading">
        <span className="language-level-dot" aria-hidden="true" />
        <div>
          <h3 id={`language-${tone}-title`}>{title}</h3>
          <p>{description}</p>
        </div>
        <strong>{suggestions.length}</strong>
      </div>
      {suggestions.length ? (
        <div className="language-level-list">
          {suggestions.slice(0, 2).map((suggestion) => (
            <article className="language-note" key={suggestion.id} data-testid={`${tone}-suggestion-card`}>
              <div>
                <h4>{suggestion.short_message}</h4>
                <p>{suggestion.message}</p>
                <q>{formatSuggestionSpan(suggestion.sourceText)}</q>
              </div>
              <div className="language-note-actions">
                {suggestion.replacements[0] ? (
                  <button type="button" onClick={() => onAccept(suggestion, suggestion.replacements[0])}>
                    Use “{suggestion.replacements[0]}”
                  </button>
                ) : null}
                <button type="button" onClick={() => onDismiss(suggestion)}>Dismiss</button>
              </div>
            </article>
          ))}
        </div>
      ) : (
        <p className="language-level-clear">No active {level === "WORD" ? "word" : "sentence"} notes.</p>
      )}
    </section>
  );
}

export function WritingLanguageSupport({
  suggestions,
  suggestionState,
  suggestionServiceStatus,
  overviewStale,
  paragraphSuggestions,
  paragraphState,
  paragraphServiceStatus,
  paragraphEligible,
  paragraphStale,
  locked,
  onCheckAll,
  onAccept,
  onDismiss,
  onDismissParagraph,
}: WritingLanguageSupportProps) {
  const wordSuggestions = suggestions.filter((suggestion) => suggestion.level === "WORD");
  const sentenceSuggestions = suggestions.filter((suggestion) => suggestion.level === "SENTENCE");
  const isChecking = suggestionState === "checking" || paragraphState === "checking";

  return (
    <section className="story-language-card" aria-label="Three-level language support">
      <div className="story-language-heading">
        <div>
          <h2>Live language support</h2>
          <p aria-live="polite">
            {suggestionState === "checking"
              ? "Checking words and sentences..."
              : suggestionState === "error"
                ? "Word and sentence checks are reconnecting"
                : `${suggestions.length} active language ${suggestions.length === 1 ? "note" : "notes"}`}
            {overviewStale || paragraphStale ? " · Updating" : ""}
          </p>
        </div>
        <button
          type="button"
          onClick={onCheckAll}
          disabled={locked || isChecking}
          className="story-text-button"
          data-testid="full-check-button"
        >
          {isChecking ? "Checking..." : "Check all"}
        </button>
      </div>

      <div className="language-level-summary" aria-label="Language check levels">
        <span className="word">{levelStatus(wordSuggestions.length, "Word")}</span>
        <span className="sentence">{levelStatus(sentenceSuggestions.length, "Sentence")}</span>
        <span className="paragraph">
          {paragraphState === "ready" ? levelStatus(paragraphSuggestions.length, "Paragraph") : "Paragraph coach"}
        </span>
      </div>

      {suggestionServiceStatus === "unavailable" ? (
        <div className="story-support-warning">Writing and autosave still work while word and sentence checks reconnect.</div>
      ) : null}

      <div className="language-level-stack">
        <GrammarLevelSection
          level="WORD"
          title="Word check"
          description="Spelling, word form and word choice"
          suggestions={wordSuggestions}
          onAccept={onAccept}
          onDismiss={onDismiss}
        />
        <GrammarLevelSection
          level="SENTENCE"
          title="Sentence check"
          description="Tense, agreement and sentence structure"
          suggestions={sentenceSuggestions}
          onAccept={onAccept}
          onDismiss={onDismiss}
        />

        <section className="language-level language-level-paragraph" aria-labelledby="language-paragraph-title">
          <div className="language-level-heading">
            <span className="language-level-dot" aria-hidden="true" />
            <div>
              <h3 id="language-paragraph-title">Paragraph coach</h3>
              <p>Focus, flow, order and links between ideas</p>
            </div>
            <strong>{paragraphSuggestions.length}</strong>
          </div>

          {!paragraphEligible ? (
            <p className="language-level-clear">Write at least three sentences to unlock paragraph feedback.</p>
          ) : paragraphState === "waiting" || paragraphState === "checking" ? (
            <div className="paragraph-coach-loading" role="status">
              <span aria-hidden="true" />
              <p>{paragraphState === "waiting" ? "Waiting for a short pause..." : "Reading how the ideas connect..."}</p>
            </div>
          ) : paragraphState === "error" ? (
            <p className="story-support-warning">Paragraph feedback could not update yet. Your writing is still saved.</p>
          ) : paragraphSuggestions.length ? (
            <div className="paragraph-suggestion-list">
              {paragraphSuggestions.map((suggestion) => (
                <article className="paragraph-suggestion-card" key={suggestion.id} data-testid="paragraph-suggestion-card">
                  <span>{suggestion.focus.toLowerCase()}</span>
                  <h4>{suggestion.title}</h4>
                  <p>{suggestion.message}</p>
                  <q>{suggestion.evidence}</q>
                  <div className="paragraph-action"><strong>Try this:</strong> {suggestion.action}</div>
                  <button type="button" onClick={() => onDismissParagraph(suggestion.id)}>Got it</button>
                </article>
              ))}
              {paragraphServiceStatus === "fallback" ? (
                <small className="paragraph-service-note">Using the built-in paragraph check while the AI coach reconnects.</small>
              ) : null}
            </div>
          ) : paragraphState === "ready" ? (
            <p className="language-level-clear positive">Your paragraph has a clear, connected flow.</p>
          ) : (
            <p className="language-level-clear">Pause after a few sentences and Pip will check how they connect.</p>
          )}
        </section>
      </div>
    </section>
  );
}
