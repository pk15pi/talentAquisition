export type SessionUser = {
  id: string;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  employee_code: string | null;
  role: string;
  phone: string;
  is_active: boolean;
  is_superuser: boolean;
  permissions: string[];
  can_own_client: boolean;
  can_be_assigned_recruiter: boolean;
};

export type Can = (permission: string) => boolean;

export function displayName(person: { first_name?: string; last_name?: string; username?: string; user_name?: string }) {
  if (person.user_name) return person.user_name;
  const name = `${person.first_name || ""} ${person.last_name || ""}`.trim();
  return name || person.username || "Unassigned";
}

export const ROLE_LABELS: Record<string, string> = {
  ADMIN: "Administrator",
  MANAGEMENT: "Management",
  SALES: "Sales Executive",
  HR: "HR Executive",
  TEAM_LEAD: "Team Lead",
};

export function canSeeCommercialTerms(can: Can) {
  return (
    can("clients.change_client") ||
    can("placements.view_placement_financials") ||
    can("reports.view_financial_report") ||
    can("billing.view_invoice")
  );
}
