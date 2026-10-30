# SynfoTalent development status

Phase 0 audit, 2026-10-30. This file describes the code that is already in the repository. It is not a roadmap by itself; the phased plan is in `AUDIT_REPORT.md`.

**Completion rule used here:** a feature is complete only when backend behavior, frontend integration, and tests have all been verified. Nothing in this repository meets that bar. "Present in code" is not "complete".

**Tests that actually ran**

| Command | Result |
| --- | --- |
| `python manage.py test -v 2` (backend, Django 5.2.18) | Exit 0. `Found 0 test(s)`. `Ran 0 tests`. Database setup skipped. |
| Frontend unit/integration tests | No test runner, no test files. Not run. |
| Browser pass of the React app | Not run. The API and Vite dev servers were not started. |

Extra probes (Django test client and ORM against a **disposable SQLite copy** under `/tmp`, not the repo, not PostgreSQL) are cited under the modules they touched. They are diagnostics, not the project's test suite, and they are not counted as passed tests.

---

## 1. Platform, configuration, and local runtime

- **Module name:** Platform / configuration / Docker
- **Current implementation status:** Partial. Compose file, Dockerfiles, settings, and `.env.example` exist. The stack does not start from a clean clone.
- **Completed features:** None.
- **Pending features:**
  - Committed migrations and a boot command that only runs `migrate`.
  - `.env` created from the example (the example is not named `.env`; Compose requires `.env`).
  - Gunicorn, Nginx, non-root containers, healthchecks, restart policy.
  - Frontend production image. The dev image runs `npm run dev`.
  - Lockfile for npm. `package-lock.json` is not in git.
  - Tailwind is in the target stack and is not installed. Styling is hand-written CSS.
  - API versioning is a URL prefix only (`/api/v1/`). No custom error handler, logging, or health endpoint.
- **Known bugs:**
  - `docker compose config` exits 1: `env file /workspace/.env not found`. README says an `.env` is included. It is gitignored and not in the tree.
  - Copying `.env.example` makes Compose resolve, and also sets `POSTGRES_HOST=db` and `DJANGO_DEBUG=1`. That host name works only inside Compose. On the host, Django defaults to `localhost:5432` when the variable is unset, and that connection was refused in this environment.
  - Celery broker default is `redis://redis:6379/0`, which does not resolve off the Compose network.
  - Backend container command runs `makemigrations` on every start and writes into the bind-mounted source tree.
  - `manage.py makemigrations --check --dry-run` with **no app labels** prints `No changes detected` and exits 0, because apps have no `migrations` package. With explicit labels, Django plans initial migrations for every model app. See the audit.
- **Tests executed:** `manage.py check` (exit 0). `manage.py check --deploy` (exit 0, 5 warnings). `manage.py test` (0 tests). `docker compose config` (exit 1 without `.env`; exit 0 after a temporary `.env` copied from the example and then deleted). Disposable SQLite `migrate` of generated migrations (exit 0, copy only).
- **Tests passed:** None in the project suite (0 collected).
- **Tests failed:** None in the project suite (0 collected). Deploy check warnings, not failures: `security.W004`, `W008`, `W009`, `W012`, `W016`.
- **Security issues:** Fallback `SECRET_KEY` is `unsafe-dev-key-change-me` (24 bytes). Signing a JWT with it emits PyJWT `InsecureKeyLengthWarning`. Example key is 38 characters, still under Django's 50-character guidance (`W009` when that key is what check sees; this audit's `--deploy` check used the fallback). `DEBUG=1` in the example serves `/media/` without authentication. Redis is published on host port 6379 with no password. Containers run as root. Django `runserver` is the API process.
- **Next development tasks:** Phase 1. Add a real `.env` workflow, generate and commit the first migrations on PostgreSQL, stop generating migrations at container start, add a health URL and a consistent error shape, fix the frontend TypeScript build, add Gunicorn behind a reverse proxy only when the app actually runs.

## 2. Accounts and authentication

