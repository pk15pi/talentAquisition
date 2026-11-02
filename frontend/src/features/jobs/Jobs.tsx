import { useEffect, useState, type FormEvent } from "react";
import { canSeeCommercialTerms } from "../../auth/types";
import { useAuth } from "../../auth/session";
import { Alert, Empty, Field, PageHeader, Pager, Panel, Select, Tag, TextArea, TextInput, primaryButton, secondaryButton, tinyButton } from "../../components/ui";
import { errorMessage } from "../../lib/errors";
import { fetchAll } from "../../lib/paging";
import { usePaged } from "../../lib/usePaged";
import { normalizeSkillName, statusLabel } from "../../lib/workflow";
import api from "../../services/api";

type Client = { id: string; company_name: string };
type Assignment = { id: string; recruiter: string; recruiter_name?: string; is_active: boolean };
type Job = {
  id: string;
  job_code: string;
  title: string;
  client: string;
  client_name?: string;
  location: string;
  status: string;
  priority: string;
  assignments: Assignment[];
};
type Staff = { id: string; username: string; first_name: string; last_name: string; can_be_assigned_recruiter: boolean };
type Skill = { id: string; name: string };
type JobSkill = { id: string; skill: string; skill_name: string; is_mandatory: boolean; weight: number };
type MatchResult = {
  id: string;
  candidate_name: string;
  candidate_code: string;
  overall_score: string;
  skills_score: string;
  experience_score: string;
  location_score: string;
  responsibility_score: string;
  notice_period_score: string;
  missing_mandatory_skills: string[];
  mandatory_skill_failure: boolean;
  explanation: {
    matched_skills?: string[];
    missing_skills?: string[];
    missing_mandatory_skills?: string[];
    alias_matches?: { skill: string; alias: string }[];
    experience?: { candidate_years: string; required_min: string; required_max: string };
    location?: { matched?: boolean; job?: string; candidate?: string };
    responsibility?: { matched_terms?: string[]; available?: boolean };
    notice_period?: { within_limit?: boolean; job_days?: number | null; candidate_days?: number | null };
  };
};
type MatchRun = { id: string; candidates_processed: number; engine_version: string; results: MatchResult[] };

