import { useEffect, useState, type FormEvent } from "react";
import { useAuth } from "../../auth/session";
import { Alert, Empty, Field, PageHeader, Pager, Panel, Select, TextArea, TextInput, primaryButton } from "../../components/ui";
import { errorMessage } from "../../lib/errors";
import { fetchAll } from "../../lib/paging";
import { usePaged } from "../../lib/usePaged";
import { inr, statusLabel } from "../../lib/workflow";
import api from "../../services/api";

type Invoice = {
  id: string;
  invoice_number: string;
  client_name?: string;
  invoice_date: string;
  due_date: string;
  status: string;
  subtotal: string;
  tax_amount: string;
  total: string;
  paid_amount: string;
  credited_amount: string;
  outstanding_amount: string;
};
type Payment = { id: string; invoice: string; invoice_number?: string; amount: string; payment_date: string; reference: string; mode: string };
type CreditNote = { id: string; invoice: string; invoice_number?: string; credit_note_number: string; amount: string; reason: string; issue_date: string };
type Client = { id: string; company_name: string };
type Placement = { id: string; candidate_name?: string; application_code?: string };

const INVOICE_STATUSES = ["DRAFT", "ISSUED", "OVERDUE", "VOID"];

export default function Billing() {
  const { can } = useAuth();
  const invoices = usePaged<Invoice>("/invoices/", {}, can("billing.view_invoice"));
  const payments = usePaged<Payment>("/payments/", {}, can("billing.view_payment"));
  const credits = usePaged<CreditNote>("/credit-notes/", {}, can("billing.view_creditnote"));
  const [clients, setClients] = useState<Client[]>([]);
  const [placements, setPlacements] = useState<Placement[]>([]);
  const [invoiceChoices, setInvoiceChoices] = useState<Invoice[]>([]);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [invoiceForm, setInvoiceForm] = useState({ client: "", invoice_date: "", due_date: "", status: "DRAFT", notes: "" });
  const [lineForm, setLineForm] = useState({ invoice: "", description: "", quantity: "1", unit_amount: "", tax_rate: "0", placement: "" });
  const [paymentForm, setPaymentForm] = useState({ invoice: "", amount: "", payment_date: "", reference: "", mode: "" });
  const [creditForm, setCreditForm] = useState({ invoice: "", amount: "", reason: "", issue_date: "" });

  useEffect(() => {
    if (can("clients.view_client") && can("billing.add_invoice")) {
      fetchAll<Client>("/clients/").then((result) => setClients(result.rows)).catch(() => setClients([]));
    }
    if (can("placements.view_placement") && can("billing.add_invoiceline")) {
      fetchAll<Placement>("/placements/").then((result) => setPlacements(result.rows)).catch(() => setPlacements([]));
    }
    if (can("billing.view_invoice")) {
      fetchAll<Invoice>("/invoices/").then((result) => setInvoiceChoices(result.rows)).catch(() => setInvoiceChoices([]));
    }
  }, [can, invoices.rows.length, payments.rows.length, credits.rows.length]);

  async function createInvoice(event: FormEvent) {
    event.preventDefault();
    setError("");
    try {
      await api.post("/invoices/", invoiceForm);
      setInvoiceForm({ client: "", invoice_date: "", due_date: "", status: "DRAFT", notes: "" });
      setNotice("Invoice created. Totals stay zero until a line is added.");
      invoices.reload();
    } catch (reason) {
      setError(errorMessage(reason, "The invoice could not be created."));
    }
  }

  async function addLine(event: FormEvent) {
    event.preventDefault();
    setError("");
    const payload: Record<string, string | number> = {
      invoice: lineForm.invoice,
      description: lineForm.description,
      quantity: Number(lineForm.quantity),
      unit_amount: lineForm.unit_amount,
      tax_rate: lineForm.tax_rate || "0",
    };
    if (lineForm.placement) payload.placement = lineForm.placement;
    try {
      await api.post("/invoice-lines/", payload);
      setLineForm({ invoice: "", description: "", quantity: "1", unit_amount: "", tax_rate: "0", placement: "" });
      setNotice("Line saved. Invoice subtotal, tax, and total were recalculated.");
      invoices.reload();
    } catch (reason) {
      setError(errorMessage(reason, "The invoice line could not be saved."));
    }
  }

  async function addPayment(event: FormEvent) {
    event.preventDefault();
    setError("");
    try {
      await api.post("/payments/", paymentForm);
      setPaymentForm({ invoice: "", amount: "", payment_date: "", reference: "", mode: "" });
      setNotice("Payment recorded.");
      payments.reload();
      invoices.reload();
    } catch (reason) {
      setError(errorMessage(reason, "The payment could not be recorded."));
    }
  }

  async function addCredit(event: FormEvent) {
    event.preventDefault();
    setError("");
    try {
      await api.post("/credit-notes/", creditForm);
      setCreditForm({ invoice: "", amount: "", reason: "", issue_date: "" });
      setNotice("Credit note issued.");
      credits.reload();
      invoices.reload();
    } catch (reason) {
      setError(errorMessage(reason, "The credit note could not be issued."));
    }
  }

  return (
    <>
      <PageHeader eyebrow="FINANCE" title="Billing" description="Header totals are calculated from lines. Paid and part-paid are derived from payments and credit notes." />
      {error && <Alert>{error}</Alert>}
      {notice && <Alert tone="success">{notice}</Alert>}
      {invoices.error && <Alert>{invoices.error}</Alert>}
      {payments.error && <Alert>{payments.error}</Alert>}
      {credits.error && <Alert>{credits.error}</Alert>}
      {can("billing.add_invoice") && (
        <Panel title="New invoice">
          <form className="grid gap-3 md:grid-cols-3" onSubmit={createInvoice}>
            <Field label="Client">
              <Select required value={invoiceForm.client} onChange={(event) => setInvoiceForm({ ...invoiceForm, client: event.target.value })}>
                <option value="">Select client</option>
                {clients.map((client) => <option key={client.id} value={client.id}>{client.company_name}</option>)}
              </Select>
            </Field>
            <Field label="Invoice date"><TextInput required type="date" value={invoiceForm.invoice_date} onChange={(event) => setInvoiceForm({ ...invoiceForm, invoice_date: event.target.value })} /></Field>
            <Field label="Due date"><TextInput required type="date" value={invoiceForm.due_date} onChange={(event) => setInvoiceForm({ ...invoiceForm, due_date: event.target.value })} /></Field>
            <Field label="Status">
              <Select value={invoiceForm.status} onChange={(event) => setInvoiceForm({ ...invoiceForm, status: event.target.value })}>
                {INVOICE_STATUSES.map((status) => <option key={status} value={status}>{statusLabel(status)}</option>)}
              </Select>
            </Field>
            <Field label="Notes"><TextArea value={invoiceForm.notes} onChange={(event) => setInvoiceForm({ ...invoiceForm, notes: event.target.value })} /></Field>
            <div className="flex items-end"><button className={primaryButton}>Create invoice</button></div>
          </form>
        </Panel>
      )}
      {can("billing.view_invoice") && (
        <div className="mt-4 overflow-x-auto rounded-xl border border-line bg-white">
          <table className="w-full text-left text-sm">
            <thead className="bg-canvas text-xs uppercase tracking-wide text-muted">
              <tr>
                <th className="px-3 py-2">Invoice</th>
                <th className="px-3 py-2">Client</th>
                <th className="px-3 py-2">Status</th>
                <th className="px-3 py-2">Subtotal</th>
                <th className="px-3 py-2">Tax</th>
                <th className="px-3 py-2">Total</th>
                <th className="px-3 py-2">Outstanding</th>
              </tr>
            </thead>
            <tbody>
              {invoices.rows.map((row) => (
                <tr key={row.id} className="border-t border-line">
                  <td className="px-3 py-2 font-semibold">{row.invoice_number}</td>
                  <td className="px-3 py-2">{row.client_name || "—"}</td>
                  <td className="px-3 py-2">{statusLabel(row.status)}</td>
                  <td className="px-3 py-2">{inr(row.subtotal)}</td>
                  <td className="px-3 py-2">{inr(row.tax_amount)}</td>
                  <td className="px-3 py-2">{inr(row.total)}</td>
                  <td className="px-3 py-2">{inr(row.outstanding_amount)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {!invoices.rows.length && !invoices.loading && <Empty>No invoices.</Empty>}
          <div className="px-3"><Pager page={invoices.page} count={invoices.count} onPage={invoices.setPage} /></div>
        </div>
      )}
      <div className="mt-4 grid gap-4 lg:grid-cols-3">
        {can("billing.add_invoiceline") && (
          <Panel title="Add line">
            <form className="grid gap-2" onSubmit={addLine}>
              <Select required value={lineForm.invoice} onChange={(event) => setLineForm({ ...lineForm, invoice: event.target.value })}>
                <option value="">Invoice</option>
                {invoiceChoices.map((row) => <option key={row.id} value={row.id}>{row.invoice_number}</option>)}
              </Select>
              <TextInput required placeholder="Description" value={lineForm.description} onChange={(event) => setLineForm({ ...lineForm, description: event.target.value })} />
              <TextInput required type="number" min={1} placeholder="Quantity" value={lineForm.quantity} onChange={(event) => setLineForm({ ...lineForm, quantity: event.target.value })} />
              <TextInput required placeholder="Unit amount" value={lineForm.unit_amount} onChange={(event) => setLineForm({ ...lineForm, unit_amount: event.target.value })} />
              <TextInput placeholder="Tax rate" value={lineForm.tax_rate} onChange={(event) => setLineForm({ ...lineForm, tax_rate: event.target.value })} />
              <Select value={lineForm.placement} onChange={(event) => setLineForm({ ...lineForm, placement: event.target.value })}>
                <option value="">No placement</option>
                {placements.map((row) => <option key={row.id} value={row.id}>{row.candidate_name || row.application_code || row.id}</option>)}
              </Select>
              <button className={primaryButton}>Save line</button>
            </form>
          </Panel>
        )}
        {can("billing.add_payment") && (
          <Panel title="Record payment">
            <form className="grid gap-2" onSubmit={addPayment}>
              <Select required value={paymentForm.invoice} onChange={(event) => setPaymentForm({ ...paymentForm, invoice: event.target.value })}>
                <option value="">Invoice</option>
                {invoiceChoices.map((row) => <option key={row.id} value={row.id}>{row.invoice_number}</option>)}
              </Select>
              <TextInput required placeholder="Amount" value={paymentForm.amount} onChange={(event) => setPaymentForm({ ...paymentForm, amount: event.target.value })} />
              <TextInput required type="date" value={paymentForm.payment_date} onChange={(event) => setPaymentForm({ ...paymentForm, payment_date: event.target.value })} />
              <TextInput placeholder="Reference" value={paymentForm.reference} onChange={(event) => setPaymentForm({ ...paymentForm, reference: event.target.value })} />
              <TextInput placeholder="Mode" value={paymentForm.mode} onChange={(event) => setPaymentForm({ ...paymentForm, mode: event.target.value })} />
              <button className={primaryButton}>Record payment</button>
            </form>
          </Panel>
        )}
        {can("billing.add_creditnote") && (
          <Panel title="Credit note">
            <form className="grid gap-2" onSubmit={addCredit}>
              <Select required value={creditForm.invoice} onChange={(event) => setCreditForm({ ...creditForm, invoice: event.target.value })}>
                <option value="">Invoice</option>
                {invoiceChoices.map((row) => <option key={row.id} value={row.id}>{row.invoice_number}</option>)}
              </Select>
              <TextInput required placeholder="Amount" value={creditForm.amount} onChange={(event) => setCreditForm({ ...creditForm, amount: event.target.value })} />
              <TextInput required type="date" value={creditForm.issue_date} onChange={(event) => setCreditForm({ ...creditForm, issue_date: event.target.value })} />
              <TextArea required placeholder="Reason" value={creditForm.reason} onChange={(event) => setCreditForm({ ...creditForm, reason: event.target.value })} />
              <button className={primaryButton}>Issue credit note</button>
            </form>
          </Panel>
        )}
      </div>
      {can("billing.view_payment") && (
        <div className="mt-4">
          <Panel title="Payments">
            <ul className="text-sm">
              {payments.rows.map((row) => (
                <li key={row.id}>{row.invoice_number || "Invoice"} · {inr(row.amount)} · {row.payment_date} · {row.mode || row.reference || "—"}</li>
              ))}
              {!payments.rows.length && !payments.loading && <Empty>No payments.</Empty>}
            </ul>
            <Pager page={payments.page} count={payments.count} onPage={payments.setPage} />
          </Panel>
        </div>
      )}
      {can("billing.view_creditnote") && (
        <div className="mt-4">
          <Panel title="Credit notes">
            <ul className="text-sm">
              {credits.rows.map((row) => (
                <li key={row.id}>{row.credit_note_number} · {row.invoice_number || "Invoice"} · {inr(row.amount)} · {row.reason}</li>
              ))}
              {!credits.rows.length && !credits.loading && <Empty>No credit notes.</Empty>}
            </ul>
            <Pager page={credits.page} count={credits.count} onPage={credits.setPage} />
          </Panel>
        </div>
      )}
    </>
  );
}
