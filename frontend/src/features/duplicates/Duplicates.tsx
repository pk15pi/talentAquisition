import { useState } from "react";
import { Alert, Empty, Field, PageHeader, Pager, Panel, Select, TextArea, primaryButton, secondaryButton } from "../../components/ui";
import { errorMessage } from "../../lib/errors";
import { usePaged } from "../../lib/usePaged";
import { statusLabel } from "../../lib/workflow";
import api from "../../services/api";

type Review = {
  id: string;
  candidate: { id: string; candidate_code: string; full_name: string };
  matched_candidate: { id: string; candidate_code: string; full_name: string };
  match_type: string;
  status: string;
  notes: string;
  reviewed_at: string | null;
};

export default function Duplicates() {
  const [status, setStatus] = useState("PENDING");
  const list = usePaged<Review>("/duplicate-reviews/", { status });
  const [notes, setNotes] = useState<Record<string, string>>({});
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  async function decide(review: Review, approved: boolean) {
    setError("");
    setNotice("");
    try {
      await api.post(`/duplicate-reviews/${review.id}/decide/`, { approved, notes: notes[review.id] || "" });
      setNotice(approved ? "Review approved. The two profiles were not merged." : "Review rejected. The two profiles were not merged.");
      list.reload();
    } catch (reason) {
      setError(errorMessage(reason, "The decision was not saved."));
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="DATA QUALITY"
        title="Duplicate review"
        description="Approve or reject a possible duplicate. This records the decision and does not merge or delete either profile."
      />
      {error && <Alert>{error}</Alert>}
      {notice && <Alert tone="success">{notice}</Alert>}
      {list.error && <Alert>{list.error}</Alert>}
      <Panel>
        <Field label="Status">
          <Select value={status} onChange={(event) => setStatus(event.target.value)}>
            <option value="PENDING">Pending</option>
            <option value="APPROVED">Approved</option>
            <option value="REJECTED">Rejected</option>
          </Select>
        </Field>
      </Panel>
      <div className="mt-4 grid gap-3">
        {list.rows.map((review) => (
          <article key={review.id} className="rounded-xl border border-line bg-white p-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h2 className="font-display text-lg font-bold">
                  {review.candidate.full_name} <span className="text-sm font-medium text-muted">{review.candidate.candidate_code}</span>
                </h2>
                <p className="text-sm text-muted">
                  matches {review.matched_candidate.full_name} ({review.matched_candidate.candidate_code}) on {statusLabel(review.match_type)}
                </p>
                <p className="mt-1 text-xs font-semibold uppercase tracking-wide text-muted">{statusLabel(review.status)}</p>
              </div>
            </div>
            {review.status === "PENDING" ? (
              <div className="mt-3 grid gap-2">
                <TextArea
                  aria-label={`Notes for ${review.candidate.full_name}`}
                  placeholder="Decision notes"
                  value={notes[review.id] || ""}
                  onChange={(event) => setNotes({ ...notes, [review.id]: event.target.value })}
                />
                <div className="flex gap-2">
                  <button type="button" className={primaryButton} onClick={() => decide(review, true)}>Approve</button>
                  <button type="button" className={secondaryButton} onClick={() => decide(review, false)}>Reject</button>
                </div>
              </div>
            ) : (
              review.notes && <p className="mt-2 text-sm">{review.notes}</p>
            )}
          </article>
        ))}
        {!list.rows.length && !list.loading && <Empty>No duplicate reviews in this status.</Empty>}
      </div>
      <Pager page={list.page} count={list.count} onPage={list.setPage} />
    </>
  );
}
