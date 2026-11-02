import { useEffect, useState, type FormEvent } from "react";
import { useAuth } from "../../auth/session";
import { Alert, Empty, Field, PageHeader, Pager, Panel, Select, TextArea, TextInput, primaryButton, tinyButton } from "../../components/ui";
import { errorMessage } from "../../lib/errors";
import { fetchAll } from "../../lib/paging";
import { usePaged } from "../../lib/usePaged";
import { inr, normalizeSkillName, statusLabel } from "../../lib/workflow";
import api, { apiOrigin } from "../../services/api";

type Resume = { id: string; original_filename: string; version: number; is_primary: boolean; parsing_status: string };
type Candidate = {
  id: string;
  candidate_code: string;
  full_name: string;
  email: string;
  phone: string;
  location: string;
  total_experience: string | null;
  current_company: string;
  source: string;
  privacy_notice_version: string;
  current_ctc?: string | null;
  expected_ctc?: string | null;
  resumes: Resume[];
};
type Note = { id: string; note: string; user_name?: string; created_at: string };
type Skill = { id: string; name: string };
type CandidateSkill = { id: string; skill_name: string; experience_months: number | null };

const SOURCES = ["LINKEDIN", "REFERRAL", "JOB_PORTAL", "WEBSITE", "INTERNAL", "OTHER"];