- **Module name:** Accounts and authentication
- **Current implementation status:** Partial. Custom UUID user, role field, JWT obtain/refresh URLs, and a user viewset exist. Groups are not seeded. The React app can call login and stores tokens. No test covers this.
- **Completed features:** None.
- **Pending features:**
  - Django Groups and permissions aligned with Administrator, Management, Sales Executive, HR Executive, and Team Lead. Only a `role` CharField exists.
  - Self-service password change, reset, and forced change. Non-admins cannot update their own user row.
  - Refresh, rotation, and logout/blacklist. `djangorestframework-simplejwt` 5.5.1 defaults: access token 5 minutes, refresh 1 day, rotation off, blacklist off. Confirmed by importing `api_settings`. The UI never calls `/api/v1/auth/token/refresh/`.
  - `department` and `date_joined_company` are on the model. The user serializer omits both. Admin fieldsets omit `department`.
  - Employee codes are optional free text, not a sequence.
  - Inactive-user revocation beyond the next request (no outstanding-token blacklist). Inactive login itself is rejected.
- **Known bugs:**
  - `createsuperuser` leaves `role` at the model default `HR`. Probed: that superuser `POST /api/v1/clients/` returns **403** `Only Sales, Management or Admin can create clients.` Role checks do not treat `is_superuser` as Admin. The overview report would also take the HR branch and zero the revenue figures (code inspection, not HTTP-probed).
  - After 5 minutes the access token expires. `App.tsx` still treats any `localStorage.access` value as authenticated, and Axios has no 401 interceptor.
  - `UserViewSet` list is limited by role, but Team Lead receives every user (email, phone, role). Create/update/deactivate are admin-only. Deactivate sets `is_active=False` rather than deleting. Good direction; no test.
  - Inactive login probed: `POST /api/v1/auth/token/` returns **401** `No active account found with the given credentials`. An active sales user received access and refresh (**200**). This is not a completed feature: the UI path was not exercised.
- **Tests executed:** Project suite, 0 tests. Probes above on disposable SQLite via `APIClient`.
- **Tests passed:** None in the project suite.
- **Tests failed:** None in the project suite.
- **Security issues:** Short fallback HMAC key. No login throttle. JWT in `localStorage`. No server-side logout. User create accepts a password (minimum 10) but `createsuperuser` uses Django's default minimum of 8.
- **Next development tasks:** Phase 1 and 4. One permission module used by every view, groups bootstrap, token refresh in the client, role-aware navigation, tests for inactive users and each role.

## 3. Organizations

- **Module name:** Organizations (departments and business-code sequences)
- **Current implementation status:** Partial. `Department`, `CodeSequence`, and `next_business_code()` exist. No API and no UI.
- **Completed features:** None.
- **Pending features:** Department CRUD, assigning a department from the user admin and API, protecting sequence rows from casual admin edits, documenting gap behavior.
- **Known bugs:**
  - Sequence allocation commits inside its own `transaction.atomic()` during `Model.save()`. If the parent insert fails afterward, the number is consumed. Uniqueness still holds. Not probed under concurrency.
  - The helper is sound on PostgreSQL (`select_for_update` plus an integrity-error retry). It was not run against PostgreSQL here.
  - Disposable SQLite probe did generate `SW-CLI-0001`, `SW-JD-0001`, `SW-CAN-00001`, `SW-CAN-00002`, and `SW-INV-2026-0001`. That shows the formatter works. It does not verify locking.
- **Tests executed:** Project suite, 0 tests. ORM probe on disposable SQLite for four code families.
- **Tests passed:** None in the project suite.
- **Tests failed:** None in the project suite.
- **Security issues:** `CodeSequence` is editable in Django admin, so a privileged user can rewind or skip IDs.
- **Next development tasks:** Phase 2. Keep this table as the only ID source. Add tests that two concurrent allocations do not collide, on PostgreSQL.

## 4. Clients and contacts

- **Module name:** Clients, contacts, ownership history, activities
- **Current implementation status:** Partial. Models and viewsets exist. The UI can list and create a client (name, industry, optional sales owner). Contacts, activities, ownership history, and status changes have no UI.
- **Completed features:** None.
- **Pending features:**
  - Contact management, one primary contact, activity log, ownership-history display.
  - Rules for blacklisted clients (new JDs, submissions). Not enforced.
  - Object-level checks so a sales user cannot attach records to someone else's client.
  - Status values Lead / Active / Inactive / Blacklisted exist on the model and match the approved list.
