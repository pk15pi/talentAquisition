import { useEffect, useState, type FormEvent } from "react";
import { useAuth } from "../../auth/session";
import { Alert, Empty, Field, PageHeader, Pager, Panel, Select, primaryButton, tinyButton } from "../../components/ui";
import { errorMessage } from "../../lib/errors";
import { fetchAll } from "../../lib/paging";
import { usePaged } from "../../lib/usePaged";
import { APPLICATION_PIPELINE, allowedApplicationStatuses, statusLabel } from "../../lib/workflow";
import api from "../../services/api";

type Application = {
  id: string;
  application_code: string;
  candidate: string;
  candidate_name: string;
  candidate_code: string;
  job: string;
  job_title: string;
  job_code: string;
  recruiter_name: string;
  status: string;
  match_score: string | null;
};
type Option = { id: string; full_name?: string; candidate_code?: string; title?: string; job_code?: string };

const COLUMNS = [...APPLICATION_PIPELINE, "REJECTED", "WITHDRAWN"];

export default function Applications() {
  const { can } = useAuth();
  const list = usePaged<Application>("/applications/");
  const [candidates, setCandidates] = useState<Option[]>([]);
  const [jobs, setJobs] = useState<Option[]>([]);
  const [candidate, setCandidate] = useState("");
  const [job, setJob] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const canChange = can("applications.change_application");
  const canAdd = can("applications.add_application");

  useEffect(() => {
    if (!canAdd) return;
    Promise.all([
      can("candidates.view_candidate") ? fetchAll<Option>("/candidates/") : Promise.resolve({ rows: [] as Option[] }),
      can("jobs.view_job") ? fetchAll<Option>("/jobs/") : Promise.resolve({ rows: [] as Option[] }),
    ]).then(([people, roles]) => {
      setCandidates(people.rows);
      setJobs(roles.rows);
    }).catch(() => setError("Candidates or job descriptions could not be loaded."));
  }, [canAdd, can]);

  async function create(event: FormEvent) {
    event.preventDefault();
    setError("");
    setNotice("");
    try {
      await api.post("/applications/", { candidate, job });
      setCandidate("");
      setJob("");
      setNotice("Application created at Identified.");
      list.reload();
    } catch (reason) {
      setError(errorMessage(reason, "Could not create the application. The candidate may already have an active application for this JD."));
    }
  }

  async function move(row: Application, status: string) {
    setError("");
    setNotice("");
    try {
      await api.post(`/applications/${row.id}/change-status/`, { status });
      list.reload();
    } catch (reason) {
      setError(errorMessage(reason, "That status change is not allowed."));
    }
  }

  async function reapply(row: Application) {
    setError("");
    setNotice("");
    try {
      await api.post("/applications/", { candidate: row.candidate, job: row.job });
      setNotice("A new application was created. The earlier rejected or withdrawn row stays in history.");
      list.reload();
    } catch (reason) {
      setError(errorMessage(reason, "The candidate could not be re-applied to this JD."));
    }
  }

  return (
    <>
      <PageHeader eyebrow="PIPELINE" title="Applications" description="Names come from the application record. Status buttons follow the legal next step, plus reject or withdraw." />
      {error && <Alert>{error}</Alert>}
      {notice && <Alert tone="success">{notice}</Alert>}
      {list.error && <Alert>{list.error}</Alert>}
      {canAdd && (
        <Panel title="Add to pipeline">
          <form className="grid gap-3 md:grid-cols-3" onSubmit={create}>
            <Field label="Candidate">
              <Select required value={candidate} onChange={(event) => setCandidate(event.target.value)}>
                <option value="">Select candidate</option>
                {candidates.map((item) => <option key={item.id} value={item.id}>{item.candidate_code} · {item.full_name}</option>)}
              </Select>
            </Field>
            <Field label="Job description">
              <Select required value={job} onChange={(event) => setJob(event.target.value)}>
                <option value="">Select JD</option>
                {jobs.map((item) => <option key={item.id} value={item.id}>{item.job_code} · {item.title}</option>)}
              </Select>
            </Field>
            <div className="flex items-end"><button className={primaryButton}>Add to pipeline</button></div>
          </form>
        </Panel>
      )}
      <div className="mt-4 flex gap-3 overflow-x-auto pb-2">
        {COLUMNS.map((status) => {
          const cards = list.rows.filter((row) => row.status === status);
          return (
            <section key={status} className="w-72 shrink-0 rounded-xl border border-line bg-canvas p-3">
              <h2 className="mb-2 text-xs font-bold uppercase tracking-wide text-muted">{statusLabel(status)} · {cards.length}</h2>
              <div className="grid gap-2">
                {cards.map((row) => {
                  const next = canChange ? allowedApplicationStatuses(row.status) : [];
                  const closed = row.status === "REJECTED" || row.status === "WITHDRAWN";
                  return (
                    <article key={row.id} className="rounded-lg border border-line bg-white p-3 text-sm">
                      <b>{row.candidate_name}</b>
                      <div className="text-muted">{row.candidate_code}</div>
                      <div>{row.job_title}</div>
                      <div className="text-muted">{row.job_code} · {row.recruiter_name || "No recruiter"}</div>
                      <div className="text-muted">{row.application_code}{row.match_score ? ` · match ${row.match_score}` : ""}</div>
                      <div className="mt-2 flex flex-wrap gap-1">
                        {next.map((step) => (
                          <button key={step} type="button" className={tinyButton} onClick={() => move(row, step)}>{statusLabel(step)}</button>
                        ))}
                        {canAdd && closed && (
                          <button type="button" className={tinyButton} onClick={() => reapply(row)}>Re-apply</button>
                        )}
                      </div>
                    </article>
                  );
                })}
                {!cards.length && <Empty>None on this page.</Empty>}
              </div>
            </section>
          );
        })}
      </div>
      <Pager page={list.page} count={list.count} onPage={list.setPage} />
    </>
  );
}
