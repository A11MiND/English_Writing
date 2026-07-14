"use client";

import type { GrammarSuggestion } from "@english-ai-writing/shared";
import { createPortal } from "react-dom";

export type AnchoredGrammarSuggestion = {
  suggestion: GrammarSuggestion & { sourceText: string };
  top: number;
  left: number;
};

type GrammarSuggestionPopoverProps = {
  anchor: AnchoredGrammarSuggestion | null;
  onApply: (replacement: string) => void;
  onDismiss: () => void;
  onClose: () => void;
  onPointerEnter: () => void;
  onPointerLeave: () => void;
};

export function GrammarSuggestionPopover({
  anchor,
  onApply,
  onDismiss,
  onClose,
  onPointerEnter,
  onPointerLeave,
}: GrammarSuggestionPopoverProps) {
  if (!anchor || typeof document === "undefined") return null;

  const { suggestion } = anchor;
  const replacement = suggestion.replacements[0];
  const levelLabel = suggestion.level === "WORD" ? "Word suggestion" : "Sentence suggestion";

  return createPortal(
    <aside
      className={`grammar-suggestion-popover grammar-suggestion-popover-${suggestion.level.toLowerCase()}`}
      style={{ top: anchor.top, left: anchor.left }}
      role="dialog"
      aria-label={`${levelLabel}: ${suggestion.short_message}`}
      data-testid="grammar-suggestion-popover"
      onPointerEnter={onPointerEnter}
      onPointerLeave={onPointerLeave}
    >
      <header>
        <span>{levelLabel}</span>
        <button type="button" onClick={onClose} aria-label="Close suggestion">Close</button>
      </header>
      <strong>{suggestion.short_message}</strong>
      <p>{suggestion.message}</p>

      {replacement ? (
        <div className="grammar-popover-change" aria-label={`Change ${suggestion.sourceText} to ${replacement}`}>
          <div><span>In your writing</span><del>{suggestion.sourceText || "(space)"}</del></div>
          <div><span>Suggested change</span><ins>{replacement || "(remove)"}</ins></div>
        </div>
      ) : null}

      <div className="grammar-popover-actions">
        {replacement ? (
          <button
            type="button"
            className="grammar-popover-apply"
            onClick={() => onApply(replacement)}
            data-testid="inline-apply-suggestion"
          >
            Change to “{replacement}”
          </button>
        ) : null}
        <button type="button" className="grammar-popover-dismiss" onClick={onDismiss}>Ignore this note</button>
      </div>
    </aside>,
    document.body,
  );
}
