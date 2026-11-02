import { useEffect, useState, type FormEvent } from "react";
import { useAuth } from "../../auth/session";
import { Alert, Field, PageHeader, Panel, TextArea, TextInput, primaryButton } from "../../components/ui";
import { errorMessage } from "../../lib/errors";
import api from "../../services/api";

type Config = {
  candidate_retention_days: number | null;
  application_retention_days: number | null;
  resume_retention_days: number | null;
  audit_log_retention_days: number | null;
  privacy_notice_version: string;
  privacy_notice_text: string;
  updated_at: string;
};

const FIELDS: { key: keyof Config; label: string }[] = [
  { key: "candidate_retention_days", label: "Candidate retention days" },
  { key: "application_retention_days", label: "Application retention days" },
  { key: "resume_retention_days", label: "Resume retention days" },
  { key: "audit_log_retention_days", label: "Audit log retention days" },
];

const EMPTY: Config = {
  candidate_retention_days: null,
  application_retention_days: null,
  resume_retention_days: null,
  audit_log_retention_days: null,
  privacy_notice_version: "",
  privacy_notice_text: "",
  updated_at: "",
};

export default function Settings() {
  const { can } = useAuth();
  const editable = can("organizations.change_systemconfiguration");
  const [form, setForm] = useState<Config>(EMPTY);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  useEffect(() => {
    api
      .get<Config>("/system-configuration/")
      .then((response) => setForm({ ...EMPTY, ...response.data }))
      .catch((reason) => setError(errorMessage(reason, "System configuration could not be loaded.")));
  }, []);

  function days(value: number | null) {
    if (value === null || Number.isNaN(value)) return null;
    return value;
  }

  async function save(event: FormEvent) {
    event.preventDefault();
    setError("");
    setNotice("");
    const payload = {
      candidate_retention_days: days(form.candidate_retention_days),
      application_retention_days: days(form.application_retention_days),
      resume_retention_days: days(form.resume_retention_days),
      audit_log_retention_days: days(form.audit_log_retention_days),
      privacy_notice_version: form.privacy_notice_version,
      privacy_notice_text: form.privacy_notice_text,
    };
    try {
      const response = await api.patch<Config>("/system-configuration/", payload);
      setForm({ ...EMPTY, ...response.data });
      setNotice("Settings saved. Blank retention fields stay unset.");
    } catch (reason) {
      setError(errorMessage(reason, "Settings could not be saved."));
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="ORGANIZATION"
        title="Settings"
        description="Retention periods stay empty until someone with configuration access sets them. Nothing here deletes data."
      />
      {error && <Alert>{error}</Alert>}
      {notice && <Alert tone="success">{notice}</Alert>}
      <Panel>
        <form className="grid gap-4" onSubmit={save}>
          <div className="grid gap-3 md:grid-cols-2">
            {FIELDS.map((field) => (
              <Field key={field.key} label={field.label}>
                <TextInput
                  type="number"
                  min={1}
                  value={form[field.key] ?? ""}
                  disabled={!editable}
                  placeholder="Not set"
                  onChange={(event) => setForm({ ...form, [field.key]: event.target.value === "" ? null : Number(event.target.value) })}
                />
              </Field>
            ))}
          </div>
          <Field label="Privacy notice version">
            <TextInput
              value={form.privacy_notice_version}
              disabled={!editable}
              onChange={(event) => setForm({ ...form, privacy_notice_version: event.target.value })}
            />
          </Field>
          <Field label="Privacy notice text">
            <TextArea
              value={form.privacy_notice_text}
              disabled={!editable}
              onChange={(event) => setForm({ ...form, privacy_notice_text: event.target.value })}
            />
          </Field>
          {editable && <button className={primaryButton}>Save settings</button>}
          {form.updated_at && <p className="text-xs text-muted">Updated {new Date(form.updated_at).toLocaleString()}</p>}
        </form>
      </Panel>
    </>
  );
}
