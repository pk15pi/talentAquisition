import { useEffect, useState, type FormEvent } from "react";
import { useAuth } from "../../auth/session";
import { Alert, Empty, Field, PageHeader, Pager, Panel, Select, TextInput, primaryButton } from "../../components/ui";
import { errorMessage } from "../../lib/errors";
import { fetchAll } from "../../lib/paging";
import { usePaged } from "../../lib/usePaged";
import { inr, statusLabel } from "../../lib/workflow";
import api from "../../services/api";

type Placement = {
  id: string;
  application: string;
  application_code?: string;
  candidate_name?: string;
  job_title?: string;
  joining_date: string | null;
  status: string;
  offered_ctc?: string;
  agreed_fee_type?: string;
  agreed_fee_value?: string;
  expected_revenue?: string;
  guarantee_period_days?: number;
};
type ApplicationOption = { id: string; candidate_name: string; job_title: string; application_code: string; status: string };

const STATUSES = ["OFFERED", "JOINED", "CANCELLED", "GUARANTEE", "COMPLETED"];

export default function Placements() {
  const { can } = useAuth();
  const list = usePaged<Placement>("/placements/");
  const [applications, setApplications] = useState<ApplicationOption[]>([]);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [form, setForm] = useState({ application: "", offered_ctc: "", joining_date: "", fee_type: "", fee_value: "", expected_revenue: "" });
  const showMoney = can("placements.view_placement_financials");
  const canCreate = can("placements.add_placement") && can("placements.change_placement_financials");
  const canEdit = can("placements.change_placement");
  const canEditMoney = can("placements.change_placement_financials");

  useEffect(() => {
    if (!canCreate || !can("applications.view_application")) return;
    fetchAll<ApplicationOption>("/applications/").then((result) => setApplications(result.rows)).catch(() => setApplications([]));
  }, [canCreate, can]);

  async function create(event: FormEvent) {
    event.preventDefault();
    setError("");
    setNotice("");
    const payload: Record<string, string> = { application: form.application, offered_ctc: form.offered_ctc };
    if (form.joining_date) payload.joining_date = form.joining_date;
    if (form.fee_type) payload.agreed_fee_type = form.fee_type;
    if (form.fee_value) payload.agreed_fee_value = form.fee_value;
    if (form.expected_revenue) payload.expected_revenue = form.expected_revenue;
    try {
      await api.post("/placements/", payload);
      setForm({ application: "", offered_ctc: "", joining_date: "", fee_type: "", fee_value: "", expected_revenue: "" });
      setNotice("Placement saved. Blank fee fields were copied from the job or client when those terms exist. Revenue is calculated unless you entered it.");
      list.reload();
    } catch (reason) {
      setError(errorMessage(reason, "The placement could not be saved."));
    }
  }

  async function update(row: Placement, patch: Record<string, string>) {
    setError("");
    try {
      await api.patch(`/placements/${row.id}/`, patch);
      list.reload();
    } catch (reason) {
      setError(errorMessage(reason, "The placement could not be updated."));
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="PLACEMENTS"
        title="Placements"
        description={showMoney ? "Commercial fields are visible for this account." : "Operational placement view. Commercial amounts are not shown for this account."}
      />
      {error && <Alert>{error}</Alert>}
      {notice && <Alert tone="success">{notice}</Alert>}
      {list.error && <Alert>{list.error}</Alert>}
      {canCreate && (
        <Panel title="Record placement">
          <form className="grid gap-3 md:grid-cols-3" onSubmit={create}>
            <Field label="Application">
              <Select required value={form.application} onChange={(event) => setForm({ ...form, application: event.target.value })}>
                <option value="">Select application</option>
                {applications.map((item) => (
                  <option key={item.id} value={item.id}>{item.candidate_name} · {item.job_title} · {item.application_code}</option>
                ))}
              </Select>
            </Field>
            <Field label="Offered CTC"><TextInput required value={form.offered_ctc} onChange={(event) => setForm({ ...form, offered_ctc: event.target.value })} /></Field>
            <Field label="Joining date"><TextInput type="date" value={form.joining_date} onChange={(event) => setForm({ ...form, joining_date: event.target.value })} /></Field>
            <Field label="Fee type override">
              <Select value={form.fee_type} onChange={(event) => setForm({ ...form, fee_type: event.target.value })}>
                <option value="">Copy from job or client</option>
                <option value="PERCENTAGE">Percentage</option>
                <option value="FIXED">Fixed amount</option>
              </Select>
            </Field>
            <Field label="Fee value override"><TextInput value={form.fee_value} onChange={(event) => setForm({ ...form, fee_value: event.target.value })} /></Field>
            <Field label="Expected revenue override"><TextInput value={form.expected_revenue} onChange={(event) => setForm({ ...form, expected_revenue: event.target.value })} /></Field>
            <button className={primaryButton}>Save placement</button>
          </form>
        </Panel>
      )}
      <div className="mt-4 overflow-x-auto rounded-xl border border-line bg-white">
        <table className="w-full text-left text-sm">
          <thead className="bg-canvas text-xs uppercase tracking-wide text-muted">
            <tr>
              <th className="px-3 py-2">Candidate</th>
              <th className="px-3 py-2">Job</th>
              <th className="px-3 py-2">Application</th>
              <th className="px-3 py-2">Joining</th>
              <th className="px-3 py-2">Status</th>
              {showMoney && <th className="px-3 py-2">Offered CTC</th>}
              {showMoney && <th className="px-3 py-2">Fee</th>}
              {showMoney && <th className="px-3 py-2">Expected revenue</th>}
              {canEdit && <th className="px-3 py-2">Update</th>}
            </tr>
          </thead>
          <tbody>
            {list.rows.map((row) => (
              <tr key={row.id} className="border-t border-line">
                <td className="px-3 py-2 font-semibold">{row.candidate_name || "—"}</td>
                <td className="px-3 py-2">{row.job_title || "—"}</td>
                <td className="px-3 py-2">{row.application_code || "—"}</td>
                <td className="px-3 py-2">{row.joining_date || "—"}</td>
                <td className="px-3 py-2">{statusLabel(row.status)}</td>
                {showMoney && <td className="px-3 py-2">{inr(row.offered_ctc)}</td>}
                {showMoney && <td className="px-3 py-2">{statusLabel(row.agreed_fee_type)} {row.agreed_fee_value ?? ""}</td>}
                {showMoney && <td className="px-3 py-2">{inr(row.expected_revenue)}</td>}
                {canEdit && (
                  <td className="px-3 py-2">
                    <Select aria-label={`Status for ${row.candidate_name || row.application_code}`} defaultValue={row.status} onChange={(event) => update(row, { status: event.target.value })}>
                      {STATUSES.map((status) => <option key={status} value={status}>{statusLabel(status)}</option>)}
                    </Select>
                    {canEditMoney && row.offered_ctc !== undefined && (
                      <p className="mt-1 text-xs text-muted">Guarantee {row.guarantee_period_days ?? "—"} days</p>
                    )}
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
        {!list.rows.length && !list.loading && <Empty>No placements.</Empty>}
      </div>
      <Pager page={list.page} count={list.count} onPage={list.setPage} />
    </>
  );
}
