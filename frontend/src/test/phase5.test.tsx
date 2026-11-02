import { cleanup, render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "../App";
import { AuthProvider } from "../auth/session";
import Applications from "../features/applications/Applications";
import Billing from "../features/billing/Billing";
import Candidates from "../features/candidates/Candidates";
import Clients from "../features/clients/Clients";
import Dashboard from "../features/dashboard/Dashboard";
import Duplicates from "../features/duplicates/Duplicates";
import Jobs from "../features/jobs/Jobs";
import Placements from "../features/placements/Placements";
import Reports from "../features/reports/Reports";
import Settings from "../features/settings/Settings";
import api, { login } from "../services/api";
import { HR_PERMISSIONS, MANAGEMENT_PERMISSIONS, SALES_PERMISSIONS, page, sessionUser } from "./fixtures";

vi.mock("../services/api", () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
  login: vi.fn(),
  logout: vi.fn(),
  apiOrigin: () => "http://localhost:8000",
}));

const http = api as unknown as {
  get: ReturnType<typeof vi.fn>;
  post: ReturnType<typeof vi.fn>;
  patch: ReturnType<typeof vi.fn>;
};

function renderApp(user = sessionUser("HR", HR_PERMISSIONS), path = "/") {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AuthProvider initialUser={user}>
        <App />
      </AuthProvider>
    </MemoryRouter>,
  );
}

function renderPage(node: ReactNode, user = sessionUser("HR", HR_PERMISSIONS)) {
  return render(<MemoryRouter><AuthProvider initialUser={user}>{node}</AuthProvider></MemoryRouter>);
}

afterEach(() => cleanup());

beforeEach(() => {
  http.get.mockReset();
  http.post.mockReset();
  http.patch.mockReset();
  http.get.mockImplementation(async (url: string) => {
    if (String(url).includes("/reports/overview")) {
      return { data: { clients: 2, open_jobs: 3, candidates: 4, applications: 5, joined_placements: 1, invoiced_revenue: 0, payments_received: 0 } };
    }
    if (String(url).includes("/reports/hr")) {
      return { data: { applications_by_recruiter: [{ recruiter__first_name: "Asha", recruiter__last_name: "Rao", applications: 2 }], candidates_sourced_by: [] } };
    }
    if (String(url).includes("/reports/sales")) {
      return { data: { jds_by_sales_owner: [], clients_by_sales_owner: [] } };
    }
    if (String(url).includes("/system-configuration")) {
      return { data: { candidate_retention_days: null, application_retention_days: null, resume_retention_days: null, audit_log_retention_days: null, privacy_notice_version: "notice-1", privacy_notice_text: "", updated_at: "2026-11-02T00:00:00Z" } };
    }
    return page([]);
  });
  http.post.mockResolvedValue({ data: { id: "new", full_name: "Saved" } });
  http.patch.mockResolvedValue({ data: {} });
});

