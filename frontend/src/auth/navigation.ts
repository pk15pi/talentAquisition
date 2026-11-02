import type { Can } from "./types";

export type NavItem = {
  to: string;
  label: string;
  end?: boolean;
  allow: (can: Can) => boolean;
};

export const NAV: NavItem[] = [
  { to: "/", label: "Dashboard", end: true, allow: () => true },
  { to: "/clients", label: "Clients", allow: (can) => can("clients.view_client") },
  { to: "/opportunities", label: "Opportunities", allow: (can) => can("sales.view_salesopportunity") },
  { to: "/jobs", label: "Job descriptions", allow: (can) => can("jobs.view_job") },
  { to: "/candidates", label: "Candidates", allow: (can) => can("candidates.view_candidate") },
  { to: "/duplicates", label: "Duplicate review", allow: (can) => can("candidates.review_duplicate") },
  { to: "/applications", label: "Pipeline", allow: (can) => can("applications.view_application") },
  { to: "/interviews", label: "Interviews", allow: (can) => can("interviews.view_interview") },
  { to: "/submissions", label: "Submissions", allow: (can) => can("recruitment.view_submission") },
  { to: "/placements", label: "Placements", allow: (can) => can("placements.view_placement") },
  {
    to: "/billing",
    label: "Billing",
    allow: (can) => can("billing.view_invoice") || can("billing.view_payment") || can("billing.view_creditnote"),
  },
  {
    to: "/reports",
    label: "Reports",
    allow: (can) =>
      can("reports.view_overview_report") || can("reports.view_hr_report") || can("reports.view_sales_report"),
  },
  { to: "/users", label: "Users", allow: (can) => can("accounts.view_user") },
  { to: "/settings", label: "Settings", allow: (can) => can("organizations.view_systemconfiguration") },
];
