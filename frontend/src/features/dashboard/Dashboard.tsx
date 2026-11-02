import { useEffect, useState } from "react";
import { useAuth } from "../../auth/session";
import { Alert, PageHeader, Panel } from "../../components/ui";
import { errorMessage } from "../../lib/errors";
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

export default function Dashboard() {
  const { can } = useAuth();
  const [stats, setStats] = useState<Overview | null>(null);
  const [error, setError] = useState("");
  const [parseFailures, setParseFailures] = useState(0);
  const showOverview = can("reports.view_overview_report");
  const showFailures = can("audit.view_auditlog");

  useEffect(() => {
    if (!showOverview) return;
    api
      .get<Overview>("/reports/overview/")
      .then((response) => setStats(response.data))
      .catch((reason) => setError(errorMessage(reason, "The overview report is not available.")));
  }, [showOverview]);

  useEffect(() => {
    if (!showFailures) return;
    api
      .get<{ count?: number }>("/audit-logs/", { params: { action: "resume_parse_failed" } })
      .then((response) => setParseFailures(response.data.count ?? 0))
      .catch(() => setParseFailures(0));
  }, [showFailures]);

  const cards: { label: string; value: number | undefined }[] = [
    { label: "Active clients", value: stats?.clients },
    { label: "Open JDs", value: stats?.open_jobs },
  ];
  if (can("candidates.view_candidate")) cards.push({ label: "Candidates", value: stats?.candidates });
  cards.push({ label: "Applications", value: stats?.applications });
  if (can("placements.view_placement")) cards.push({ label: "Joined placements", value: stats?.joined_placements });

  return (
    <>
      <PageHeader
        eyebrow="OVERVIEW"
        title="Good work starts with visibility."
        description="Track clients, requirements and recruitment progress from one place."
      />
      {error && <Alert>{error}</Alert>}
      {showFailures && parseFailures > 0 && (
        <Alert>{parseFailures} resume parse failure{parseFailures === 1 ? "" : "s"} recorded. Open the candidate to see parsing status.</Alert>
      )}
      {!showOverview && <Alert tone="info">Your account does not include the overview report.</Alert>}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {cards.map((card) => (
          <div key={card.label} className="rounded-xl border border-line bg-white p-4 shadow-sm">
            <div className="text-sm text-muted">{card.label}</div>
            <div className="mt-2 font-display text-3xl font-extrabold">{stats ? card.value : "—"}</div>
          </div>
        ))}
      </div>
      {can("reports.view_financial_report") && stats && (
        <div className="mt-4 max-w-xl">
          <Panel title="Financial snapshot">
            <div className="flex justify-between border-t border-line py-2 text-sm">
              <span>Invoiced revenue</span>
              <b>{inr(stats.invoiced_revenue)}</b>
            </div>
            <div className="flex justify-between border-t border-line py-2 text-sm">
              <span>Payments received</span>
              <b>{inr(stats.payments_received)}</b>
            </div>
          </Panel>
        </div>
      )}
    </>
  );
}
