/**
 * Pure text/position helpers for the writing editor's AI-assist features
 * (grammar suggestions, sentence rewrite). Kept separate from the editor
 * component so this logic can be unit tested without a real ProseMirror
 * document or DOM.
 */

/** The minimal slice of a ProseMirror doc these helpers need. The real
 * `editor.state.doc` satisfies this structurally. */
export type TextDocument = {
  content: { size: number };
  textBetween(from: number, to: number, blockSeparator?: string): string;
};

// Must match the API's RewriteRequest.text max_length: "rewrite" means a
// sentence, not a whole draft, and both ends of the request need to agree
// on that or a long selection reaches the model and comes back as
// commentary instead of a rewrite.
export const REWRITE_MAX_CHARS = 400;

const POSITION_DRIFT_SEARCH_CHARS = 300;

/** The sentence (trimmed) that contains `offset` within `text`, with its trimmed start/end in `text`. */
export function sentenceAroundOffset(
  text: string,
  offset: number,
): { text: string; start: number; end: number } | null {
  const sentencePattern = /[^.!?]+[.!?]+|[^.!?]+$/g;
  let match: RegExpExecArray | null;
  while ((match = sentencePattern.exec(text)) !== null) {
    const rawStart = match.index;
    const rawEnd = rawStart + match[0].length;
    if (offset < rawStart || offset > rawEnd) continue;
    const trimmed = match[0].trim();
    if (!trimmed) return null;
    const leading = match[0].length - match[0].trimStart().length;
    const start = rawStart + leading;
    return { text: trimmed, start, end: start + trimmed.length };
  }
  return null;
}

/**
 * Where `expectedText` currently sits in the document, starting from where it was
 * last known to be at [expectedFrom, expectedTo). A suggestion's position is captured
 * once (when it's checked, or when a rewrite is requested) but only applied later, by
 * which point ordinary typing elsewhere in the draft - or another suggestion being
 * accepted first - has very likely shifted every position after it. An exact match at
 * the old position is the uncommon case; this looks nearby before giving up.
 *
 * Bounds are validated before any read: `doc.textBetween` throws on an out-of-range
 * position, and stored positions can already exceed the current document if text was
 * deleted since - that exception, uncaught in a click handler, is why "accept" or
 * "apply" could silently do nothing.
 */
export function locateCurrentRange(
  doc: TextDocument,
  expectedFrom: number,
  expectedTo: number,
  expectedText: string,
): { from: number; to: number } | null {
  const docSize = doc.content.size;
  const from = Math.max(0, Math.min(expectedFrom, docSize));
  const to = Math.max(from, Math.min(expectedTo, docSize));
  if (to <= docSize && doc.textBetween(from, to, " ") === expectedText) {
    return { from, to };
  }
  // Position 0 is the boundary before the document's first character, not a character
  // itself - textBetween(0, N) and textBetween(1, N) return the same text, both
  // anchored at position 1. Flooring the window at 1 (not 0) keeps "windowText's
  // local index J is at position windowFrom + J" true; flooring at 0 would silently
  // shift every match found near the very start of the document by one position.
  const windowFrom = Math.max(1, from - POSITION_DRIFT_SEARCH_CHARS);
  const windowTo = Math.min(docSize, to + POSITION_DRIFT_SEARCH_CHARS);
  if (windowFrom >= windowTo) return null;
  const windowText = doc.textBetween(windowFrom, windowTo, " ");
  // Several occurrences of the same short word/phrase can sit inside one search
  // window; take whichever is closest to where it was expected, not just the first.
  let bestFrom: number | null = null;
  let bestDistance = Infinity;
  let searchIndex = 0;
  for (;;) {
    const localIndex = windowText.indexOf(expectedText, searchIndex);
    if (localIndex === -1) break;
    const candidateFrom = windowFrom + localIndex;
    const distance = Math.abs(candidateFrom - from);
    if (distance < bestDistance) {
      bestDistance = distance;
      bestFrom = candidateFrom;
    }
    searchIndex = localIndex + 1;
  }
  return bestFrom === null ? null : { from: bestFrom, to: bestFrom + expectedText.length };
}
