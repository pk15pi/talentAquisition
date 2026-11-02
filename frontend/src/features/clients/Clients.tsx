import { useEffect, useState, type FormEvent } from "react";
import { canSeeCommercialTerms } from "../../auth/types";
import { useAuth } from "../../auth/session";
import { Alert, Empty, Field, PageHeader, Pager, Panel, Select, Tag, TextArea, TextInput, primaryButton } from "../../components/ui";
import { errorMessage } from "../../lib/errors";
import { usePaged } from "../../lib/usePaged";
import { statusLabel } from "../../lib/workflow";
import api from "../../services/api";

type Contact = { id: string; name: string; designation: string; email: string; phone: string; is_primary: boolean };
type Client = {
  id: string;
  client_code: string;
  company_name: string;
  industry: string;
  website: string;
  status: string;
  sales_owner: string;
  sales_owner_name?: string;
  default_fee_type?: string;
  default_fee_value?: string | null;
  default_guarantee_period_days?: number | null;
  contacts: Contact[];
};
type Staff = { id: string; username: string; first_name: string; last_name: string; can_own_client: boolean };
type Activity = { id: string; activity_type: string; subject: string; notes: string; user_name?: string; created_at: string };

export default function Clients() {
  const { can } = useAuth();
  const showFees = canSeeCommercialTerms(can);
  const list = usePaged<Client>("/clients/");
  const [owners, setOwners] = useState<Staff[]>([]);
  const [selected, setSelected] = useState<Client | null>(null);
  const [activities, setActivities] = useState<Activity[]>([]);
  const [error, setError] = useState("");
  const [form, setForm] = useState({ company_name: "", industry: "", sales_owner: "", fee_type: "", fee_value: "", guarantee: "" });
  const [contact, setContact] = useState({ name: "", designation: "", email: "", phone: "" });
  const [activity, setActivity] = useState({ activity_type: "NOTE", subject: "", notes: "" });

  useEffect(() => {
    if (!can("accounts.view_user")) return;
    api.get("/users/").then((response) => {
      const rows = (response.data.results ?? response.data) as Staff[];
      setOwners(rows.filter((row) => row.can_own_client));
    }).catch(() => setOwners([]));
  }, [can]);

  async function openClient(id: string) {
    setError("");
    try {
      const [clientResponse, activityResponse] = await Promise.all([
        api.get<Client>(`/clients/${id}/`),
        api.get("/client-activities/", { params: { client: id } }),
      ]);
      setSelected(clientResponse.data);
      setActivities(activityResponse.data.results ?? activityResponse.data);
    } catch (reason) {
      setError(errorMessage(reason, "This client could not be opened."));
    }
  }

  async function create(event: FormEvent) {
    event.preventDefault();
    setError("");
    const payload: Record<string, string | number> = { company_name: form.company_name, industry: form.industry, status: "LEAD" };
    if (can("clients.assign_client_owner")) {
      if (!form.sales_owner) {
        setError("Choose an active user who is allowed to own clients.");
        return;
      }
      payload.sales_owner = form.sales_owner;
    }
    if (showFees && form.fee_type) payload.default_fee_type = form.fee_type;
    if (showFees && form.fee_value) payload.default_fee_value = form.fee_value;
    if (showFees && form.guarantee) payload.default_guarantee_period_days = Number(form.guarantee);
    try {
      await api.post("/clients/", payload);
      setForm({ company_name: "", industry: "", sales_owner: "", fee_type: "", fee_value: "", guarantee: "" });
      list.reload();
    } catch (reason) {
      setError(errorMessage(reason, "The client could not be created."));
    }
  }

  async function addContact(event: FormEvent) {
    event.preventDefault();
    if (!selected) return;
    setError("");
    try {
      await api.post("/client-contacts/", { client: selected.id, ...contact, is_primary: false });
      setContact({ name: "", designation: "", email: "", phone: "" });
      await openClient(selected.id);
      list.reload();
    } catch (reason) {
      setError(errorMessage(reason, "The contact could not be saved."));
    }
  }

  async function addActivity(event: FormEvent) {
    event.preventDefault();
    if (!selected) return;
    setError("");
    try {
      await api.post("/client-activities/", { client: selected.id, ...activity });
      setActivity({ activity_type: "NOTE", subject: "", notes: "" });
      await openClient(selected.id);
    } catch (reason) {
      setError(errorMessage(reason, "The activity could not be saved."));
    }
  }

  return (
    <>
      <PageHeader eyebrow="CRM" title="Clients" description="Accounts, contacts, activities, and commercial defaults when your account can set them." />
      {error && <Alert>{error}</Alert>}
      {list.error && <Alert>{list.error}</Alert>}
      {can("clients.add_client") && (
        <Panel title="Add client">
          <form className="grid gap-3 md:grid-cols-3" onSubmit={create}>
            <Field label="Company name"><TextInput required value={form.company_name} onChange={(event) => setForm({ ...form, company_name: event.target.value })} /></Field>
            <Field label="Industry"><TextInput value={form.industry} onChange={(event) => setForm({ ...form, industry: event.target.value })} /></Field>
            {can("clients.assign_client_owner") && (
              <Field label="Sales owner">
                <Select required value={form.sales_owner} onChange={(event) => setForm({ ...form, sales_owner: event.target.value })}>
                  <option value="">Choose sales owner</option>
                  {owners.map((owner) => (
                    <option key={owner.id} value={owner.id}>{owner.first_name || owner.username} {owner.last_name}</option>
                  ))}
                </Select>
              </Field>
            )}
            {showFees && (
              <>
                <Field label="Default fee type">
                  <Select value={form.fee_type} onChange={(event) => setForm({ ...form, fee_type: event.target.value })}>
                    <option value="">No default</option>
                    <option value="PERCENTAGE">Percentage</option>
                    <option value="FIXED">Fixed amount</option>
                  </Select>
                </Field>
                <Field label="Default fee value"><TextInput value={form.fee_value} onChange={(event) => setForm({ ...form, fee_value: event.target.value })} /></Field>
                <Field label="Default guarantee days"><TextInput type="number" min={1} value={form.guarantee} onChange={(event) => setForm({ ...form, guarantee: event.target.value })} /></Field>
              </>
            )}
            <div className="flex items-end"><button className={primaryButton}>Add client</button></div>
          </form>
        </Panel>
      )}
      <div className="mt-4 overflow-x-auto rounded-xl border border-line bg-white">
        <table className="w-full text-left text-sm">
          <thead className="bg-canvas text-xs uppercase tracking-wide text-muted">
            <tr>
              <th className="px-3 py-2">Client</th>
              <th className="px-3 py-2">Code</th>
              <th className="px-3 py-2">Industry</th>
              <th className="px-3 py-2">Owner</th>
              <th className="px-3 py-2">Status</th>
            </tr>
          </thead>
          <tbody>
            {list.rows.map((client) => (
              <tr key={client.id} className="cursor-pointer border-t border-line hover:bg-canvas" onClick={() => openClient(client.id)}>
                <td className="px-3 py-2 font-semibold">{client.company_name}</td>
                <td className="px-3 py-2">{client.client_code}</td>
                <td className="px-3 py-2">{client.industry || "—"}</td>
                <td className="px-3 py-2">{client.sales_owner_name || "—"}</td>
                <td className="px-3 py-2"><Tag>{statusLabel(client.status)}</Tag></td>
              </tr>
            ))}
          </tbody>
        </table>
        {!list.rows.length && !list.loading && <Empty>No clients yet.</Empty>}
      </div>
      <Pager page={list.page} count={list.count} onPage={list.setPage} />
      {selected && (
        <div className="mt-4 grid gap-4 lg:grid-cols-2">
          <Panel title={`${selected.company_name} contacts`}>
            <ul className="mb-3 grid gap-2 text-sm">
              {selected.contacts?.map((item) => (
                <li key={item.id}>
                  <b>{item.name}</b> {item.designation && <span className="text-muted">· {item.designation}</span>}
                  <div className="text-muted">{item.email || "No email"} · {item.phone || "No phone"}</div>
                </li>
              ))}
              {!selected.contacts?.length && <Empty>No contacts yet.</Empty>}
            </ul>
            {showFees && (selected.default_fee_type || selected.default_fee_value) && (
              <p className="mb-3 text-sm text-muted">
                Commercial default: {statusLabel(selected.default_fee_type)} {selected.default_fee_value ?? ""}
                {selected.default_guarantee_period_days ? ` · guarantee ${selected.default_guarantee_period_days} days` : ""}
              </p>
            )}
            {can("clients.add_clientcontact") && (
              <form className="grid gap-2" onSubmit={addContact}>
                <TextInput required placeholder="Contact name" value={contact.name} onChange={(event) => setContact({ ...contact, name: event.target.value })} />
                <TextInput placeholder="Designation" value={contact.designation} onChange={(event) => setContact({ ...contact, designation: event.target.value })} />
                <TextInput type="email" placeholder="Email" value={contact.email} onChange={(event) => setContact({ ...contact, email: event.target.value })} />
                <TextInput placeholder="Phone" value={contact.phone} onChange={(event) => setContact({ ...contact, phone: event.target.value })} />
                <button className={primaryButton}>Add contact</button>
              </form>
            )}
          </Panel>
          <Panel title="Activities">
            <ul className="mb-3 grid gap-2 text-sm">
              {activities.map((item) => (
                <li key={item.id}>
                  <b>{statusLabel(item.activity_type)}</b> {item.subject}
                  <div className="text-muted">{item.user_name} · {item.notes}</div>
                </li>
              ))}
              {!activities.length && <Empty>No activities yet.</Empty>}
            </ul>
            {can("clients.add_clientactivity") && (
              <form className="grid gap-2" onSubmit={addActivity}>
                <Select value={activity.activity_type} onChange={(event) => setActivity({ ...activity, activity_type: event.target.value })}>
                  <option value="NOTE">Note</option>
                  <option value="CALL">Call</option>
                  <option value="EMAIL">Email</option>
                  <option value="MEETING">Meeting</option>
                  <option value="FOLLOW_UP">Follow-up</option>
                </Select>
                <TextInput placeholder="Subject" value={activity.subject} onChange={(event) => setActivity({ ...activity, subject: event.target.value })} />
                <TextArea placeholder="Notes" value={activity.notes} onChange={(event) => setActivity({ ...activity, notes: event.target.value })} />
                <button className={primaryButton}>Add activity</button>
              </form>
            )}
          </Panel>
        </div>
      )}
    </>
  );
}