- **Known bugs:**
  - **Reproduced.** Sales user `sales1` `POST /api/v1/client-contacts/` with another owner's client id returned **201**, and the contact row was stored. List filtering hides other owners' contacts; create does not check ownership.
  - Client activities use the same pattern (code inspection, not separately posted).
  - HR and Team Lead pass `allowed_roles` and can update client fields. Create is then rejected unless the role is Sales, Admin, or Management. Inconsistent.
  - Ownership history is written on create and on owner change in `perform_update`, but there is no read API. Superuser-with-role-HR cannot create, so the initial history row is never written for that account.
  - Several contacts may have `is_primary=True`. No constraint.
  - Company name is not unique.
- **Tests executed:** Project suite, 0 tests. Contact IDOR and superuser create probes.
- **Tests passed:** None in the project suite.
- **Tests failed:** None in the project suite.
- **Security issues:** Cross-owner contact create (above). Any authenticated role that can call the contact or activity viewset can attempt writes; Sales is the case that was reproduced.
- **Next development tasks:** Phase 4 and 5. Object permission on every child write, primary-contact constraint, blacklist rule once the business answers the open question, UI for contacts and history.

## 5. Sales

- **Module name:** Sales opportunities
- **Current implementation status:** Partial. `SalesOpportunity` model and CRUD API exist. No frontend.
- **Completed features:** None.
- **Pending features:** Pipeline stages in the UI, follow-up reminders, permission split so HR does not see commercial expected value, link to client ownership.
- **Known bugs:**
  - `permission_classes` is only `IsAuthenticated`. HR can list every opportunity, including `expected_value` (code inspection, not HTTP-probed).
  - Owner is not required to be an active Sales user.
  - No stage-history table. Updates overwrite `stage`.
- **Tests executed:** Project suite, 0 tests.
- **Tests passed:** None.
- **Tests failed:** None.
- **Security issues:** Commercial opportunity values are not restricted to sales and management roles.
- **Next development tasks:** Phase 4 and 5. Role gate, queryset by owner, history, UI. Decide whether HR should see this module at all.

## 6. Jobs (job descriptions)

