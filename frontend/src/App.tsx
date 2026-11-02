import type { ReactNode } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { useAuth } from "./auth/session";
import { Forbidden } from "./components/ui";
import Applications from "./features/applications/Applications";
import Billing from "./features/billing/Billing";
import Candidates from "./features/candidates/Candidates";
import Clients from "./features/clients/Clients";
import Dashboard from "./features/dashboard/Dashboard";
import Duplicates from "./features/duplicates/Duplicates";
import Interviews from "./features/interviews/Interviews";
import Jobs from "./features/jobs/Jobs";
import Placements from "./features/placements/Placements";
import Reports from "./features/reports/Reports";
import Opportunities from "./features/sales/Opportunities";
import Settings from "./features/settings/Settings";
import Submissions from "./features/submissions/Submissions";
import Users from "./features/users/Users";
import Layout from "./layouts/Layout";
import Login from "./pages/Login";

function RequireAuth() {
  const location = useLocation();
  const { user, ready } = useAuth();
  const token = typeof localStorage !== "undefined" ? localStorage.getItem("access") : null;
  if (!ready || (token && !user)) {
    return <div className="grid min-h-screen place-items-center text-sm text-muted">Loading workspace…</div>;
  }
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  return <Layout />;
}

function Permit({ allow, children }: { allow: boolean; children: ReactNode }) {
  if (!allow) return <Forbidden />;
  return children;
}

export default function App() {
  const { can } = useAuth();
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route element={<RequireAuth />}>
        <Route index element={<Dashboard />} />
        <Route path="clients" element={<Permit allow={can("clients.view_client")}><Clients /></Permit>} />
        <Route path="opportunities" element={<Permit allow={can("sales.view_salesopportunity")}><Opportunities /></Permit>} />
        <Route path="jobs" element={<Permit allow={can("jobs.view_job")}><Jobs /></Permit>} />
        <Route path="candidates" element={<Permit allow={can("candidates.view_candidate")}><Candidates /></Permit>} />
        <Route path="duplicates" element={<Permit allow={can("candidates.review_duplicate")}><Duplicates /></Permit>} />
        <Route path="applications" element={<Permit allow={can("applications.view_application")}><Applications /></Permit>} />
        <Route path="interviews" element={<Permit allow={can("interviews.view_interview")}><Interviews /></Permit>} />
        <Route path="submissions" element={<Permit allow={can("recruitment.view_submission")}><Submissions /></Permit>} />
        <Route path="placements" element={<Permit allow={can("placements.view_placement")}><Placements /></Permit>} />
        <Route
          path="billing"
          element={
            <Permit allow={can("billing.view_invoice") || can("billing.view_payment") || can("billing.view_creditnote")}>
              <Billing />
            </Permit>
          }
        />
        <Route
          path="reports"
          element={
            <Permit
              allow={can("reports.view_overview_report") || can("reports.view_hr_report") || can("reports.view_sales_report")}
            >
              <Reports />
            </Permit>
          }
        />
        <Route path="users" element={<Permit allow={can("accounts.view_user")}><Users /></Permit>} />
        <Route
          path="settings"
          element={<Permit allow={can("organizations.view_systemconfiguration")}><Settings /></Permit>}
        />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
