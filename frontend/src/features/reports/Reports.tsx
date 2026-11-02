import { useEffect, useState } from "react";
import { useAuth } from "../../auth/session";
import { Alert, Field, PageHeader, Panel, TextInput, primaryButton } from "../../components/ui";
import { errorMessage } from "../../lib/errors";
import { displayName } from "../../auth/types";
import { inr } from "../../lib/workflow";
import api from "../../services/api";

type Overview = {
  clients: number;
  open_jobs: number;
  candidates: number;
  applications: number;
  joined_placements: number;
  invoiced_revenue: number;
  payments_received: number;
};

type NamedCount = {
  applications?: number;
  candidates_sourced?: number;
  jds?: number;
  clients?: number;
  recruiter__first_name?: string;
  recruiter__last_name?: string;
  sourced_by__first_name?: string;
  sourced_by__last_name?: string;
  sales_owner__first_name?: string;
  sales_owner__last_name?: string;
};

function person(row: NamedCount, prefix: "recruiter" | "sourced_by" | "sales_owner") {
  return displayName({
    first_name: row[`${prefix}__first_name`],
    last_name: row[`${prefix}__last_name`],
  });
}

export default function Reports() {
  const { can } = useAuth();
  const [overview, setOverview] = useState<Overview | null>(null);
  const [hr, setHr] = useState<{ applications_by_recruiter: NamedCount[]; candidates_sourced_by: NamedCount[] } | null>(null);
  const [sales, setSales] = useState<{ jds_by_sales_owner: NamedCount[]; clients_by_sales_owner: NamedCount[] } | null>(null);
  const [errors, setErrors] = useState<string[]>([]);
  const [filters, setFilters] = useState({ date_from: "", date_to: "", status: "", client: "", job: "", recruiter: "", sales_executive: "", department: "", employee: "" });
  const [applied, setApplied] = useState(filters);

  useEffect(() => {
    const messages: string[] = [];
    const params = Object.fromEntries(Object.entries(applied).filter(([, value]) => value));
    const jobs: Promise<void>[] = [];
    if (can("reports.view_overview_report")) {
      jobs.push(
        api
          .get<Overview>("/reports/overview/", { params })
          .then((response) => {
            setOverview(response.data);
          })
          .catch((reason) => {
            messages.push(errorMessage(reason, "Overview report was refused."));
          }),
      );
    }
    if (can("reports.view_hr_report")) {
      jobs.push(
        api
          .get("/reports/hr/", { params })
          .then((response) => {
            setHr(response.data);
          })
          .catch((reason) => {
            messages.push(errorMessage(reason, "The recruitment report was refused."));
          }),
      );
    }
    if (can("reports.view_sales_report")) {
      jobs.push(
        api
          .get("/reports/sales/", { params })
          .then((response) => {
            setSales(response.data);
          })
          .catch((reason) => {
            messages.push(errorMessage(reason, "The sales report was refused."));
          }),
      );
    }
    Promise.all(jobs).then(() => setErrors(messages));
  }, [can, applied]);

  return (
    <>
      <PageHeader
        eyebrow="ANALYTICS"
        title="Performance reports"
        description="Client credit uses the owner at creation. JD credit uses the current sales owner because job owner changes are not historized. Recruitment counts use the recruiter stored on the application."
      />
      <Panel title="Filters">
        <form
          className="grid gap-3 md:grid-cols-3"
          onSubmit={(event) => {
            event.preventDefault();
            setApplied(filters);
          }}
        >
          <Field label="From"><TextInput type="date" value={filters.date_from} onChange={(event) => setFilters({ ...filters, date_from: event.target.value })} /></Field>
          <Field label="To"><TextInput type="date" value={filters.date_to} onChange={(event) => setFilters({ ...filters, date_to: event.target.value })} /></Field>
          <Field label="Status"><TextInput value={filters.status} onChange={(event) => setFilters({ ...filters, status: event.target.value })} placeholder="OPEN, IDENTIFIED, ACTIVE" /></Field>
          <Field label="Client id"><TextInput value={filters.client} onChange={(event) => setFilters({ ...filters, client: event.target.value })} /></Field>
          <Field label="Job id"><TextInput value={filters.job} onChange={(event) => setFilters({ ...filters, job: event.target.value })} /></Field>
          <Field label="Recruiter id"><TextInput value={filters.recruiter} onChange={(event) => setFilters({ ...filters, recruiter: event.target.value })} /></Field>
          <Field label="Sales executive id"><TextInput value={filters.sales_executive} onChange={(event) => setFilters({ ...filters, sales_executive: event.target.value })} /></Field>
          <Field label="Department id"><TextInput value={filters.department} onChange={(event) => setFilters({ ...filters, department: event.target.value })} /></Field>
          <Field label="Employee id"><TextInput value={filters.employee} onChange={(event) => setFilters({ ...filters, employee: event.target.value })} /></Field>
          <button className={primaryButton} type="submit">Apply filters</button>
        </form>
      </Panel>
      {errors.map((message) => (
        <Alert key={message}>{message}</Alert>
      ))}
      {overview && (
        <Panel title="Overview">
          <dl className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            <Stat label="Clients" value={overview.clients} />
            <Stat label="Open JDs" value={overview.open_jobs} />
            {can("candidates.view_candidate") && <Stat label="Candidates" value={overview.candidates} />}
            <Stat label="Applications" value={overview.applications} />
            {can("placements.view_placement") && <Stat label="Joined placements" value={overview.joined_placements} />}
            {can("reports.view_financial_report") && (
              <>
                <Stat label="Invoiced revenue" value={inr(overview.invoiced_revenue)} />
                <Stat label="Payments received" value={inr(overview.payments_received)} />
              </>
            )}
          </dl>
        </Panel>
      )}
      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        {hr && (
          <Panel title="Recruitment activity">
            <CountTable
              rows={hr.applications_by_recruiter.map((row) => ({ name: person(row, "recruiter"), count: row.applications ?? 0 }))}
              countLabel="Applications"
            />
            <h3 className="mb-2 mt-4 text-sm font-bold">Candidates sourced</h3>
            <CountTable
              rows={hr.candidates_sourced_by.map((row) => ({ name: person(row, "sourced_by"), count: row.candidates_sourced ?? 0 }))}
              countLabel="Candidates"
            />
          </Panel>
        )}
        {sales && (
          <Panel title="Sales activity">
            <CountTable
              rows={sales.jds_by_sales_owner.map((row) => ({ name: person(row, "sales_owner"), count: row.jds ?? 0 }))}
              countLabel="JDs"
            />
            <h3 className="mb-2 mt-4 text-sm font-bold">Clients</h3>
            <CountTable
              rows={sales.clients_by_sales_owner.map((row) => ({ name: person(row, "sales_owner"), count: row.clients ?? 0 }))}
              countLabel="Clients"
            />
          </Panel>
        )}
      </div>
    </>
  );
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-lg bg-canvas px-3 py-2">
      <dt className="text-xs text-muted">{label}</dt>
      <dd className="font-display text-xl font-bold">{value}</dd>
    </div>
  );
}

function CountTable({ rows, countLabel }: { rows: { name: string; count: number }[]; countLabel: string }) {
  if (!rows.length) return <p className="text-sm text-muted">No rows.</p>;
  return (
    <table className="w-full text-left text-sm">
      <thead>
        <tr className="text-xs uppercase tracking-wide text-muted">
          <th className="py-2">Name</th>
          <th className="py-2">{countLabel}</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr key={`${row.name}-${row.count}`} className="border-t border-line">
            <td className="py-2">{row.name}</td>
            <td className="py-2">{row.count}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
