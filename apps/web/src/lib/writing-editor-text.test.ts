import { describe, expect, it } from "vitest";

import { locateCurrentRange, sentenceAroundOffset, type TextDocument, REWRITE_MAX_CHARS } from "./writing-editor-text";

/**
 * A fake ProseMirror document backed by a plain string, following the real
 * position convention: position 1 is the first character, position 0 is the
 * boundary just before it (both read as the same text), and reading past the
 * end throws - matching `doc.textBetween` in the real editor.
 */
function fakeDoc(text: string): TextDocument {
  return {
    content: { size: text.length + 1 },
    textBetween(from: number, to: number): string {
      const size = text.length + 1;
      if (from < 0 || to > size || from > to) {
        throw new RangeError(`Position ${from}/${to} outside of fragment (size ${size})`);
      }
      return text.slice(Math.max(0, from - 1), Math.max(0, to - 1));
    },
  };
}

describe("sentenceAroundOffset", () => {
  const essay =
    "Yesterday my family and me go to the city zoo. It was very sunny day and we was so exited! " +
    "First we seed the giant elephants. They are eating big green leaves with dere long trunks. " +
    "My brother run fast to see the monkeys. The little monkeys was swinging on the tree and making funny noises. " +
    "One monkey throw a little stick and we laugh so much. After we ate our lunch on a red table. " +
    "I had a ham sandwhich and a apple. Mom buyed us ice cream too. Mine was choclate flavor and it drip on my shirt! " +
    "Next we went to look at the tall giraffes. They have dark spots and very long neck. " +
    "I tried to feed a leaf but a worker say no we cannot do that. " +
    "The best part was when we watch the big dolphins swiming fast and jumping high in the blue water. " +
    "They splash water on the people in the front row. I love the zoo very much because animals is cool. " +
    "We goed home in the car and I fall sleep becuz I was so tired. It was the bestest day ever!";

  it("bounds the target to one sentence no matter where the cursor sits in a long, unbroken paragraph", () => {
    // Reproduces the reported bug: with no text selected, "rewrite" used to fall
    // back to the entire current paragraph. A pupil who never presses Enter in a
    // free-write task has their whole essay as one paragraph, so any cursor
    // position sent the whole thing to the model as if it were "one sentence".
    for (let offset = 0; offset < essay.length; offset += 7) {
      const sentence = sentenceAroundOffset(essay, offset);
      expect(sentence).not.toBeNull();
      expect(sentence!.text.length).toBeLessThan(REWRITE_MAX_CHARS);
    }
  });

  it("returns null for an out-of-range offset", () => {
    expect(sentenceAroundOffset("Hello world.", 500)).toBeNull();
  });
});

describe("locateCurrentRange", () => {
  const essay =
    "Yesterday my family and me go to the city zoo. It was very sunny day and we was so exited! " +
    "First we seed the giant elephants.";

  function positionOf(doc: string, needle: string) {
    const index = doc.indexOf(needle);
    return { from: index + 1, to: index + 1 + needle.length };
  }

  it("returns the exact range when nothing has changed", () => {
    const { from, to } = positionOf(essay, "exited");
    expect(locateCurrentRange(fakeDoc(essay), from, to, "exited")).toEqual({ from, to });
  });

  it("finds the word after an earlier insertion shifted it right", () => {
    const { from, to } = positionOf(essay, "exited");
    const edited = "Yesterday, in the morning, " + essay;
    const truth = positionOf(edited, "exited");

    expect(locateCurrentRange(fakeDoc(edited), from, to, "exited")).toEqual(truth);
  });

  it("finds the word after an earlier deletion shifted it left", () => {
    const { from, to } = positionOf(essay, "exited");
    const edited = essay.replace("Yesterday my family and me go to the city zoo. ", "");
    const truth = positionOf(edited, "exited");

    expect(locateCurrentRange(fakeDoc(edited), from, to, "exited")).toEqual(truth);
  });

  it("does not throw when the stored position now exceeds a shrunk document", () => {
    // This is the actual failure mode reported live: a stale position past the end
    // of the current document made `doc.textBetween` throw inside a click handler,
    // so "accept"/"apply" appeared to silently do nothing.
    expect(() => locateCurrentRange(fakeDoc("Hi."), 500, 506, "exited")).not.toThrow();
    expect(locateCurrentRange(fakeDoc("Hi."), 500, 506, "exited")).toBeNull();
  });

  it("returns null rather than guessing when the text was edited away entirely", () => {
    const { from, to } = positionOf(essay, "exited");
    const edited = essay.replace("exited", "happy");

    expect(locateCurrentRange(fakeDoc(edited), from, to, "exited")).toBeNull();
  });

  it("does not match an occurrence far outside the drift window", () => {
    const farDoc = "word ".repeat(200) + "exited" + " word".repeat(200);

    expect(locateCurrentRange(fakeDoc(farDoc), 1, 7, "exited")).toBeNull();
  });

  it("is unaffected by unrelated text appended after the target", () => {
    // Reproduces the other half of the reported bug: an AI response spliced in
    // after the essay must not disturb suggestions that target the essay itself.
    const { from, to } = positionOf(essay, "exited");
    const withAppendedAnalysis =
      essay + " Error Breakdown and Analysis. Grammar and Tense Consistency: shifts between past and present tense.";

    expect(locateCurrentRange(fakeDoc(withAppendedAnalysis), from, to, "exited")).toEqual({ from, to });
  });

  it("picks the occurrence closest to the original position when the text repeats nearby", () => {
    const doc = "The cat sat. Then a cat ran. Later the cat slept again on the warm windowsill.";
    const secondOccurrence = positionOf(doc.slice(doc.indexOf("cat") + 1), "cat");
    // `from`/`to` computed against the pre-edit doc, pointing at the *second* "cat".
    const preEditIndex = doc.indexOf("cat", doc.indexOf("cat") + 1);
    const from = preEditIndex + 1;
    const to = from + 3;
    const edited = "  " + doc; // two characters inserted before the whole document
    const editedSecondIndex = edited.indexOf("cat", edited.indexOf("cat") + 1);

    const result = locateCurrentRange(fakeDoc(edited), from, to, "cat");

    expect(result).toEqual({ from: editedSecondIndex + 1, to: editedSecondIndex + 1 + 3 });
    expect(secondOccurrence.from).toBeGreaterThan(0); // sanity: fixture actually has a second occurrence
  });
});
