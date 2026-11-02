# SynfoTalent delivery report

Date: 2026-11-02. Branch: `cursor/completion-gaps-b414`. Base: `master` at `635cc4d` (Phase 5 merged). This report follows the gap register in `FINAL_AUDIT_BASELINE.md`, which was committed before the code changes.

The production-prep agent (`bc-64130237-fd50-5ec8-a1d1-a677d6d1757a`) was already implementing Gunicorn, Nginx, non-root images, and secret/CORS/throttle hardening. This branch does not replace that work. It adds a Celery beat service to the development Compose file so retention has a process to run.

## Completion

The baseline register has 38 rows whose status cell is exactly Complete, Partial, Missing, or Defective: 10 complete, 13 partial, 14 missing, 1 defective.

| After this pass | Count | Rows |
| --- | --- | --- |
| Complete, unchanged | 10 | The baseline complete rows, including HR placement view-only, matching weights, group restore, superuser bypass, API billing, placement terms, the transition graph, and Tailwind |
| Missing or defective, now complete | 9 | Admin invoice integrity, consent withdrawal, duplicate merge, retention job, report filters, the opportunities screen, the merge control, the withdrawal control, and the report filter screen |
| Partial | 14 | The original 13 partial rows, plus background-failure notice (an audit row and a dashboard count, no mail recipient). Report filters and the opportunities screen moved out of partial/missing; JD credit is still the current owner inside the partial report row |
| Still missing | 5 | Login throttle, cookie session, and S3 (production-prep scope), JD sales-owner history, department UI, password reset, malware scanning |

19 of 38 rows are complete. That is 50%. Partial rows are not counted as complete. Production readiness is not that percentage. See the last section.

## What changed

| Area | Behavior |
| --- | --- |
| Duplicate merge | `POST /api/v1/duplicate-reviews/{id}/merge/` with `surviving_candidate_id`. Approve still only records a decision. The other row stays, inactive, with `merged_into`. Consent rows and `sourced_by` are not copied. Applications move, so interviews, submissions, and placements move with them. Two active applications for the same job abort the whole merge. Skills the survivor already has stay on the alias and are listed as conflicts. |
| Consent withdrawal | `POST /api/v1/candidates/{id}/withdraw-consent/` and a Django admin action. Requires a real `consent_recorded_at`. Does not delete the profile. |
| Retention | `apps.organizations.tasks.enforce_retention`, daily beat schedule, `python manage.py enforce_retention`. Null days skip that category. Submissions protect resumes. Interviews, submissions, and placements protect applications. Applications protect candidates. Aliases are kept. |
| Billing admin | Header subtotal, tax, and total are read-only and recomputed from lines. Payments and credit notes over outstanding are rejected while the invoice row is locked. |
| Reports | Filters listed below. Client counts use the first ownership-history owner. Invoices, only when `reports.view_financial_report` is held, use the owner at `invoice.created_at`. HR output has no fee or revenue keys. |
| Frontend | Opportunities route. Merge control separate from Approve. Withdraw consent. Report filter form. Dashboard count of `resume_parse_failed` for users who can view the audit log. |
| Audit | Consent recorded, consent withdrawn, candidates merged, resume link and download, invoice/line/payment/credit-note writes, retention summary, final parse failure. `GET /api/v1/audit-logs/` requires `audit.view_auditlog`. |

## Migration

`candidates.0004_candidate_alias_and_merge`.

Why it was required: the approved merge rule says the other profile remains an audited alias and field conflicts are recorded. `AuditLog` is itself subject to `audit_log_retention_days`, so the alias pointer and the conflict list cannot live only there. The migration adds nullable `merged_into` and `merged_at` on `Candidate`, and a `CandidateMerge` row. No earlier migration file was edited. `makemigrations --check --dry-run` reports no further drift.

## Security notes

- HR still has `placements.view_placement` only. The browser pass confirmed the placement page does not show offered CTC.
- Withdrawal does not invent a consent timestamp for `contract`, `legal_obligation`, or `legitimate_interest`.
- Merge is not available by name. There is no successful `POST /api/v1/candidates/merge/`.
- One person's consent is not written onto the other.
- Resume bytes still require `candidates.view_resume_content`, re-checked when the signed link is redeemed. Downloads are now audited.
- Who may merge was not specified (audit open question 9). The endpoint uses the permission that already decides duplicate reviews, which every default group has. An administrator can remove `candidates.review_duplicate` from a group. `bootstrap_groups` will not put it back unless `--reset` is passed.
- Superuser bypass is unchanged.
- Role groups are still not rewritten on login or save.
- This branch does not add throttles, cookie sessions, Gunicorn, or Nginx.

## Tests and commands

PostgreSQL 16.15 on localhost, database `synfotalent`, user `synfotalent`.

```bash
cd backend
DJANGO_DEBUG=1 DJANGO_SECRET_KEY=dev-only-baseline-not-for-prod \
POSTGRES_DB=synfotalent POSTGRES_USER=synfotalent \
POSTGRES_PASSWORD=synfotalent_dev_password POSTGRES_HOST=localhost \
.venv/bin/python manage.py test apps
```

Result: **98 tests, OK**. The same command before the code changes, recorded in the baseline, was 82 tests, OK.

```bash
DJANGO_DEBUG=0 DJANGO_SECRET_KEY=production-secret-not-dev-only-32chars-min \
POSTGRES_HOST=localhost .venv/bin/python manage.py check
```

Result: no issues.

```bash
.venv/bin/python manage.py makemigrations --check --dry-run
```

Result: no changes detected.

```bash
cd frontend
npm test
npm run build
```

Result: Vitest **13 passed**. `tsc -b && vite build` exit 0.

Browser, against `runserver` on port 8000 and Vite on port 5173, users `hrcomplete`, `salescomplete`, and `mgmtcomplete`:

```bash
CHROME_PATH=/usr/local/bin/google-chrome node frontend/scripts/verify-completion.mjs
```

Result: **completion browser verification ok**.

- HR dashboard has no Billing link, no Opportunities link, and no invoiced revenue. `/billing` and `/opportunities` show the permission message. The placement row for Browser Candidate does not show offered CTC.
- HR cannot save a candidate until the consent box is checked. Withdraw consent then shows "Consent withdrawn. The profile was not deleted."
- Sales opens Opportunities, saves "Browser Deal" on Browser Client, is refused `/billing`, and the Browser Role page has no Find candidates button.
- Management sees invoiced revenue and billing, and the placement cell shows ₹1,23,456.78.

Screenshots: `/opt/cursor/artifacts/screenshots/completion-hr-dashboard.png`, `completion-hr-placement.png`, `completion-hr-consent-withdrawn.png`, `completion-sales-opportunity.png`, `completion-sales-match-hidden.png`, `completion-management-billing.png`, `completion-management-placement.png`, `completion-management-reports.png`.

Not run in this pass: `docker compose up`, Celery beat as a live process, and Gunicorn. Retention was executed inside the Django test process. The beat schedule is in `backend/config/celery.py`.

## Production readiness

Not ready for real candidate files or live invoices.

Ready enough for a staff pilot only after the production-prep change supplies a non-root Gunicorn/Nginx path, a real secret, and HTTPS. Even then:

- Job owner history is current-state only, so a JD transfer rewrites sales credit for that JD.
- Merge authority is as wide as duplicate review.
- Retention deletes unprotected old rows when an administrator sets a number. Protected pipeline rows stay. That is the schema, not a legal retention policy. No privacy law was specified.
- Resume parsing failures are an audit row, not an email.
- Tokens remain in `localStorage`.
