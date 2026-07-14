"use client";

import type { MarkingResult, TeacherMarkingSubmission } from "@english-ai-writing/shared";
import { useState } from "react";

type ReviewDraft = {
  content: string;
  language: string;
  organisation: string;
  notes: string;
};

type TeacherReviewDeskProps = {
  items: TeacherMarkingSubmission[];
  selectedItem: TeacherMarkingSubmission | undefined;
  selectedResult: MarkingResult | null;
  selectedDraft: ReviewDraft | undefined;
  pendingReview: number;
  readyToRelease: number;
  onSelectSubmission: (submissionId: string) => void;
  onUpdateDraft: (markingResultId: string, patch: Partial<ReviewDraft>) => void;
  onRunMarking: (markingResultId: string) => void;
  onSaveReview: (markingResultId: string) => void;
  onRequestRelease: (markingResultId: string) => void;
};

const rubricRows = [
  { key: "content", label: "Content", note: "Ideas, detail and relevance", tone: "sage" },
  { key: "language", label: "Language", note: "Word choice, grammar and sentences", tone: "lavender" },
  { key: "organisation", label: "Organisation", note: "Beginning, sequence and ending", tone: "gold" },
] as const;

function sentenceRows(content: string) {
  return (content.match(/[^.!?]+[.!?]+|[^.!?]+$/g) ?? [content])
    .map((sentence) => sentence.trim())
    .filter(Boolean)
    .slice(0, 12);
}

function queueLabel(item: TeacherMarkingSubmission, index: number) {
  return `${item.class_name} · Student ${String(index + 1).padStart(2, "0")}`;
}

function scoreValue(result: MarkingResult | null, key: (typeof rubricRows)[number]["key"]) {
  if (!result) return null;
  if (key === "content") return result.content_score;
  if (key === "language") return result.language_score;
  return result.organisation_score;
}

function scoreMaximum(
  item: TeacherMarkingSubmission | undefined,
  key: (typeof rubricRows)[number]["key"],
) {
  const label = rubricRows.find((row) => row.key === key)?.label;
  return item?.task.rubric.dimensions.find(
    (dimension) => dimension.name.toLowerCase() === label?.toLowerCase(),
  )?.max_score;
}