describe("role navigation", () => {
  it("hides billing and financial navigation from HR", async () => {
    renderApp(sessionUser("HR", HR_PERMISSIONS));
    expect(await screen.findByRole("link", { name: "Candidates" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Placements" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Billing" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Opportunities" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Settings" })).not.toBeInTheDocument();
    expect(screen.queryByText("Invoiced revenue")).not.toBeInTheDocument();
  });

  it("shows billing to management and blocks HR from the billing route", async () => {
    renderApp(sessionUser("MANAGEMENT", MANAGEMENT_PERMISSIONS));
    expect(await screen.findByRole("link", { name: "Billing" })).toBeInTheDocument();
    cleanup();
    renderApp(sessionUser("HR", HR_PERMISSIONS), "/billing");
    expect(await screen.findByText(/do not have permission to view this page/i)).toBeInTheDocument();
  });

  it("hides match from sales", async () => {
    http.get.mockImplementation(async (url: string) => {
      if (String(url).includes("/jobs")) {
        return page([{ id: "job-1", job_code: "SW-JD-0001", title: "Engineer", client_name: "Acme", location: "Pune", status: "OPEN", priority: "MEDIUM", assignments: [] }]);
      }
      return page([]);
    });
    renderPage(<Jobs />, sessionUser("SALES", SALES_PERMISSIONS));
    expect(await screen.findByText("Engineer")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Find candidates" })).not.toBeInTheDocument();
  });
});

describe("login", () => {
  it("stores a session and leaves the login page", async () => {
    vi.mocked(login).mockImplementation(async () => {
      localStorage.setItem("access", "header.payload.sig");
      localStorage.setItem("refresh", "refresh.token.value");
      return { access: "header.payload.sig", refresh: "refresh.token.value" };
    });
    http.get.mockImplementation(async (url: string) => {
      if (String(url).includes("/users/me")) return { data: sessionUser("HR", HR_PERMISSIONS) };
      if (String(url).includes("/reports/overview")) {
        return { data: { clients: 1, open_jobs: 1, candidates: 1, applications: 1, joined_placements: 0, invoiced_revenue: 0, payments_received: 0 } };
      }
      return page([]);
    });
    render(
      <MemoryRouter initialEntries={["/login"]}>
        <AuthProvider>
          <App />
        </AuthProvider>
      </MemoryRouter>,
    );
    await userEvent.type(screen.getByLabelText("Username"), "hr");
    await userEvent.type(screen.getByLabelText("Password"), "longpassword1");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
    expect(login).toHaveBeenCalledWith("hr", "longpassword1");
    expect(await screen.findByRole("heading", { name: "Good work starts with visibility." })).toBeInTheDocument();
  });
});

describe("forms", () => {
  it("requires candidate consent before posting", async () => {
    renderPage(<Candidates />);
    await userEvent.type(screen.getByPlaceholderText("Full name"), "Browser Candidate");
    await userEvent.type(screen.getByPlaceholderText("Privacy notice version"), "notice-browser");
    await userEvent.click(screen.getByRole("button", { name: "Save candidate" }));
    expect(http.post).not.toHaveBeenCalled();
    await userEvent.click(screen.getByRole("checkbox", { name: /Candidate has given consent/ }));
    await userEvent.click(screen.getByRole("button", { name: "Save candidate" }));
    await waitFor(() => expect(http.post).toHaveBeenCalledWith("/candidates/", expect.objectContaining({
      full_name: "Browser Candidate",
      consent_acknowledged: true,
      privacy_notice_version: "notice-browser",
    })));
  });

  it("shows pipeline names and only the legal next statuses", async () => {
    http.get.mockImplementation(async (url: string) => {
      if (String(url).includes("/applications")) {
        return page([{
          id: "app-1",
          application_code: "SW-APP-0001",
          candidate: "cand-1",
          candidate_name: "Asha Rao",
          candidate_code: "SW-CAN-00001",
          job: "job-1",
          job_title: "Engineer",
          job_code: "SW-JD-0001",
          recruiter_name: "HR User",
          status: "IDENTIFIED",
          match_score: null,
        }]);
      }
      return page([]);
    });
    renderPage(<Applications />);
    expect(await screen.findByText("Asha Rao")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Contacted" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Rejected" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Withdrawn" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Joined" })).not.toBeInTheDocument();
    expect(screen.queryByRole("columnheader", { name: "Candidate ID" })).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Contacted" }));
    expect(http.post).toHaveBeenCalledWith("/applications/app-1/change-status/", { status: "CONTACTED" });
  });

  it("hides placement money from HR and shows it to management", async () => {
    const row = {
      id: "place-1",
      application: "app-1",
      application_code: "SW-APP-0001",
      candidate_name: "Asha Rao",
      job_title: "Engineer",
      joining_date: "2026-12-01",
      status: "OFFERED",
      offered_ctc: "880011.22",
      agreed_fee_type: "PERCENTAGE",
      agreed_fee_value: "10.00",
      expected_revenue: "770022.33",
      guarantee_period_days: 45,
    };
    http.get.mockResolvedValue(page([row]));
    renderPage(<Placements />, sessionUser("HR", HR_PERMISSIONS));
    expect(await screen.findByText("Asha Rao")).toBeInTheDocument();
    expect(screen.queryByText(/880011\.22/)).not.toBeInTheDocument();
    expect(screen.queryByText("Offered CTC")).not.toBeInTheDocument();
    renderPage(<Placements />, sessionUser("MANAGEMENT", MANAGEMENT_PERMISSIONS));
    expect(await screen.findByText(/₹8,80,011\.22|₹880,011\.22/)).toBeInTheDocument();
  });

  it("keeps a reported financial zero at zero and does not dump JSON", async () => {
    renderPage(<Reports />, sessionUser("MANAGEMENT", MANAGEMENT_PERMISSIONS));
    expect(await screen.findByText("Invoiced revenue")).toBeInTheDocument();
    expect(screen.getAllByText("₹0.00").length).toBeGreaterThan(0);
    expect(screen.queryByText(/applications_by_recruiter/)).not.toBeInTheDocument();
    cleanup();
    renderPage(<Reports />, sessionUser("HR", HR_PERMISSIONS));
    expect(await screen.findByText("Asha Rao")).toBeInTheDocument();
    expect(screen.queryByText("Invoiced revenue")).not.toBeInTheDocument();
  });

  it("posts a client without inventing a fee for HR", async () => {
    renderPage(<Clients />);
    expect(screen.queryByLabelText("Default fee type")).not.toBeInTheDocument();
  });

  it("approves a duplicate review without merging, and merge is a separate control", async () => {
    http.get.mockResolvedValue(page([{
      id: "review-1",
      candidate: { id: "a", candidate_code: "SW-CAN-00001", full_name: "Asha Rao" },
      matched_candidate: { id: "b", candidate_code: "SW-CAN-00002", full_name: "Asha R." },
      match_type: "EMAIL",
      status: "PENDING",
      notes: "",
      reviewed_at: null,
    }]));
    renderPage(<Duplicates />);
    expect(await screen.findByText(/does not merge or delete/i)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Approve" }));
    expect(http.post).toHaveBeenCalledWith("/duplicate-reviews/review-1/decide/", { approved: true, notes: "" });
    expect(http.post).not.toHaveBeenCalledWith("/duplicate-reviews/review-1/merge/", expect.anything());
    await userEvent.selectOptions(screen.getByLabelText(/Surviving profile for Asha Rao/i), "a");
    await userEvent.click(screen.getByRole("button", { name: "Merge into surviving profile" }));
    expect(http.post).toHaveBeenCalledWith("/duplicate-reviews/review-1/merge/", {
      surviving_candidate_id: "a",
      notes: "",
    });
  });

  it("shows invoice totals as calculated figures and has no header total input", async () => {
    http.get.mockImplementation(async (url: string) => {
      if (String(url).includes("/invoices")) {
        return page([{ id: "inv-1", invoice_number: "SW-INV-2026-0001", client_name: "Acme", invoice_date: "2026-11-01", due_date: "2026-11-15", status: "ISSUED", subtotal: "0.00", tax_amount: "0.00", total: "0.00", paid_amount: "0.00", credited_amount: "0.00", outstanding_amount: "0.00" }]);
      }
      return page([]);
    });
    renderPage(<Billing />, sessionUser("MANAGEMENT", MANAGEMENT_PERMISSIONS));
    expect(await screen.findByText("SW-INV-2026-0001")).toBeInTheDocument();
    expect(screen.queryByLabelText(/subtotal/i)).not.toBeInTheDocument();
    expect(screen.getAllByText("₹0.00").length).toBeGreaterThan(0);
  });

  it("saves blank retention as null", async () => {
    renderPage(<Settings />, sessionUser("MANAGEMENT", MANAGEMENT_PERMISSIONS));
    expect(await screen.findByLabelText("Candidate retention days")).toHaveValue(null);
    await userEvent.click(screen.getByRole("button", { name: "Save settings" }));
    expect(http.patch).toHaveBeenCalledWith("/system-configuration/", expect.objectContaining({
      candidate_retention_days: null,
      privacy_notice_version: "notice-1",
    }));
  });

  it("omits financial figures on the HR dashboard even if the payload is non-zero", async () => {
    http.get.mockResolvedValue({ data: { clients: 1, open_jobs: 1, candidates: 1, applications: 1, joined_placements: 1, invoiced_revenue: 999, payments_received: 999 } });
    renderPage(<Dashboard />);
    expect(await screen.findByText("Active clients")).toBeInTheDocument();
    expect(screen.queryByText("Invoiced revenue")).not.toBeInTheDocument();
    expect(screen.queryByText(/999/)).not.toBeInTheDocument();
  });
});
