import { useEffect, useState, type FormEvent } from "react";
import { useAuth } from "../../auth/session";
import { Alert, Empty, Field, PageHeader, Pager, Panel, Select, TextArea, primaryButton, tinyButton } from "../../components/ui";
import { errorMessage } from "../../lib/errors";
import { fetchAll } from "../../lib/paging";
import { usePaged } from "../../lib/usePaged";
import { allowedSubmissionStatuses, statusLabel } from "../../lib/workflow";
import api from "../../services/api";

type Submission = {
  id: string;
  application: string;
  application_code: string;
  candidate_name: string;
  job_title: string;
  resume_filename: string;
  response_status: string;
  client_feedback: string;
  submitted_by_name: string;
};
type ApplicationOption = { id: string; candidate: string; candidate_name: string; job_title: string; application_code: string };
type Resume = { id: string; original_filename: string };

export default function Submissions() {
  const { can } = useAuth();
  const list = usePaged<Submission>("/submissions/");
  const [applications, setApplications] = useState<ApplicationOption[]>([]);
  const [resumes, setResumes] = useState<Resume[]>([]);
  const [application, setApplication] = useState("");
  const [resume, setResume] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const canAdd = can("recruitment.add_submission");
  const canChange = can("recruitment.change_submission");

  useEffect(() => {
    if (!can("applications.view_application")) return;
    fetchAll<ApplicationOption>("/applications/").then((result) => setApplications(result.rows)).catch(() => setApplications([]));
  }, [can]);

  useEffect(() => {
    const chosen = applications.find((item) => item.id === application);
    if (!chosen || !can("candidates.view_candidate")) {
      setResumes([]);
      return;
    }
    api.get(`/candidates/${chosen.candidate}/`).then((response) => setResumes(response.data.resumes || [])).catch(() => setResumes([]));
  }, [application, applications, can]);

  async function create(event: FormEvent) {
    event.preventDefault();
    setError("");
    setNotice("");
    if (!resume) {
      setError("Choose a resume that belongs to this candidate.");
      return;
    }
    try {
      await api.post("/submissions/", { application, resume });
      setApplication("");
      setResume("");
      setNotice("Submission recorded as Pending. The application status was not changed.");
      list.reload();
    } catch (reason) {
      setError(errorMessage(reason, "The submission could not be created."));
    }
  }

  async function move(row: Submission, responseStatus: string) {
    setError("");
    try {
      await api.patch(`/submissions/${row.id}/`, { response_status: responseStatus });
      list.reload();
    } catch (reason) {
      setError(errorMessage(reason, "That submission status is not allowed."));
    }
  }

  async function saveFeedback(row: Submission, clientFeedback: string) {
    setError("");
    try {
      await api.patch(`/submissions/${row.id}/`, { client_feedback: clientFeedback, response_status: row.response_status });
      list.reload();
    } catch (reason) {
      setError(errorMessage(reason, "Feedback could not be saved."));
    }
  }

  return (
    <>
      <PageHeader eyebrow="CLIENT REVIEW" title="Submissions" description="Send a candidate resume to the client. The pipeline status stays where it is." />
      {error && <Alert>{error}</Alert>}
      {notice && <Alert tone="success">{notice}</Alert>}
      {list.error && <Alert>{list.error}</Alert>}
      {canAdd && (
        <Panel title="New submission">
          <form className="grid gap-3 md:grid-cols-3" onSubmit={create}>
            <Field label="Application">
              <Select required value={application} onChange={(event) => { setApplication(event.target.value); setResume(""); }}>
                <option value="">Select application</option>
                {applications.map((item) => (
                  <option key={item.id} value={item.id}>{item.candidate_name} · {item.job_title} · {item.application_code}</option>
                ))}
              </Select>
            </Field>
            <Field label="Resume">
              <Select required value={resume} onChange={(event) => setResume(event.target.value)} disabled={!resumes.length}>
                <option value="">{resumes.length ? "Select resume" : "No resume on this candidate"}</option>
                {resumes.map((item) => <option key={item.id} value={item.id}>{item.original_filename}</option>)}
              </Select>
            </Field>
            <div className="flex items-end">{resumes.length > 0 && <button className={primaryButton}>Submit to client</button>}</div>
          </form>
        </Panel>
      )}
      <div className="mt-4 grid gap-3">
        {list.rows.map((row) => (
          <article key={row.id} className="rounded-xl border border-line bg-white p-4 text-sm">
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <h2 className="font-display text-lg font-bold">{row.candidate_name}</h2>
              <span>{statusLabel(row.response_status)}</span>
            </div>
            <p className="text-muted">{row.job_title} · {row.application_code} · {row.resume_filename}</p>
            <p className="text-muted">Submitted by {row.submitted_by_name || "—"}</p>
            {row.client_feedback && <p className="mt-2">{row.client_feedback}</p>}
            {canChange && (
              <div className="mt-3 grid gap-2">
                <div className="flex flex-wrap gap-2">
                  {allowedSubmissionStatuses(row.response_status).map((status) => (
                    <button key={status} type="button" className={tinyButton} onClick={() => move(row, status)}>{statusLabel(status)}</button>
                  ))}
                </div>
                <FeedbackForm initial={row.client_feedback} onSave={(value) => saveFeedback(row, value)} />
              </div>
            )}
          </article>
        ))}
        {!list.rows.length && !list.loading && <Empty>No submissions.</Empty>}
      </div>
      <Pager page={list.page} count={list.count} onPage={list.setPage} />
    </>
  );
}

function FeedbackForm({ initial, onSave }: { initial: string; onSave: (value: string) => void }) {
  const [value, setValue] = useState(initial);
  return (
    <form className="grid gap-2" onSubmit={(event) => { event.preventDefault(); onSave(value); }}>
      <TextArea value={value} onChange={(event) => setValue(event.target.value)} placeholder="Client feedback" />
      <button className={primaryButton}>Save feedback</button>
    </form>
  );
}