- **Module name:** Jobs, assignments, status history
- **Current implementation status:** Partial. Model, constraints, CRUD, assign action, and match action exist. UI can create a JD and call match. Assignment has no UI.
- **Completed features:** None.
- **Pending features:**
  - JD creation limited to sales (open question: code also allows HR and Team Lead).
  - HR scoped to assigned JDs (open question: code returns all JDs to HR).
  - Unassign, assignment event history (today's row is updated in place), status history UI.
  - Skill requirements captured when the JD is created. The UI does not call `/api/v1/job-skills/`.
  - Blacklist / closed-JD guards.
- **Known bugs:**
  - **Reproduced.** `POST /api/v1/jobs/{id}/match/` raises `ValueError: chunk_size must be provided when using QuerySet.iterator() after prefetch_related()` from `apps/matching/services.py`. Django's test client re-raises; a running server would return HTTP 500. A `MatchRun` row is inserted before the loop, so the failed call still leaves a run. See Skills and matching.
  - Assign accepts only active HR or Team Lead ids and uses `get_or_create`, which matches "no duplicate assignment". Re-activating an inactive row overwrites `assigned_by` and does not append history. No unassign action.
  - Sales cannot change `sales_owner` on update. Admin and Management can. The new owner is not checked to be an active Sales user (unlike client create).
  - Experience and salary check constraints are in the model and were included in the disposable migration. Not tested with invalid payloads.
- **Tests executed:** Project suite, 0 tests. Match POST probe. SQLite migrate included the job constraints.
- **Tests passed:** None in the project suite.
- **Tests failed:** None in the project suite. The match probe raised `ValueError` (not a test-runner failure).
- **Security issues:** Match is available to every role that can read the JD, including Sales, and it walks every active candidate. Sales are otherwise blocked from the candidate API, so match results expose candidate name and code to Sales (code path; the probe crashed before returning results).
- **Next development tasks:** Phase 2 and 4. Fix matching before any UI work depends on it. Assignment history table. Decide HR visibility. Wire skills into the JD form.

## 7. Candidates and resumes

- **Module name:** Candidates, resumes, notes, consent
- **Current implementation status:** Partial. Shared candidate model, resume versions, Celery parse task, and a create/search/upload UI exist. Duplicate review, consent, and private file access do not.
- **Completed features:** None.
- **Pending features:**
  - Duplicate detection on normalized email, normalized phone, and file hash, with a human review queue. Never auto-merge by name. **Not implemented.** Identical emails are stored as two candidates.
  - Consent capture, privacy notice, retention, and deletion workflow. `CandidateConsent` is a model with admin registration only.
  - Signed, short-lived download URLs and S3-compatible storage. Dev storage is local `FileField`.
  - Resume version UI, notes UI, sourced-by display, skill capture. Upload sets the file then calls `parse_resume.delay()`.
  - Content checks beyond the extension (PDF/DOCX, 10 MB).
- **Known bugs:**
  - **Reproduced.** Two candidates with email `asha@example.com` / `Asha@Example.com` were both saved (`SW-CAN-00001`, `SW-CAN-00002`). `normalized_email` is indexed, not unique.
  - Phone normalization keeps every digit and nothing else. `+91 98-76` became `919876`. A local number and an E.164 number for the same person will not match. No review queue either way.
  - `ModelViewSet` destroy hard-deletes the candidate. Resumes cascade.
  - Upload writes the `Resume` row, then enqueues Celery. If Redis is down, the client can see an error after the row exists (code inspection, not probed).
  - Parser marks `FAILED` and retries. Extension is trusted; file bytes are not sniffed.
  - Search covers name, email, location, and skill name. The UI search box does not mention skills. Pagination still caps the response at 25.
  - Sales are not in `allowed_roles` (403 expected, not probed). The Candidates nav item is still shown to every logged-in user.
- **Tests executed:** Project suite, 0 tests. ORM duplicate-email insert on disposable SQLite.
- **Tests passed:** None in the project suite.
- **Tests failed:** None in the project suite.
- **Security issues:** With `DJANGO_DEBUG=1` (the example and the Compose backend), `config/urls.py` mounts `django.conf.urls.static` for `MEDIA_ROOT`. Resume URLs are guessable paths under `/media/resumes/…`. The serializer returns the file field. There is no authorized download view. Not fetched over HTTP in this audit (server not started).
- **Next development tasks:** Phase 2 (duplicate-review and consent models), Phase 4 (private download, block or queue duplicates), Phase 5 (UI), Phase 9 (storage). Do not treat the upload form as done.

## 8. Skills and matching

- **Module name:** Skills and rule-based matching
- **Current implementation status:** Partial and currently broken at runtime. Skill, candidate-skill, job-skill, match-run, and match-result models exist. The scorer crashes before it scores. No skill UI. The JD screen calls match and cannot succeed on Django 5.2.18.
- **Completed features:** None.
- **Pending features:**
  - Normalize names and honor aliases (`JS` / `JavaScript`, `React` / `React.js`, `Postgres` / `PostgreSQL`). `aliases` is a JSON list and is not read by `run_matching`. `services.py` does not contain the word `aliases`.
  - Use `JobSkill.weight` (stored, constrained 1–10, ignored). Mandatory vs preferred is only a cap: if any mandatory skill is missing, `overall_score` is forced to at most 49.
  - Score responsibilities from real data. `responsibility_score` is assigned the skill score. Weights in code are 40 / 25 / 15 / 10 / 10, which match the approved split, but two of the five inputs are not independent.
  - Explainable result in the UI (explanation JSON is stored, not returned by the match action, not rendered).
  - Match history API. Engine version `rules-v1` is stored.
  - Never auto-reject or auto-shortlist. The scorer does not change application status. That part matches the rule, and it is still not a completed feature.
- **Known bugs:**
  - **Reproduced.** `Candidate.objects.prefetch_related(...).iterator()` raises `ValueError` on Django 5.2.18 unless `chunk_size` is set. `run_matching` creates the `MatchRun` first. Probe: run count went from 0 to 1, then the exception. The same exception propagated out of `JobViewSet.match`.
  - Missing notice period or location awards high partial credit (100 if either notice value is null; 40 if the location string is not contained). Code inspection.
  - The match action loads every active candidate into a Python list and `bulk_create`s it. Not wrapped in one transaction with the run header. Not safe for a large database even after the crash is fixed.
  - Skill `normalized_name` is not derived on save. Nothing stops two spellings of the same skill.
- **Tests executed:** Project suite, 0 tests. Direct `run_matching` call and HTTP match probe.
- **Tests passed:** None in the project suite.
- **Tests failed:** None in the project suite.
- **Security issues:** Crash is availability of the match feature. Result payload, once fixed, leaks candidate identity to roles that can open a JD (see Jobs).
- **Next development tasks:** Phase 4, blocked on a one-line iterator fix only as a patch; the scoring rules still need a real implementation and tests with fixed fixtures (aliases, weights, mandatory flag, each sub-score). Do not call the engine done because the weights are named in a dict.

## 9. Applications and pipeline

- **Module name:** Applications and pipeline
- **Current implementation status:** Partial. Status enum matches the approved 12 statuses. Unique `(candidate, job)`. History row on create and on `change-status`. UI can create a row and lists raw UUIDs. No status buttons.
- **Completed features:** None.
- **Pending features:**
  - Legal transitions, not a jump from Identified to Joined.
  - One **active** application vs one row forever. The unique constraint blocks a new row after Rejected or Withdrawn. Open question.
  - Show candidate name, JD code, recruiter, and history. The UI shows UUID foreign keys.
  - `change-status` is not called by the frontend.
  - Freeze sourced-by and recruiter at the time of the event. Both FKs are writable on the serializer.
  - `contacted_at` is never set. `submitted_at`, `selected_at`, and `joined_at` are set only inside `change-status`, not when a client PATCHes `status`.
- **Known bugs:**
  - Any authenticated HR, Team Lead, Admin, or Management user can set any status (code inspection).
  - Sales cannot call the application API (`allowed_roles`), but can read interviews for those applications (see Interviews).
  - Pagination 25, no next control.
- **Tests executed:** Project suite, 0 tests. An application row was created via the ORM so placement and interview probes had a parent. `change-status` was not called.
- **Tests passed:** None in the project suite.
- **Tests failed:** None in the project suite.
- **Security issues:** Status and recruiter can be rewritten through the API, which destroys historical attribution. No object-level "this HR is assigned to this JD" check.
- **Next development tasks:** Phase 4 (transition service, read-only attribution) and Phase 5 (pipeline board that calls `change-status` and displays names).

## 10. Recruitment submissions

- **Module name:** Client submissions
- **Current implementation status:** Model and admin registration only. No serializer, view, URL, or UI.
- **Completed features:** None.
- **Pending features:** Submit a chosen resume version to the client, store who submitted it, client feedback, response status, and keep that attribution if the employee leaves (`submitted_by` is `PROTECT`, which is the right delete behavior once the API exists).
- **Known bugs:** None executed. The model cannot be used from the product UI.
- **Tests executed:** Project suite, 0 tests. Table was created on the disposable SQLite migrate.
- **Tests passed:** None.
- **Tests failed:** None.
- **Security issues:** None beyond "feature absent". Admin users could insert rows.
- **Next development tasks:** Phase 2 review of the model, Phase 4 API, Phase 6 workflow. Do not invent a submission from the application `SUBMITTED` timestamp; that timestamp is not a submission record.

## 11. Interviews

- **Module name:** Interviews
- **Current implementation status:** Partial. One model (round name, datetime, free-text interviewer, feedback, result) and an open CRUD API. No UI.
- **Completed features:** None.
- **Pending features:** Multiple interviewers, reschedule history, result history, link from result to the application stage without auto-reject, role checks, UI.
- **Known bugs:**
  - **Reproduced.** A Sales user `GET /api/v1/interviews/` returned **200** and the feedback string `Confidential: salary expectation discussed` for an application they do not manage. The viewset is `IsAuthenticated` only.
  - Updating `interview_date` or `feedback` overwrites history. No reschedule table.
  - Result choices include On Hold in addition to Pending / Passed / Failed.
  - `created_by` is set on create and is nullable.
- **Tests executed:** Project suite, 0 tests. Sales list probe above.
- **Tests passed:** None in the project suite.
- **Tests failed:** None in the project suite.
- **Security issues:** Interview feedback is readable and writable by every authenticated role, including Sales. This is a candidate-data leak.
- **Next development tasks:** Phase 4 permission and history before any UI. Phase 5 interview page.

## 12. Placements

- **Module name:** Placements
- **Current implementation status:** Partial. One-to-one with application, offered CTC, fee type (fixed or percent), fee value, expected revenue, guarantee days, joining date, status. API exists. No UI. Expected revenue is whatever the client sends; it is not calculated.
- **Completed features:** None.
- **Pending features:** Separate selection from joining in the workflow (both statuses exist on the model and are not tied to application timestamps). Guarantee-period tracking. Fee math. Hide commercial fields from HR if the business confirms that rule. UI.
- **Known bugs:**
  - **Reproduced.** HR `GET /api/v1/placements/` returned **200** with `offered_ctc` `1200000.00`, `agreed_fee_value` `8.33`, and `expected_revenue` `100000.00`. The same HR user `GET /api/v1/invoices/` returned **403**.
  - Queryset has no `order_by`. DRF emitted `UnorderedObjectListWarning` during the probe. Page boundaries can move.
  - No check that percent fees match CTC, or that joining date is empty until status is Joined.
  - HR is in `allowed_roles`, so HR can also POST and PATCH these fields (write not probed; permission class allows it).
- **Tests executed:** Project suite, 0 tests. HR read probe.
- **Tests passed:** None in the project suite.
- **Tests failed:** None in the project suite.
- **Security issues:** Commercial placement data is available to HR. Spec says HR has no billing/financial access. Invoices are restricted; placements are not.
- **Next development tasks:** Phase 4 field-level or role split, ordering, server-side fee calculation, tests. Phase 5 UI. Phase 6 link to billing.

## 13. Billing

- **Module name:** Billing (invoices, lines, payments, credit notes)
- **Current implementation status:** Partial. Invoice, line, payment, and credit-note models exist. Invoice, line, and payment viewsets are limited to Admin and Management. Credit notes have no API. No UI. Decimal fields are used.
- **Completed features:** None.
- **Pending features:**
  - Commercial terms master (not only per placement).
  - Credit notes, refunds, and adjustments as workflows. Outstanding balance is a property (`total - payments - credits`), not a stored cache. Good direction, incomplete.
  - Tax configuration. One `tax_rate` per line. No GST breakup.
  - Unique invoice numbers: `SW-INV-{year}-0001` via `CodeSequence`. Generated in the SQLite probe. Statutory format is an open question.
  - UI for invoices, lines, and payments. No frontend calls these URLs.
  - Transactions and `select_for_update` around payment vs outstanding.
- **Known bugs:**
  - Invoice `subtotal`, `tax_amount`, and `total` are writable. Lines recalculate them on line save. ORM probe stored an invoice with total `1000.00` and zero lines. The API serializer does not mark those amounts read-only (code inspection; not posted).
  - `Payment.save` sets status `PAID` or `PART_PAID` from payments vs `total` and ignores credit notes and `VOID`.
  - Payment serializer rejects amount greater than outstanding. On update, outstanding already includes the payment being edited, so a legitimate edit can be rejected (code inspection, not probed).
  - No DB constraint that payments + credits cannot exceed total. Concurrent payments can over-apply.
  - Negative `unit_amount` is allowed. Payment and credit-note amounts must be `> 0` (constraints present in the disposable migration).
- **Tests executed:** Project suite, 0 tests. HR invoice 403 probe. ORM invoice with no lines.
- **Tests passed:** None in the project suite.
- **Tests failed:** None in the project suite.
- **Security issues:** Role gate for invoice list is present and returned 403 for HR in the probe. Totals can still be forged by a permitted user. No audit row is written for payment or invoice changes.
- **Next development tasks:** Phase 2 constraints, Phase 4 a billing service inside `transaction.atomic()`, credit-note API, Phase 5 UI, Phase 7 revenue reports from these rows only.

## 14. Reports

- **Module name:** Reports (overview, HR, sales)
- **Current implementation status:** Partial. Three GET endpoints and a dashboard plus a JSON dump page. No filters. Numbers are simple counts, not the approved productivity reports.
- **Completed features:** None.
- **Pending features:** Filters for date, employee, department, client, JD, status, recruiter, and sales executive. HR productivity (submissions, interviews, selections, joins, not only application counts). Sales productivity. Management dashboard. Historical attribution when an owner changes. All from real tables (the endpoints do query the ORM; they are still not the required reports).
- **Known bugs:**
  - Overview for HR still counts all clients, all open jobs, and all active candidates. Applications and joined placements are filtered to that recruiter. Revenue is forced to 0 unless role is Admin or Management (code inspection).
  - Overview for Sales zeros candidates, applications, and placements, and scopes clients and open jobs to `sales_owner`.
  - The React reports page requests HR and sales together and ignores errors, so a 403 looks like an empty panel.
  - Dashboard always renders invoiced revenue and payments, which will be 0 for HR and Sales rather than hidden.
  - No date bounds. Counts are all-time.
- **Tests executed:** Project suite, 0 tests. Endpoints not HTTP-probed.
- **Tests passed:** None.
- **Tests failed:** None.
- **Security issues:** Revenue keys are omitted in value (set to 0) rather than removed, for non-finance roles. HR company-wide client and candidate counts may be more visibility than intended. Not probed.
- **Next development tasks:** Phase 7 after the workflow data is trustworthy. Do not build charts on these three payloads.

## 15. Audit, privacy, and consent

- **Module name:** Audit and privacy
- **Current implementation status:** Not started as a behavior. `AuditLog` and `CandidateConsent` models exist and are on the admin index. No writer, no reader API, no retention job, no privacy notice.
- **Completed features:** None.
- **Pending features:** Append-only audit for sensitive reads (resume download), status changes, ownership changes, and billing. Consent required or explicitly optional (open question). Retention and data-subject deletion. Records surviving employee exit: many FKs are `PROTECT`, which is a start, and hard delete of candidates/clients is still exposed.
- **Known bugs:** Nothing writes `AuditLog`. A download cannot be audited because there is no download authorization view.
- **Tests executed:** Project suite, 0 tests. Tables created on disposable migrate.
- **Tests passed:** None.
- **Tests failed:** None.
- **Security issues:** No trail for resume access, match runs, or invoice edits.
- **Next development tasks:** Phase 2 model review, Phase 9 implementation. Do not mark consent complete because the table exists.

## 16. Frontend shell

- **Module name:** Frontend (React, TypeScript, Vite)
- **Current implementation status:** Partial shell. Routes: `/login`, `/`, `/clients`, `/jobs`, `/candidates`, `/applications`, `/reports`. Axios instance points at `VITE_API_URL` or `http://localhost:8000/api/v1`. Tailwind is not a dependency. No React tests.
- **Completed features:** None.
- **Pending features:** Every screen in Phase 5 that is missing: users, contacts, JD assignment, skills, resume library, match explanation, pipeline actions, interviews, placements, invoices, payments, real reports, settings. Role-based menus. Token refresh. Pagination. Error boundary. No dead ends: several current buttons call the API, and several workflows have no button at all (status change, assign recruiters, skills).
- **Known bugs:**
  - **Reproduced.** `npm run build` (`tsc -b && vite build`) exits 1: `src/services/api.ts(2,45): error TS2339: Property 'env' does not exist on type 'ImportMeta'`. There is no `src/vite-env.d.ts` referencing `vite/client`. `npx tsc --noEmit` exits 2 with the same error. `npx vite build` exits 0 (bundle only, no typecheck).
  - Applications table shows candidate and job UUIDs.
  - Reports render `JSON.stringify` and swallow failures.
  - Login error is a generic string. No loading state on lists.
  - Auth gate reads `localStorage` during render and does not know the user's role.
- **Tests executed:** `npm run build`, `npx tsc --noEmit`, `npx vite build`. No component tests. No browser session.
- **Tests passed:** None (typecheck failed; Vite bundle is not a test).
- **Tests failed:** Typecheck, as above. Vite's own build succeeded and is not a functional test.
- **Security issues:** Access and refresh tokens in `localStorage`. No CSP. Role is not enforced in the router; a Sales user can open Candidates and only then see an API error.
- **Next development tasks:** Phase 1 (Vite types, refresh, error interceptor, env) then Phase 5 page by page, each page only after its API rules exist.

---

## Cross-check against the approved modules

| Area | Backend code | Frontend wired | Automated tests | Treated as complete |
| --- | --- | --- | --- | --- |
| Accounts, JWT, roles | Partial | Login only | No | No |
| Departments and ID sequences | Partial, no API | No | No | No |
| Clients, contacts, ownership | Partial | Client list/create | No | No |
| Sales opportunities | API only | No | No | No |
| JDs, assignment, status | Partial | Create and match button | No | No |
| Candidates, resumes, consent | Partial | Create, search, upload | No | No |
| Skills and matching | Broken at runtime | Match button calls it | No | No |
| Applications / pipeline | Partial | Create and UUID list | No | No |
| Submissions | Model only | No | No | No |
| Interviews | API, no role gate | No | No | No |
| Placements | API, HR sees fees | No | No | No |
| Billing | API, no credit-note workflow | No | No | No |
| Reports | Three unfiltered counts | Dashboard and JSON | No | No |
| Audit / privacy | Models only | No | No | No |