export default function Jobs() {
  const { can } = useAuth();
  const showFees = canSeeCommercialTerms(can);
  const list = usePaged<Job>("/jobs/");
  const [clients, setClients] = useState<Client[]>([]);
  const [recruiters, setRecruiters] = useState<Staff[]>([]);
  const [skills, setSkills] = useState<Skill[]>([]);
  const [jobSkills, setJobSkills] = useState<JobSkill[]>([]);
  const [selected, setSelected] = useState<string>("");
  const [picked, setPicked] = useState<string[]>([]);
  const [error, setError] = useState("");
  const [matchRun, setMatchRun] = useState<MatchRun | null>(null);
  const [matching, setMatching] = useState(false);
  const [form, setForm] = useState({ client: "", title: "", jd: "", min: "", max: "", location: "", priority: "MEDIUM", fee_type: "", fee_value: "", guarantee: "" });
  const [skillForm, setSkillForm] = useState({ skill: "", name: "", mandatory: false, weight: "1" });

  useEffect(() => {
    fetchAll<Client>("/clients/").then((result) => setClients(result.rows)).catch(() => setClients([]));
    if (can("accounts.view_user")) {
      fetchAll<Staff>("/users/").then((result) => setRecruiters(result.rows.filter((row) => row.can_be_assigned_recruiter))).catch(() => setRecruiters([]));
    }
    if (can("matching.view_skill")) {
      fetchAll<Skill>("/skills/").then((result) => setSkills(result.rows)).catch(() => setSkills([]));
    }
  }, [can]);

  useEffect(() => {
    if (!selected || !can("matching.view_jobskill")) {
      setJobSkills([]);
      return;
    }
    api.get("/job-skills/", { params: { job: selected } }).then((response) => setJobSkills(response.data.results ?? response.data)).catch(() => setJobSkills([]));
  }, [selected, can]);

  async function create(event: FormEvent) {
    event.preventDefault();
    setError("");
    if (Number(form.max) < Number(form.min)) {
      setError("Maximum experience cannot be below the minimum.");
      return;
    }
    const payload: Record<string, string | number> = {
      client: form.client,
      title: form.title,
      jd_text: form.jd,
      experience_min: form.min,
      experience_max: form.max,
      location: form.location,
      status: "OPEN",
      priority: form.priority,
    };
    if (showFees && form.fee_type) payload.fee_type = form.fee_type;
    if (showFees && form.fee_value) payload.fee_value = form.fee_value;
    if (showFees && form.guarantee) payload.guarantee_period_days = Number(form.guarantee);
    try {
      await api.post("/jobs/", payload);
      setForm({ client: "", title: "", jd: "", min: "", max: "", location: "", priority: "MEDIUM", fee_type: "", fee_value: "", guarantee: "" });
      list.reload();
    } catch (reason) {
      setError(errorMessage(reason, "Could not create the job description."));
    }
  }

  async function match(id: string) {
    setError("");
    setMatching(true);
    setSelected(id);
    try {
      const response = await api.post<MatchRun>(`/jobs/${id}/match/`);
      setMatchRun(response.data);
    } catch (reason) {
      setMatchRun(null);
      setError(errorMessage(reason, "Matching could not be run."));
    } finally {
      setMatching(false);
    }
  }

  async function assign(event: FormEvent) {
    event.preventDefault();
    if (!selected) return;
    if (!picked.length) {
      setError("Select at least one recruiter who is allowed to be assigned.");
      return;
    }
    setError("");
    try {
      await api.post(`/jobs/${selected}/assign/`, { recruiter_ids: picked });
      setPicked([]);
      list.reload();
    } catch (reason) {
      setError(errorMessage(reason, "Recruiters could not be assigned."));
    }
  }

  async function addSkill(event: FormEvent) {
    event.preventDefault();
    if (!selected) return;
    setError("");
    try {
      let skillId = skillForm.skill;
      if (!skillId) {
        if (!skillForm.name.trim() || !can("matching.add_skill")) {
          setError("Choose a skill, or enter a name you are allowed to create.");
          return;
        }
        const created = await api.post<Skill>("/skills/", { name: skillForm.name.trim(), normalized_name: normalizeSkillName(skillForm.name) });
        skillId = created.data.id;
        setSkills((current) => [...current, created.data]);
      }
      await api.post("/job-skills/", { job: selected, skill: skillId, is_mandatory: skillForm.mandatory, weight: Number(skillForm.weight) || 1 });
      setSkillForm({ skill: "", name: "", mandatory: false, weight: "1" });
      const response = await api.get("/job-skills/", { params: { job: selected } });
      setJobSkills(response.data.results ?? response.data);
    } catch (reason) {
      setError(errorMessage(reason, "The skill could not be saved on this JD."));
    }
  }

  const failures = matchRun?.results.filter((row) => row.mandatory_skill_failure) ?? [];

  return (
    <>
      <PageHeader eyebrow="RECRUITMENT" title="Job descriptions" description="Create requirements, capture skills, and review match explanations." />
      {error && <Alert>{error}</Alert>}
      {can("jobs.add_job") && (
        <Panel title="Create a JD">
          <form className="grid gap-3" onSubmit={create}>
            <div className="grid gap-3 md:grid-cols-3">
              <Field label="Client">
                <Select required value={form.client} onChange={(event) => setForm({ ...form, client: event.target.value })}>
                  <option value="">Select client</option>
                  {clients.map((client) => <option key={client.id} value={client.id}>{client.company_name}</option>)}
                </Select>
              </Field>
              <Field label="Job title"><TextInput required value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} /></Field>
              <Field label="Location"><TextInput value={form.location} onChange={(event) => setForm({ ...form, location: event.target.value })} /></Field>
              <Field label="Minimum experience (years)"><TextInput required type="number" step="0.5" value={form.min} onChange={(event) => setForm({ ...form, min: event.target.value })} /></Field>
              <Field label="Maximum experience (years)"><TextInput required type="number" step="0.5" value={form.max} onChange={(event) => setForm({ ...form, max: event.target.value })} /></Field>
              <Field label="Priority">
                <Select value={form.priority} onChange={(event) => setForm({ ...form, priority: event.target.value })}>
                  <option value="LOW">Low</option>
                  <option value="MEDIUM">Medium</option>
                  <option value="HIGH">High</option>
                  <option value="URGENT">Urgent</option>
                </Select>
              </Field>
              {showFees && (
                <>
                  <Field label="Fee override">
                    <Select value={form.fee_type} onChange={(event) => setForm({ ...form, fee_type: event.target.value })}>
                      <option value="">Use client default</option>
                      <option value="PERCENTAGE">Percentage</option>
                      <option value="FIXED">Fixed amount</option>
                    </Select>
                  </Field>
                  <Field label="Fee value"><TextInput value={form.fee_value} onChange={(event) => setForm({ ...form, fee_value: event.target.value })} /></Field>
                  <Field label="Guarantee days"><TextInput type="number" min={1} value={form.guarantee} onChange={(event) => setForm({ ...form, guarantee: event.target.value })} /></Field>
                </>
              )}
            </div>
            <Field label="Job description"><TextArea required value={form.jd} onChange={(event) => setForm({ ...form, jd: event.target.value })} /></Field>
            <button className={primaryButton}>Create JD</button>
          </form>
        </Panel>
      )}
      <div className="mt-4 overflow-x-auto rounded-xl border border-line bg-white">
        <table className="w-full text-left text-sm">
          <thead className="bg-canvas text-xs uppercase tracking-wide text-muted">
            <tr>
              <th className="px-3 py-2">JD</th>
              <th className="px-3 py-2">Title</th>
              <th className="px-3 py-2">Client</th>
              <th className="px-3 py-2">Location</th>
              <th className="px-3 py-2">Status</th>
              <th className="px-3 py-2">Actions</th>
            </tr>
          </thead>
          <tbody>
            {list.rows.map((job) => (
              <tr key={job.id} className="border-t border-line">
                <td className="px-3 py-2">{job.job_code}</td>
                <td className="px-3 py-2 font-semibold">{job.title}</td>
                <td className="px-3 py-2">{job.client_name || "—"}</td>
                <td className="px-3 py-2">{job.location || "—"}</td>
                <td className="px-3 py-2"><Tag>{statusLabel(job.status)}</Tag></td>
                <td className="px-3 py-2">
                  <div className="flex flex-wrap gap-2">
                    <button type="button" className={tinyButton} onClick={() => setSelected(job.id)}>Details</button>
                    {can("jobs.run_match") && (
                      <button type="button" className={tinyButton} disabled={matching} onClick={() => match(job.id)}>Find candidates</button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {!list.rows.length && !list.loading && <Empty>No JDs found.</Empty>}
      </div>
      <Pager page={list.page} count={list.count} onPage={list.setPage} />
      {selected && (
        <div className="mt-4 grid gap-4 lg:grid-cols-2">
          <Panel title="Skills">
            <ul className="mb-3 text-sm">
              {jobSkills.map((row) => (
                <li key={row.id} className={row.is_mandatory ? "font-semibold text-red-800" : ""}>
                  {row.skill_name} · weight {row.weight} {row.is_mandatory ? "· mandatory" : ""}
                </li>
              ))}
              {!jobSkills.length && <Empty>No skills captured.</Empty>}
            </ul>
            {can("matching.add_jobskill") && (
              <form className="grid gap-2" onSubmit={addSkill}>
                <Select value={skillForm.skill} onChange={(event) => setSkillForm({ ...skillForm, skill: event.target.value })}>
                  <option value="">Existing skill</option>
                  {skills.map((skill) => <option key={skill.id} value={skill.id}>{skill.name}</option>)}
                </Select>
                {can("matching.add_skill") && (
                  <TextInput placeholder="Or new skill name" value={skillForm.name} onChange={(event) => setSkillForm({ ...skillForm, name: event.target.value })} />
                )}
                <label className="flex items-center gap-2 text-sm">
                  <input type="checkbox" checked={skillForm.mandatory} onChange={(event) => setSkillForm({ ...skillForm, mandatory: event.target.checked })} />
                  Mandatory
                </label>
                <TextInput type="number" min={1} max={10} value={skillForm.weight} onChange={(event) => setSkillForm({ ...skillForm, weight: event.target.value })} />
                <button className={primaryButton}>Save skill</button>
              </form>
            )}
          </Panel>
          {can("jobs.assign_recruiter") && (
            <Panel title="Assign recruiters">
              <p className="mb-2 text-sm text-muted">
                Current: {list.rows.find((job) => job.id === selected)?.assignments.filter((row) => row.is_active).map((row) => row.recruiter_name || "Recruiter").join(", ") || "None"}
              </p>
              <form className="grid gap-2" onSubmit={assign}>
                {recruiters.map((recruiter) => (
                  <label key={recruiter.id} className="flex items-center gap-2 text-sm">
                    <input
                      type="checkbox"
                      checked={picked.includes(recruiter.id)}
                      onChange={(event) => setPicked(event.target.checked ? [...picked, recruiter.id] : picked.filter((id) => id !== recruiter.id))}
                    />
                    {recruiter.first_name || recruiter.username} {recruiter.last_name}
                  </label>
                ))}
                {!recruiters.length && <p className="text-sm text-muted">No users who can be assigned are visible to you.</p>}
                {recruiters.length > 0 && <button className={secondaryButton}>Assign selected</button>}
              </form>
            </Panel>
          )}
        </div>
      )}
      {matchRun && (
        <div className="mt-4">
          <Alert tone="info">
            Matched {matchRun.candidates_processed} active candidate{matchRun.candidates_processed === 1 ? "" : "s"} with {matchRun.engine_version}. Nobody was shortlisted or rejected automatically.
          </Alert>
          {failures.length > 0 && (
            <Alert>
              Mandatory skill failure for {failures.map((row) => row.candidate_name).join(", ")}. Missing skills are listed on each result. The score is not capped and the application status is unchanged.
            </Alert>
          )}
          <div className="grid gap-3">
            {matchRun.results.map((result) => (
              <article key={result.id} className={`rounded-xl border p-4 ${result.mandatory_skill_failure ? "border-red-300 bg-red-50" : "border-line bg-white"}`}>
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <h3 className="font-display text-lg font-bold">{result.candidate_name} <span className="text-sm font-medium text-muted">{result.candidate_code}</span></h3>
                  <b>{result.overall_score}</b>
                </div>
                {result.mandatory_skill_failure && (
                  <p className="mt-2 text-sm font-bold text-red-800">
                    Missing mandatory skills: {(result.missing_mandatory_skills || result.explanation.missing_mandatory_skills || []).join(", ") || "see explanation"}
                  </p>
                )}
                <p className="mt-2 text-xs text-muted">
                  Skills {result.skills_score} · Experience {result.experience_score} · Responsibilities {result.responsibility_score} · Location {result.location_score} · Notice {result.notice_period_score}
                </p>
                <p className="mt-2 text-sm">Matched: {(result.explanation.matched_skills || []).join(", ") || "none"}</p>
                <p className="text-sm">Missing: {(result.explanation.missing_skills || []).join(", ") || "none"}</p>
                {!!result.explanation.alias_matches?.length && (
                  <p className="text-sm">Aliases: {result.explanation.alias_matches.map((item) => `${item.skill} via ${item.alias}`).join(", ")}</p>
                )}
                {result.explanation.experience && (
                  <p className="text-sm">Experience {result.explanation.experience.candidate_years} years, required {result.explanation.experience.required_min}–{result.explanation.experience.required_max}.</p>
                )}
              </article>
            ))}
            {!matchRun.results.length && <Empty>No active candidates were scored.</Empty>}
          </div>
        </div>
      )}
    </>
  );
}
