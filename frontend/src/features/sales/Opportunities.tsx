import { useEffect, useState, type FormEvent } from "react";
import { useAuth } from "../../auth/session";
import { Alert, Empty, Field, PageHeader, Pager, Panel, Select, TextArea, TextInput, primaryButton } from "../../components/ui";
import { errorMessage } from "../../lib/errors";
import { fetchAll } from "../../lib/paging";
import { usePaged } from "../../lib/usePaged";
import { inr, statusLabel } from "../../lib/workflow";
import api from "../../services/api";

type Opportunity = {
  id: string;
  client: string;
  client_name?: string;
  owner: string;
  owner_name?: string;
  title: string;
  stage: string;
  expected_value: string | null;
  notes: string;
  next_follow_up: string | null;
};

type ClientOption = { id: string; company_name: string; client_code: string };
type Staff = { id: string; username: string; first_name: string; last_name: string };

const STAGES = ["NEW", "CONTACTED", "QUALIFIED", "PROPOSAL", "WON", "LOST"];

export default function Opportunities() {
  const { can } = useAuth();
  const list = usePaged<Opportunity>("/sales-opportunities/");
  const [clients, setClients] = useState<ClientOption[]>([]);
  const [owners, setOwners] = useState<Staff[]>([]);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [form, setForm] = useState({ client: "", title: "", stage: "NEW", expected_value: "", notes: "", owner: "" });

  useEffect(() => {
    if (!can("clients.view_client")) return;
    fetchAll<ClientOption>("/clients/").then((result) => setClients(result.rows)).catch(() => setClients([]));
  }, [can]);

  useEffect(() => {
    if (!can("sales.view_all_salesopportunity") || !can("accounts.view_user")) return;
    fetchAll<Staff>("/users/").then((result) => setOwners(result.rows)).catch(() => setOwners([]));
  }, [can]);

  async function create(event: FormEvent) {
    event.preventDefault();
    setError("");
    setNotice("");
    try {
      await api.post("/sales-opportunities/", {
        client: form.client,
        title: form.title,
        stage: form.stage,
        expected_value: form.expected_value || null,
        notes: form.notes,
        ...(can("sales.view_all_salesopportunity") && form.owner ? { owner: form.owner } : {}),
      });
      setForm({ client: "", title: "", stage: "NEW", expected_value: "", notes: "", owner: "" });
      setNotice("Opportunity saved.");
      list.reload();
    } catch (reason) {
      setError(errorMessage(reason, "The opportunity was not saved."));
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="SALES"
        title="Opportunities"
        description="Expected value is visible on opportunities you are allowed to read. Sales see their own rows. Reassignment requires the all-opportunities permission."
      />
      {error && <Alert>{error}</Alert>}
      {notice && <Alert tone="success">{notice}</Alert>}
      {list.error && <Alert>{list.error}</Alert>}
      {can("sales.add_salesopportunity") && (
        <Panel title="Add opportunity">
          <form className="grid gap-3 md:grid-cols-2" onSubmit={create}>
            <Field label="Client">
              <Select required value={form.client} onChange={(event) => setForm({ ...form, client: event.target.value })}>
                <option value="">Choose a client</option>
                {clients.map((client) => (
                  <option key={client.id} value={client.id}>{client.client_code} · {client.company_name}</option>
                ))}
              </Select>
            </Field>
            <Field label="Title"><TextInput required value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} /></Field>
            <Field label="Stage">
              <Select value={form.stage} onChange={(event) => setForm({ ...form, stage: event.target.value })}>
                {STAGES.map((stage) => <option key={stage} value={stage}>{statusLabel(stage)}</option>)}
              </Select>
            </Field>
            <Field label="Expected value"><TextInput type="number" min={0} step="0.01" value={form.expected_value} onChange={(event) => setForm({ ...form, expected_value: event.target.value })} /></Field>
            {can("sales.view_all_salesopportunity") && (
              <Field label="Owner">
                <Select value={form.owner} onChange={(event) => setForm({ ...form, owner: event.target.value })}>
                  <option value="">Keep me</option>
                  {owners.map((owner) => (
                    <option key={owner.id} value={owner.id}>{owner.first_name || owner.username}</option>
                  ))}
                </Select>
              </Field>
            )}
            <Field label="Notes"><TextArea value={form.notes} onChange={(event) => setForm({ ...form, notes: event.target.value })} /></Field>
            <button className={primaryButton}>Save opportunity</button>
          </form>
        </Panel>
      )}
      <div className="mt-4 overflow-x-auto rounded-xl border border-line bg-white">
        <table className="w-full text-left text-sm">
          <thead className="bg-canvas text-xs uppercase tracking-wide text-muted">
            <tr>
              <th className="px-3 py-2">Title</th>
              <th className="px-3 py-2">Client</th>
              <th className="px-3 py-2">Stage</th>
              <th className="px-3 py-2">Owner</th>
              <th className="px-3 py-2">Expected value</th>
            </tr>
          </thead>
          <tbody>
            {list.rows.map((row) => (
              <tr key={row.id} className="border-t border-line">
                <td className="px-3 py-2 font-semibold">{row.title}</td>
                <td className="px-3 py-2">{row.client_name || row.client}</td>
                <td className="px-3 py-2">{statusLabel(row.stage)}</td>
                <td className="px-3 py-2">{row.owner_name || "—"}</td>
                <td className="px-3 py-2">{row.expected_value ? inr(row.expected_value) : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {!list.rows.length && !list.loading && <Empty>No opportunities.</Empty>}
      </div>
      <Pager page={list.page} count={list.count} onPage={list.setPage} />
    </>
  );
}
