import { useState, type FormEvent } from "react";
import { useAuth } from "../../auth/session";
import { Alert, Empty, Field, PageHeader, Pager, Panel, Select, Tag, TextInput, primaryButton, secondaryButton } from "../../components/ui";
import { errorMessage } from "../../lib/errors";
import { usePaged } from "../../lib/usePaged";
import { ROLE_LABELS, displayName } from "../../auth/types";
import api from "../../services/api";

type Staff = {
  id: string;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  employee_code: string | null;
  role: string;
  phone: string;
  is_active: boolean;
  can_own_client: boolean;
  can_be_assigned_recruiter: boolean;
};

const ROLES = Object.keys(ROLE_LABELS);

export default function Users() {
  const { can, user } = useAuth();
  const list = usePaged<Staff>("/users/");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [form, setForm] = useState({ username: "", password: "", first_name: "", last_name: "", email: "", phone: "", role: "HR", employee_code: "" });

  async function create(event: FormEvent) {
    event.preventDefault();
    setError("");
    setNotice("");
    const payload: Record<string, string> = {
      username: form.username,
      password: form.password,
      first_name: form.first_name,
      last_name: form.last_name,
      email: form.email,
      phone: form.phone,
      role: form.role,
    };
    if (form.employee_code.trim()) payload.employee_code = form.employee_code.trim();
    try {
      await api.post("/users/", payload);
      setForm({ username: "", password: "", first_name: "", last_name: "", email: "", phone: "", role: "HR", employee_code: "" });
      setNotice("Account created. The role group is added now and is not rewritten on later saves.");
      list.reload();
    } catch (reason) {
      setError(errorMessage(reason, "The account could not be created."));
    }
  }

  async function save(staff: Staff, patch: Record<string, string | boolean>) {
    setError("");
    try {
      await api.patch(`/users/${staff.id}/`, patch);
      list.reload();
    } catch (reason) {
      setError(errorMessage(reason, "The account could not be updated."));
    }
  }

  async function deactivate(staff: Staff) {
    setError("");
    try {
      await api.delete(`/users/${staff.id}/`);
      list.reload();
    } catch (reason) {
      setError(errorMessage(reason, "The account could not be deactivated."));
    }
  }

  return (
    <>
      <PageHeader eyebrow="ACCESS" title="Users" description="Staff accounts. Group membership follows the role chosen at creation." />
      {error && <Alert>{error}</Alert>}
      {notice && <Alert tone="success">{notice}</Alert>}
      {list.error && <Alert>{list.error}</Alert>}
      {can("accounts.add_user") && (
        <Panel title="Add staff">
          <form className="grid gap-3 md:grid-cols-3" onSubmit={create}>
            <Field label="Username"><TextInput required value={form.username} onChange={(event) => setForm({ ...form, username: event.target.value })} /></Field>
            <Field label="Password (at least 10 characters)"><TextInput required minLength={10} type="password" value={form.password} onChange={(event) => setForm({ ...form, password: event.target.value })} /></Field>
            <Field label="Role">
              <Select value={form.role} onChange={(event) => setForm({ ...form, role: event.target.value })}>
                {ROLES.map((role) => <option key={role} value={role}>{ROLE_LABELS[role]}</option>)}
              </Select>
            </Field>
            <Field label="First name"><TextInput value={form.first_name} onChange={(event) => setForm({ ...form, first_name: event.target.value })} /></Field>
            <Field label="Last name"><TextInput value={form.last_name} onChange={(event) => setForm({ ...form, last_name: event.target.value })} /></Field>
            <Field label="Email"><TextInput type="email" value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} /></Field>
            <Field label="Phone"><TextInput value={form.phone} onChange={(event) => setForm({ ...form, phone: event.target.value })} /></Field>
            <Field label="Employee code"><TextInput value={form.employee_code} onChange={(event) => setForm({ ...form, employee_code: event.target.value })} /></Field>
            <div className="flex items-end"><button className={primaryButton}>Create account</button></div>
          </form>
          <p className="mt-3 text-xs text-muted">Changing the role later does not add or remove groups. Password is not stored in the page after save.</p>
        </Panel>
      )}
      <div className="mt-4 overflow-x-auto rounded-xl border border-line bg-white">
        <table className="w-full min-w-[720px] text-left text-sm">
          <thead className="bg-canvas text-xs uppercase tracking-wide text-muted">
            <tr>
              <th className="px-3 py-2">Name</th>
              <th className="px-3 py-2">Username</th>
              <th className="px-3 py-2">Role</th>
              <th className="px-3 py-2">Flags</th>
              <th className="px-3 py-2">Status</th>
              {can("accounts.change_user") && <th className="px-3 py-2">Update</th>}
            </tr>
          </thead>
          <tbody>
            {list.rows.map((staff) => (
              <tr key={staff.id} className="border-t border-line">
                <td className="px-3 py-2 font-semibold">{displayName(staff)}</td>
                <td className="px-3 py-2">{staff.username}</td>
                <td className="px-3 py-2">{ROLE_LABELS[staff.role] || staff.role}</td>
                <td className="px-3 py-2 text-xs text-muted">
                  {staff.can_own_client ? "Can own clients. " : ""}
                  {staff.can_be_assigned_recruiter ? "Can be assigned as recruiter." : ""}
                </td>
                <td className="px-3 py-2">{staff.is_active ? <Tag>Active</Tag> : <Tag>Inactive</Tag>}</td>
                {can("accounts.change_user") && (
                  <td className="px-3 py-2">
                    <div className="flex flex-wrap gap-2">
                      <Select aria-label={`Role for ${staff.username}`} defaultValue={staff.role} onChange={(event) => save(staff, { role: event.target.value })}>
                        {ROLES.map((role) => <option key={role} value={role}>{ROLE_LABELS[role]}</option>)}
                      </Select>
                      {can("accounts.delete_user") && staff.is_active && staff.id !== user?.id && (
                        <button type="button" className={secondaryButton} onClick={() => deactivate(staff)}>Deactivate</button>
                      )}
                    </div>
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
        {!list.rows.length && !list.loading && <Empty>No staff records.</Empty>}
      </div>
      <Pager page={list.page} count={list.count} onPage={list.setPage} />
    </>
  );
}
