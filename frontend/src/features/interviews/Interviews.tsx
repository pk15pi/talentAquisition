import { useEffect, useState, type FormEvent } from "react";
import { useAuth } from "../../auth/session";
import { Alert, Empty, Field, PageHeader, Pager, Panel, Select, TextArea, TextInput, primaryButton } from "../../components/ui";
import { errorMessage } from "../../lib/errors";
import { fetchAll } from "../../lib/paging";
import { usePaged } from "../../lib/usePaged";
import { statusLabel } from "../../lib/workflow";
import api from "../../services/api";

type Participant = { id: string; user: string | null; user_name: string; name: string; role: string };
type Interview = {
  id: string;
  application: string;
  application_code: string;
  candidate_name: string;
  job_title: string;
  round_name: string;
  interview_date: string;
  interviewer_name: string;
  feedback: string;
  result: string;
  participants: Participant[];
};
type ApplicationOption = { id: string; candidate_name: string; job_title: string; application_code: string };
type Staff = { id: string; username: string; first_name: string; last_name: string };

function toLocalInput(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  const pad = (part: number) => String(part).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

export default function Interviews() {
  const { can, user } = useAuth();
  const list = usePaged<Interview>("/interviews/");
  const [applications, setApplications] = useState<ApplicationOption[]>([]);
  const [staff, setStaff] = useState<Staff[]>([]);
  const [selected, setSelected] = useState<Interview | null>(null);
  const [error, setError] = useState("");
  const [form, setForm] = useState({ application: "", round_name: "", interview_date: "", interviewer_name: "" });
  const [participant, setParticipant] = useState({ user: "", name: "", role: "" });
  const canAdd = can("interviews.add_interview");
  const canChange = can("interviews.change_interview");

  useEffect(() => {
    if (can("applications.view_application")) {
      fetchAll<ApplicationOption>("/applications/").then((result) => setApplications(result.rows)).catch(() => setApplications([]));
    }
    if (can("accounts.view_user")) {
      fetchAll<Staff>("/users/").then((result) => setStaff(result.rows)).catch(() => setStaff([]));
    }
  }, [can]);

  async function create(event: FormEvent) {
    event.preventDefault();
    setError("");
    try {
      await api.post("/interviews/", {
        application: form.application,
        round_name: form.round_name,
        interview_date: new Date(form.interview_date).toISOString(),
        interviewer_name: form.interviewer_name,
      });
      setForm({ application: "", round_name: "", interview_date: "", interviewer_name: "" });
      list.reload();
    } catch (reason) {
      setError(errorMessage(reason, "The interview could not be scheduled."));
    }
  }

  async function reschedule(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selected) return;
    setError("");
    const data = new FormData(event.currentTarget);
    try {
      const response = await api.patch<Interview>(`/interviews/${selected.id}/`, {
        interview_date: new Date(String(data.get("interview_date"))).toISOString(),
        result: String(data.get("result") || selected.result),
        feedback: String(data.get("feedback") ?? selected.feedback),
        round_name: selected.round_name,
        interviewer_name: selected.interviewer_name,
      });
      setSelected(response.data);
      list.reload();
    } catch (reason) {
      setError(errorMessage(reason, "The interview could not be updated."));
    }
  }

  async function addParticipant(event: FormEvent) {
    event.preventDefault();
    if (!selected) return;
    if (!participant.user && !participant.name.trim()) {
      setError("A participant needs a user or a name.");
      return;
    }
    setError("");
    try {
      await api.post("/interview-participants/", {
        interview: selected.id,
        role: participant.role,
        ...(participant.user ? { user: participant.user } : { name: participant.name }),
      });
      setParticipant({ user: "", name: "", role: "" });
      const response = await api.get<Interview>(`/interviews/${selected.id}/`);
      setSelected(response.data);
    } catch (reason) {
      setError(errorMessage(reason, "The participant could not be added."));
    }
  }

  return (
    <>
      <PageHeader eyebrow="INTERVIEWS" title="Interviews" description="Schedule, reschedule, and record participants. Feedback is visible to anyone who can open this page." />
      {error && <Alert>{error}</Alert>}
      {list.error && <Alert>{list.error}</Alert>}
      {canAdd && (
        <Panel title="Schedule">
          <form className="grid gap-3 md:grid-cols-2" onSubmit={create}>
            <Field label="Application">
              <Select required value={form.application} onChange={(event) => setForm({ ...form, application: event.target.value })}>
                <option value="">Select application</option>
                {applications.map((item) => (
                  <option key={item.id} value={item.id}>{item.candidate_name} · {item.job_title} · {item.application_code}</option>
                ))}
              </Select>
            </Field>
            <Field label="Round"><TextInput required value={form.round_name} onChange={(event) => setForm({ ...form, round_name: event.target.value })} /></Field>
            <Field label="Date and time"><TextInput required type="datetime-local" value={form.interview_date} onChange={(event) => setForm({ ...form, interview_date: event.target.value })} /></Field>
            <Field label="Interviewer name"><TextInput value={form.interviewer_name} onChange={(event) => setForm({ ...form, interviewer_name: event.target.value })} /></Field>
            <button className={primaryButton}>Schedule interview</button>
          </form>
        </Panel>
      )}
      <div className="mt-4 overflow-x-auto rounded-xl border border-line bg-white">
        <table className="w-full text-left text-sm">
          <thead className="bg-canvas text-xs uppercase tracking-wide text-muted">
            <tr>
              <th className="px-3 py-2">Candidate</th>
              <th className="px-3 py-2">Job</th>
              <th className="px-3 py-2">Round</th>
              <th className="px-3 py-2">When</th>
              <th className="px-3 py-2">Result</th>
            </tr>
          </thead>
          <tbody>
            {list.rows.map((row) => (
              <tr key={row.id} className="cursor-pointer border-t border-line hover:bg-canvas" onClick={() => setSelected(row)}>
                <td className="px-3 py-2 font-semibold">{row.candidate_name}</td>
                <td className="px-3 py-2">{row.job_title}</td>
                <td className="px-3 py-2">{row.round_name}</td>
                <td className="px-3 py-2">{new Date(row.interview_date).toLocaleString()}</td>
                <td className="px-3 py-2">{statusLabel(row.result)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {!list.rows.length && !list.loading && <Empty>No interviews.</Empty>}
      </div>
      <Pager page={list.page} count={list.count} onPage={list.setPage} />
      {selected && (
        <div className="mt-4 grid gap-4 lg:grid-cols-2">
          <Panel title={`${selected.candidate_name} · ${selected.round_name}`}>
            <p className="mb-2 text-sm text-muted">{selected.job_title} · {selected.application_code}</p>
            <p className="mb-3 text-sm"><b>Feedback.</b> {selected.feedback || "No feedback yet."}</p>
            {canChange ? (
              <form className="grid gap-2" onSubmit={reschedule}>
                <Field label="Reschedule">
                  <TextInput name="interview_date" type="datetime-local" required defaultValue={toLocalInput(selected.interview_date)} />
                </Field>
                <Field label="Result">
                  <Select name="result" defaultValue={selected.result}>
                    <option value="PENDING">Pending</option>
                    <option value="PASSED">Passed</option>
                    <option value="FAILED">Failed</option>
                    <option value="ON_HOLD">On hold</option>
                  </Select>
                </Field>
                <Field label="Feedback"><TextArea name="feedback" defaultValue={selected.feedback} /></Field>
                <button className={primaryButton}>Save interview</button>
              </form>
            ) : null}
          </Panel>
          <Panel title="Participants">
            <ul className="mb-3 text-sm">
              {selected.participants?.map((item) => (
                <li key={item.id}>{item.user_name || item.name || "Participant"}{item.role ? ` · ${item.role}` : ""}</li>
              ))}
              {!selected.participants?.length && <Empty>No participants.</Empty>}
            </ul>
            {canAdd && (
              <form className="grid gap-2" onSubmit={addParticipant}>
                {can("accounts.view_user") && (
                  <Select value={participant.user} onChange={(event) => setParticipant({ ...participant, user: event.target.value })}>
                    <option value="">Named participant</option>
                    {staff.map((person) => <option key={person.id} value={person.id}>{person.first_name || person.username} {person.last_name}</option>)}
                  </Select>
                )}
                {!participant.user && (
                  <TextInput placeholder="Participant name" value={participant.name} onChange={(event) => setParticipant({ ...participant, name: event.target.value })} />
                )}
                {user && !can("accounts.view_user") && (
                  <button type="button" className={primaryButton} onClick={() => setParticipant({ ...participant, user: user.id, name: "" })}>Add myself</button>
                )}
                <TextInput placeholder="Role" value={participant.role} onChange={(event) => setParticipant({ ...participant, role: event.target.value })} />
                <button className={primaryButton}>Add participant</button>
              </form>
            )}
          </Panel>
        </div>
      )}
    </>
  );
}