export default function Candidates() {
  const { can } = useAuth();
  const [query, setQuery] = useState("");
  const [search, setSearch] = useState("");
  const list = usePaged<Candidate>("/candidates/", search ? { q: search } : {});
  const [selected, setSelected] = useState<Candidate | null>(null);
  const [notes, setNotes] = useState<Note[]>([]);
  const [skills, setSkills] = useState<Skill[]>([]);
  const [candidateSkills, setCandidateSkills] = useState<CandidateSkill[]>([]);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [form, setForm] = useState({ name: "", email: "", phone: "", location: "", experience: "", company: "", source: "OTHER", noticeVersion: "", consent: false });
  const [resume, setResume] = useState<File | null>(null);
  const [note, setNote] = useState("");
  const [skillForm, setSkillForm] = useState({ skill: "", name: "", months: "" });

  useEffect(() => {
    if (!can("matching.view_skill")) return;
    fetchAll<Skill>("/skills/").then((result) => setSkills(result.rows)).catch(() => setSkills([]));
  }, [can]);

  async function openCandidate(row: Candidate) {
    setSelected(row);
    setError("");
    try {
      const [detail, noteResponse, skillResponse] = await Promise.all([
        api.get<Candidate>(`/candidates/${row.id}/`),
        can("candidates.view_candidatenote") ? api.get("/candidate-notes/", { params: { candidate: row.id } }) : Promise.resolve({ data: { results: [] } }),
        can("matching.view_candidateskill") ? api.get("/candidate-skills/", { params: { candidate: row.id } }) : Promise.resolve({ data: { results: [] } }),
      ]);
      setSelected(detail.data);
      setNotes(noteResponse.data.results ?? noteResponse.data);
      setCandidateSkills(skillResponse.data.results ?? skillResponse.data);
    } catch (reason) {
      setError(errorMessage(reason, "The candidate could not be opened."));
    }
  }

  async function create(event: FormEvent) {
    event.preventDefault();
    setError("");
    setNotice("");
    if (!form.consent) {
      setError("Candidate consent is required before a profile can be stored.");
      return;
    }
    if (!form.noticeVersion.trim()) {
      setError("Record the privacy notice version the candidate accepted.");
      return;
    }
    try {
      const response = await api.post<Candidate>("/candidates/", {
        full_name: form.name,
        email: form.email,
        phone: form.phone,
        location: form.location,
        current_company: form.company,
        total_experience: form.experience || null,
        source: form.source,
        consent_acknowledged: true,
        privacy_notice_version: form.noticeVersion.trim(),
      });
      if (resume && can("candidates.add_resume")) {
        const body = new FormData();
        body.append("file", resume);
        await api.post(`/candidates/${response.data.id}/upload-resume/`, body, { headers: { "Content-Type": "multipart/form-data" } });
      }
      setForm({ name: "", email: "", phone: "", location: "", experience: "", company: "", source: "OTHER", noticeVersion: "", consent: false });
      setResume(null);
      setNotice(`${response.data.full_name} was saved with the recorded consent.`);
      list.reload();
    } catch (reason) {
      setError(errorMessage(reason, "Could not save the candidate. Consent and the privacy notice version are required. Resume files must be PDF or DOCX, max 10 MB."));
    }
  }

  async function download(resumeId: string) {
    setError("");
    try {
      const response = await api.post(`/resumes/${resumeId}/download/`);
      window.open(`${apiOrigin()}${response.data.download_path}`, "_blank", "noopener");
    } catch (reason) {
      setError(errorMessage(reason, "The resume could not be downloaded."));
    }
  }

  async function addNote(event: FormEvent) {
    event.preventDefault();
    if (!selected || !note.trim()) return;
    setError("");
    try {
      await api.post("/candidate-notes/", { candidate: selected.id, note });
      setNote("");
      await openCandidate(selected);
    } catch (reason) {
      setError(errorMessage(reason, "The note could not be saved."));
    }
  }

  async function addSkill(event: FormEvent) {
    event.preventDefault();
    if (!selected) return;
    setError("");
    try {
      let skillId = skillForm.skill;
      if (!skillId) {
        if (!can("matching.add_skill") || !skillForm.name.trim()) {
          setError("Choose a skill, or enter a name you are allowed to create.");
          return;
        }
        const created = await api.post<Skill>("/skills/", { name: skillForm.name.trim(), normalized_name: normalizeSkillName(skillForm.name) });
        skillId = created.data.id;
        setSkills((current) => [...current, created.data]);
      }
      await api.post("/candidate-skills/", {
        candidate: selected.id,
        skill: skillId,
        ...(skillForm.months ? { experience_months: Number(skillForm.months) } : {}),
      });
      setSkillForm({ skill: "", name: "", months: "" });
      await openCandidate(selected);
    } catch (reason) {
      setError(errorMessage(reason, "The skill could not be saved."));
    }
  }

  return (
    <>
      <PageHeader eyebrow="TALENT DATABASE" title="Candidates" description="Profiles are stored only after consent and a privacy notice version." />
      {error && <Alert>{error}</Alert>}
      {notice && <Alert tone="success">{notice}</Alert>}
      {list.error && <Alert>{list.error}</Alert>}
      {can("candidates.add_candidate") && (
        <Panel title="Add candidate">
          <form className="grid gap-3" onSubmit={create}>
            <div className="grid gap-3 md:grid-cols-3">
              <Field label="Full name"><TextInput required placeholder="Full name" value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} /></Field>
              <Field label="Email"><TextInput type="email" value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} /></Field>
              <Field label="Phone"><TextInput value={form.phone} onChange={(event) => setForm({ ...form, phone: event.target.value })} /></Field>
              <Field label="Location"><TextInput value={form.location} onChange={(event) => setForm({ ...form, location: event.target.value })} /></Field>
              <Field label="Experience (years)"><TextInput type="number" step="0.5" value={form.experience} onChange={(event) => setForm({ ...form, experience: event.target.value })} /></Field>
              <Field label="Current company"><TextInput value={form.company} onChange={(event) => setForm({ ...form, company: event.target.value })} /></Field>
              <Field label="Source">
                <Select value={form.source} onChange={(event) => setForm({ ...form, source: event.target.value })}>
                  {SOURCES.map((source) => <option key={source} value={source}>{statusLabel(source)}</option>)}
                </Select>
              </Field>
              <Field label="Privacy notice version">
                <TextInput required placeholder="Privacy notice version" value={form.noticeVersion} onChange={(event) => setForm({ ...form, noticeVersion: event.target.value })} />
              </Field>
              {can("candidates.add_resume") && (
                <Field label="Resume (PDF or DOCX, max 10 MB)">
                  <input type="file" accept=".pdf,.docx" onChange={(event) => setResume(event.target.files?.[0] ?? null)} />
                </Field>
              )}
            </div>
            <label className="flex items-start gap-2 text-sm">
              <input type="checkbox" checked={form.consent} onChange={(event) => setForm({ ...form, consent: event.target.checked })} required />
              <span>Candidate has given consent for this notice version</span>
            </label>
            <button className={primaryButton}>Save candidate</button>
          </form>
        </Panel>
      )}
      <form className="mt-4 flex gap-2" onSubmit={(event) => { event.preventDefault(); setSearch(query); }}>
        <TextInput placeholder="Search name, email or location" value={query} onChange={(event) => setQuery(event.target.value)} />
        <button className={primaryButton}>Search</button>
      </form>
      <div className="mt-4 overflow-x-auto rounded-xl border border-line bg-white">
        <table className="w-full text-left text-sm">
          <thead className="bg-canvas text-xs uppercase tracking-wide text-muted">
            <tr>
              <th className="px-3 py-2">Candidate</th>
              <th className="px-3 py-2">Code</th>
              <th className="px-3 py-2">Email</th>
              <th className="px-3 py-2">Location</th>
              <th className="px-3 py-2">Experience</th>
            </tr>
          </thead>
          <tbody>
            {list.rows.map((candidate) => (
              <tr key={candidate.id} className="cursor-pointer border-t border-line hover:bg-canvas" onClick={() => openCandidate(candidate)}>
                <td className="px-3 py-2 font-semibold">{candidate.full_name}</td>
                <td className="px-3 py-2">{candidate.candidate_code}</td>
                <td className="px-3 py-2">{candidate.email || "—"}</td>
                <td className="px-3 py-2">{candidate.location || "—"}</td>
                <td className="px-3 py-2">{candidate.total_experience || "—"} yrs</td>
              </tr>
            ))}
          </tbody>
        </table>
        {!list.rows.length && !list.loading && <Empty>No candidates found.</Empty>}
      </div>
      <Pager page={list.page} count={list.count} onPage={list.setPage} />
      {selected && (
        <div className="mt-4 grid gap-4 lg:grid-cols-3">
          <Panel title="Profile">
            <p className="text-sm">{selected.candidate_code} · {statusLabel(selected.source)}</p>
            <p className="text-sm text-muted">Notice {selected.privacy_notice_version}</p>
            {can("candidates.view_candidate_compensation") && ("current_ctc" in selected || "expected_ctc" in selected) && (
              <p className="mt-2 text-sm">Current CTC {inr(selected.current_ctc)} · Expected CTC {inr(selected.expected_ctc)}</p>
            )}
            <h3 className="mt-3 text-sm font-bold">Resumes</h3>
            <ul className="text-sm">
              {(selected.resumes || []).map((item) => (
                <li key={item.id} className="mt-1 flex items-center justify-between gap-2">
                  <span>{item.original_filename} · v{item.version} · {statusLabel(item.parsing_status)}</span>
                  {can("candidates.view_resume_content") && (
                    <button type="button" className={tinyButton} onClick={() => download(item.id)}>Download</button>
                  )}
                </li>
              ))}
              {!selected.resumes?.length && <Empty>No resume uploaded.</Empty>}
            </ul>
          </Panel>
          {can("candidates.view_candidatenote") && (
            <Panel title="Notes">
              <ul className="mb-3 text-sm">
                {notes.map((item) => <li key={item.id} className="mb-2"><b>{item.user_name}</b> {item.note}</li>)}
                {!notes.length && <Empty>No notes.</Empty>}
              </ul>
              {can("candidates.add_candidatenote") && (
                <form className="grid gap-2" onSubmit={addNote}>
                  <TextArea value={note} onChange={(event) => setNote(event.target.value)} placeholder="Note" />
                  <button className={primaryButton}>Save note</button>
                </form>
              )}
            </Panel>
          )}
          {can("matching.view_candidateskill") && (
            <Panel title="Skills">
              <ul className="mb-3 text-sm">
                {candidateSkills.map((item) => <li key={item.id}>{item.skill_name}{item.experience_months ? ` · ${item.experience_months} months` : ""}</li>)}
                {!candidateSkills.length && <Empty>No skills.</Empty>}
              </ul>
              {can("matching.add_candidateskill") && (
                <form className="grid gap-2" onSubmit={addSkill}>
                  <Select value={skillForm.skill} onChange={(event) => setSkillForm({ ...skillForm, skill: event.target.value })}>
                    <option value="">Existing skill</option>
                    {skills.map((skill) => <option key={skill.id} value={skill.id}>{skill.name}</option>)}
                  </Select>
                  {can("matching.add_skill") && <TextInput placeholder="Or new skill name" value={skillForm.name} onChange={(event) => setSkillForm({ ...skillForm, name: event.target.value })} />}
                  <TextInput type="number" min={0} placeholder="Experience months" value={skillForm.months} onChange={(event) => setSkillForm({ ...skillForm, months: event.target.value })} />
                  <button className={primaryButton}>Save skill</button>
                </form>
              )}
            </Panel>
          )}
        </div>
      )}
    </>
  );
}