export function TeacherReviewDesk({
  items,
  selectedItem,
  selectedResult,
  selectedDraft,
  pendingReview,
  readyToRelease,
  onSelectSubmission,
  onUpdateDraft,
  onRunMarking,
  onSaveReview,
  onRequestRelease,
}: TeacherReviewDeskProps) {
  const [showAllEvidence, setShowAllEvidence] = useState(false);
  const comments = selectedResult?.sentence_level_comments ?? [];
  const visibleComments = showAllEvidence ? comments : comments.slice(0, 3);
  const sentences = selectedItem ? sentenceRows(selectedItem.submission.content_text) : [];
  const totalScore = selectedResult?.total_score;
  const canRelease = selectedResult?.status === "AI_MARKED";

  return (
    <div className="teacher-review-surface">
      <section className="teacher-review-queue" aria-label="Review queue">
        <div className="teacher-queue-heading">
          <strong>Review queue</strong>
          <span>{pendingReview} need attention · {readyToRelease} ready</span>
        </div>
        <div className="teacher-queue-list">
          {items.slice(0, 6).map((item, index) => {
            const active = item.submission.id === selectedItem?.submission.id;
            return (
              <button
                key={item.submission.id}
                type="button"
                className={`teacher-queue-item ${active ? "active" : ""}`}
                onClick={() => onSelectSubmission(item.submission.id)}
              >
                <span>{String(index + 1).padStart(2, "0")}</span>
                <span>
                  <strong>{queueLabel(item, index)}</strong>
                  <small>{item.submission.word_count} words · {item.marking_result?.status ?? "Waiting"}</small>
                </span>
              </button>
            );
          })}
        </div>
        <span className="teacher-queue-count">{items.length} in queue</span>
      </section>

      <section className="teacher-review-grid">
        <article className="teacher-evidence-panel">
          {selectedItem ? (
            <>
              <header className="teacher-evidence-heading">
                <div>
                  <h2>{selectedItem.task.title}</h2>
                  <p>{selectedItem.class_name} · Student writing · {selectedItem.submission.word_count} words</p>
                </div>
                <time dateTime={selectedItem.submission.submitted_at}>
                  Submitted {new Date(selectedItem.submission.submitted_at).toLocaleString()}
                </time>
              </header>

              <div className="teacher-essay-layout">
                <div className="teacher-essay-copy">
                  {sentences.map((sentence, index) => (
                    <p key={`${selectedItem.submission.id}-${index}`}>
                      {sentence}
                      {index < visibleComments.length ? <span>{index + 1}</span> : null}
                    </p>
                  ))}
                </div>

                <aside className="teacher-evidence-notes" aria-label="AI evidence for teacher review">
                  {visibleComments.map((comment, index) => (
                    <article key={`${comment.sentence}-${index}`} className={`teacher-evidence-note teacher-note-${(index % 3) + 1}`}>
                      <div>
                        <span>{index + 1}</span>
                        <strong>{comment.category.toLowerCase().replace("_", " ")}</strong>
                      </div>
                      <p>{comment.comment}</p>
                    </article>
                  ))}
                  {visibleComments.length === 0 ? (
                    <div className="teacher-evidence-empty">
                      {selectedResult?.status === "AI_MARKED"
                        ? "No sentence-level comments were returned for this writing."
                        : "Run AI marking to create evidence-linked comments."}
                    </div>
                  ) : null}
                </aside>
              </div>

              <div className="teacher-rubric-row" aria-label="Teacher rubric scores">
                {rubricRows.map((row) => {
                  const value = selectedDraft?.[row.key] ?? String(scoreValue(selectedResult, row.key) ?? "");
                  const maximum = scoreMaximum(selectedItem, row.key);
                  return (
                    <label key={row.key} className={`teacher-rubric-card teacher-rubric-${row.tone}`}>
                      <span>{row.label}</span>
                      <small>{row.note}</small>
                      <span className="teacher-score-input">
                        <input
                          inputMode="decimal"
                          aria-label={`${row.label} score`}
                          value={value}
                          onChange={(event) => selectedResult && onUpdateDraft(selectedResult.id, { [row.key]: event.target.value })}
                        />
                        <span>/ {maximum ?? "-"}</span>
                      </span>
                    </label>
                  );
                })}
              </div>
            </>
          ) : (
            <div className="teacher-review-empty">No submitted writing is waiting for review.</div>
          )}
        </article>

        <aside className="teacher-decision-rail">
          <section className="teacher-ai-summary">
            <div className="teacher-ai-summary-heading">
              <strong>AI-assisted assessment</strong>
              <span>Teacher decides</span>
            </div>
            <div className="teacher-total-score">
              {totalScore ?? "-"} <span>/ {selectedItem?.task.rubric.total_score ?? "-"}</span>
            </div>
            <p>
              {selectedResult?.language_feedback
                ?? "Review the evidence and rubric before releasing anything to the student."}
            </p>
            {selectedResult && selectedResult.status !== "AI_MARKED" ? (
              <button type="button" onClick={() => onRunMarking(selectedResult.id)}>Run AI marking</button>
            ) : null}
          </section>

          <section className="teacher-comment-card">
            <h2>Recommended teacher comment</h2>
            <textarea
              value={selectedDraft?.notes ?? ""}
              onChange={(event) => selectedResult && onUpdateDraft(selectedResult.id, { notes: event.target.value })}
              placeholder={selectedResult?.content_feedback ?? "Write the final comment the student will see."}
              aria-label="Teacher final comment"
            />
            <button
              type="button"
              disabled={!selectedResult}
              onClick={() => selectedResult && onSaveReview(selectedResult.id)}
            >
              Save teacher review
            </button>
          </section>

          <section className="teacher-followup-card">
            <h2>Teaching follow-up</h2>
            {selectedResult?.weaknesses.length ? (
              <ul>
                {selectedResult.weaknesses.slice(0, 3).map((weakness) => <li key={weakness}>{weakness}</li>)}
              </ul>
            ) : (
              <p>No priority weakness has been identified yet.</p>
            )}
            {selectedResult?.recommended_exercises[0] ? (
              <div className="teacher-exercise">
                <strong>{selectedResult.recommended_exercises[0].title}</strong>
                <p>{selectedResult.recommended_exercises[0].prompt}</p>
              </div>
            ) : null}
          </section>

          <div className="teacher-review-actions">
            <button
              type="button"
              className="teacher-evidence-button"
              aria-pressed={showAllEvidence}
              onClick={() => setShowAllEvidence((current) => !current)}
            >
              {showAllEvidence ? "Show key evidence" : "Review all evidence"}
            </button>
            <button
              type="button"
              className="teacher-release-button"
              disabled={!selectedResult || !canRelease}
              onClick={() => selectedResult && onRequestRelease(selectedResult.id)}
            >
              Release to student
            </button>
          </div>
        </aside>
      </section>
    </div>
  );
}
