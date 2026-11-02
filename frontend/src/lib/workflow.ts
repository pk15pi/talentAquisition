export const APPLICATION_PIPELINE = [
  "IDENTIFIED",
  "CONTACTED",
  "INTERESTED",
  "SHORTLISTED",
  "SUBMITTED",
  "CLIENT_REVIEW",
  "INTERVIEW",
  "SELECTED",
  "OFFERED",
  "JOINED",
] as const;

const APPLICATION_EXITS = ["REJECTED", "WITHDRAWN"];

export function allowedApplicationStatuses(current: string) {
  if (current === "JOINED" || APPLICATION_EXITS.includes(current)) return [];
  const index = APPLICATION_PIPELINE.indexOf(current as (typeof APPLICATION_PIPELINE)[number]);
  if (index < 0) return [];
  const next = index + 1 < APPLICATION_PIPELINE.length ? [APPLICATION_PIPELINE[index + 1]] : [];
  return [...next, ...APPLICATION_EXITS];
}

export const SUBMISSION_TRANSITIONS: Record<string, string[]> = {
  PENDING: ["ACKNOWLEDGED", "REJECTED", "WITHDRAWN"],
  ACKNOWLEDGED: ["SHORTLISTED", "REJECTED", "WITHDRAWN"],
  SHORTLISTED: ["REJECTED", "WITHDRAWN"],
  REJECTED: [],
  WITHDRAWN: [],
};

export function allowedSubmissionStatuses(current: string) {
  return SUBMISSION_TRANSITIONS[current] ?? [];
}

export const STATUS_LABELS: Record<string, string> = {
  IDENTIFIED: "Identified",
  CONTACTED: "Contacted",
  INTERESTED: "Interested",
  SHORTLISTED: "Shortlisted",
  SUBMITTED: "Submitted",
  CLIENT_REVIEW: "Client review",
  INTERVIEW: "Interview",
  SELECTED: "Selected",
  OFFERED: "Offered",
  JOINED: "Joined",
  REJECTED: "Rejected",
  WITHDRAWN: "Withdrawn",
  PENDING: "Pending",
  ACKNOWLEDGED: "Acknowledged",
  DRAFT: "Draft",
  OPEN: "Open",
  ON_HOLD: "On hold",
  CLOSED: "Closed",
  CANCELLED: "Cancelled",
  LEAD: "Lead",
  ACTIVE: "Active",
  INACTIVE: "Inactive",
  BLACKLISTED: "Blacklisted",
  GUARANTEE: "Guarantee period",
  COMPLETED: "Completed",
  ISSUED: "Issued",
  PART_PAID: "Part paid",
  PAID: "Paid",
  OVERDUE: "Overdue",
  VOID: "Void",
  PASSED: "Passed",
  FAILED: "Failed",
  APPROVED: "Approved",
  PERCENTAGE: "Percentage",
  FIXED: "Fixed amount",
  LOW: "Low",
  MEDIUM: "Medium",
  HIGH: "High",
  URGENT: "Urgent",
  OFFICE: "Office",
  HYBRID: "Hybrid",
  REMOTE: "Remote",
  LINKEDIN: "LinkedIn",
  REFERRAL: "Referral",
  JOB_PORTAL: "Job portal",
  WEBSITE: "Website",
  INTERNAL: "Internal",
  OTHER: "Other",
  EMAIL: "Email",
  PHONE: "Phone",
  FILE_HASH: "File hash",
  CALL: "Call",
  MEETING: "Meeting",
  NOTE: "Note",
  FOLLOW_UP: "Follow-up",
};

export function statusLabel(value: string | null | undefined) {
  if (!value) return "—";
  return STATUS_LABELS[value] || value;
}

export function inr(value: string | number | null | undefined) {
  const amount = typeof value === "string" ? Number(value) : value;
  if (amount === null || amount === undefined || Number.isNaN(amount)) return "—";
  return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 2 }).format(amount);
}

export function normalizeSkillName(name: string) {
  return name.trim().toLowerCase().replace(/\s+/g, " ");
}
