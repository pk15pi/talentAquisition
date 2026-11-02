# Changelog

All notable changes to SynfoTalent are recorded here. The format is based on Keep a Changelog. This file did not exist before the Phase 0 audit; the starter snapshot is described so later entries have a baseline.

## 2026-11-02 — Phase 5 frontend pages

Separate pull request into `master`. Left unmerged. No Phase 6 work. No migration. PR #4 is already merged.

### Added

- Tailwind 4 and the recruitment workspace: login, role-aware shell, dashboard, users, clients with contacts and activities, job descriptions with skills and match explanations, candidates, duplicate review, the application board, interviews, submissions, placements, billing, reports, and settings.
- Vitest and Testing Library. `npm test` covers login, navigation, consent, pipeline moves, placement visibility, report zeros, duplicate approval, billing totals, and retention.
- `frontend/scripts/verify-phase5.mjs` for the headless Chrome permission pass.
- `GET /api/v1/users/me/` returns `permissions` and `is_superuser`. User rows include `can_own_client` and `can_be_assigned_recruiter`. These fields let the UI hide controls. The API permission checks are unchanged.
- Optional parent filters on contacts, activities, notes, skills, interviews, and submissions, plus `status` on duplicate reviews. Read-only names on the records the new pages list.

### Changed

- "Find candidates" is not rendered without `jobs.run_match`. Mandatory skill failures are shown on the result. HR does not see billing navigation, placement CTC, fees, or revenue, or dashboard and report money. Management does, using the figures the API returns. A financial zero stays zero.
- Candidate save still sends `consent_acknowledged` and `privacy_notice_version` only after the checkbox is checked. Duplicate approve and reject call `decide` and do not offer a merge.
- Application buttons call `change-status` only for the legal next step, reject, or withdraw.

### Verified

- `python manage.py test apps` on PostgreSQL 16.15: 82 tests, OK.
- `python manage.py check` with debug off: no issues.
- `python manage.py makemigrations --check --dry-run`: no changes.
- `npm run build`: exit 0. `npm test`: 13 passed.
- Headless Chrome: HR blocked from billing and placement amounts; Management sees CTC ₹8,80,011.22, revenue ₹7,70,022.33, and invoice ₹6,54,321.09; Sales has no Find candidates; HR match lists missing Python; pipeline Identified to Contacted; consent required; duplicate approve does not merge.

### Not done

- Sales opportunity screens, report filters, duplicate merge, retention deletion, resume download in the browser (HR and Management still lack `candidates.view_resume_content`), and Phase 6 end-to-end automation.

## 2026-11-02 — Phase 4 APIs

APIs only. No Phase 5 screens, no duplicate merge, no retention deletion, and no new migration. The pull request is https://github.com/pk15pi/talentAquisition/pull/4 and was left unmerged. That pull request was later merged.

### Added

- `POST /api/v1/jobs/{id}/match/` runs the scorer for `jobs.run_match` and returns component scores, weights, alias matches, and `mandatory_skill_failure`. A missing mandatory skill is flagged and does not cap the score or change the application. The `MatchRun` is inserted only after scoring succeeds.
- Application `change-status` accepts only the next pipeline step, or Rejected or Withdrawn, until Joined. Joined, Rejected, and Withdrawn do not move again. The admin form uses the same map.
- `POST /api/v1/resumes/{id}/download/` and `GET /api/v1/resume-downloads/?token=` for users who hold `candidates.view_resume_content`. The token lasts 5 minutes and is checked again on download. `/media/` stays unrouted.
- `GET /api/v1/duplicate-reviews/` and `POST /api/v1/duplicate-reviews/{id}/decide/`. Decide calls `decide()` and does not merge or delete profiles.
- `GET/POST/PATCH /api/v1/submissions/` with the submission status map. New groups for HR, Team Lead, and Management include the submission permissions. Existing groups are not rewritten.
- `GET/POST/PATCH /api/v1/interview-participants/`, gated by the interview view, add, and change permissions. Sales remain 403.
- Placement create and update copy effective client/JD fee terms and derive expected revenue when the caller does not send it. HR still has no `add_placement` and no financial permissions.
- `GET/POST/PATCH /api/v1/credit-notes/`. Invoice, line, payment, and credit-note writes lock the invoice. API totals come from lines. Outstanding subtracts payments and credit notes.
- Sales opportunity API tests. Owner reassignment requires `sales.view_all_salesopportunity`. Expected value stays on the row the user is allowed to read.

### Changed

- The jobs screen "Find candidates" button calls the matcher and shows how many active candidates were scored. It does not shortlist or reject anyone.
- Application responses include candidate, job, and recruiter names plus status history.

### Migration

None. No column was added or relaxed. Consent timestamps were not invented. The placement guarantee column stays non-null; 90 is used only when the client and the JD both leave guarantee empty.

### Verified

- `python manage.py test apps` on PostgreSQL 16.15: 78 tests, OK, 0 failures.
- `python manage.py check`: no issues.
- `python manage.py makemigrations --check --dry-run`: no changes.
- `npm run build`: exit 0.
- Headless Chrome: Team Lead sees "Matched 1 active candidate. Nobody was shortlisted or rejected automatically." Sales sees "You do not have permission to perform this action."

### Not done

- Duplicate profile merge.
- Retention deletion.
- Phase 5 React screens, including a match explanation panel and hiding Find candidates from users without `jobs.run_match`.
- Admin invoice headers can still be typed apart from lines until the next line save.
- Phase 7 report filters, Phase 9 hardening, and Phase 10 Gunicorn/Nginx.

## 2026-11-02 — Phase 3 review-fix follow-up pull request

PR #2 was already merged, so the review fixes were not in `master`. They are in https://github.com/pk15pi/talentAquisition/pull/3, which was left unmerged. The verification below is the 2026-11-02 run.

## 2026-11-01 — Phase 3 review corrections

### Fixed

- `User.save()` and login no longer rewrite group membership. `create_user`, `create_superuser`, the admin add form, and the user API create call `assign_default_role_group()`, which only adds the role's group. Removed memberships stay removed after login, profile updates, role edits, and `bootstrap_groups`.
- Invoice, line, payment, and credit-note admins enforce their own add/change/view permissions. A user with only `billing.view_invoice` cannot add or change lines, payments, or credit notes, and the standalone URLs return 403. Foreign keys and autocomplete are limited to related rows the user can view, so a billing user cannot attach a placement they cannot see, and placement labels do not include CTC, fees, or revenue.
- Creating a candidate in the admin requires an explicit consent confirmation or a documented non-consent basis (`contract`, `legal_obligation`, or `legitimate_interest`). The admin does not invent a consent time. Consent confirmation stores the time of that confirmation and a `CandidateConsent` row. Another basis stores the written documentation and leaves `consent_recorded_at` empty. The API still requires `consent_acknowledged` and a matching privacy-notice version.
- Client owner changes, job status changes, recruiter assignment and removal, application status changes, and interview reschedules are covered by tests that submit the Django admin form and check the history row's actor.

### Migration

`candidates.0003_consent_evidence_optional_timestamp` makes `Candidate.consent_recorded_at` nullable and tightens the withdrawal check so a withdrawal cannot be stored without a recorded consent. This is required so a documented non-consent basis can be stored without writing a false consent timestamp. Existing rows already have a timestamp, so the change does not rewrite them. No earlier migration files were edited.

### Verified

- `python manage.py test apps` on PostgreSQL 16, re-run 2026-11-02: 66 tests, OK, 0 failures. The extra test checks that placement CTC and revenue do not appear on an invoice form or its placement autocomplete for a user without `placements.view_placement_financials`.
- `python manage.py check`: no issues.
- `python manage.py makemigrations --check --dry-run`: no changes.
- Sensitive-data coverage is in `backend/apps/accounts/tests/test_admin_review.py` (`SensitiveAdminLeakTests`) and `backend/apps/accounts/tests/test_admin_permissions.py` (`test_resume_and_compensation_fields_follow_their_permissions`, `test_hr_placement_is_view_only_and_hides_financial_fields`). Those tests were already on this branch; the invoice-widget case was added in this follow-up.

## 2026-11-01 — Phase 3 Django admin

Admin only. No Phase 4 matcher work, no Phase 5 pages, no duplicate merge, and no retention deletion. No migration files were added or edited.

### Added

- List display, filters, search, ordering, and date hierarchy on the core admins: accounts, organizations, clients, sales, jobs, candidates, matching, applications, interviews, placements, billing, recruitment submissions, and audit.
- Inlines for contacts, activities, ownership history, assignments, skills, status history, resumes, notes, consent, duplicate reviews, application history, submissions, interview participants and events, invoice lines, payments, and credit notes.
- Admin querysets for clients, jobs, applications, interviews, and opportunities use the same visibility helpers as the API.
- `apps/accounts/tests/test_admin_permissions.py` covers group access, a direct permission grant, superuser bypass, object scope, resume and compensation visibility, HR placement view-only, billing denial, immutable history and finance rows, code sequences, protected groups, and duplicate-review approval without a merge.

### Changed

- Resume file, parsed text, and file hash stay off the admin form without `candidates.view_resume_content`. Candidate CTC stays off without `candidates.view_candidate_compensation`. Placement CTC, fee, revenue, and guarantee days stay off without `placements.view_placement_financials`, and they are read-only without `placements.change_placement_financials`.
- HR still has `placements.view_placement` only, so the placement admin page is view-only and has no financial fields. Adding a placement in the admin also requires `change_placement_financials`.
- History, audit, invoices, payments, credit notes, and placements cannot be deleted in the admin, including by an active superuser. Candidates, clients, jobs, users, and skills are retired with status or `is_active`. The five default groups cannot be deleted. Only an active superuser can edit a `CodeSequence` counter. A non-superuser cannot grant `is_superuser` from the user form.
- Admin saves of client owner, job status, application status, recruiter assignment, and interview date write the existing history rows. A new candidate saved in the admin records consent and queues a duplicate review without merging.

### Verified

- `python manage.py test apps`: 56 tests, OK, PostgreSQL 16.
- `python manage.py check`: no issues.
- `python manage.py makemigrations --check --dry-run`: no changes.
- Chrome: HR staff sees a view-only placement with no fee fields and receives 403 on `/admin/billing/invoice/`. Management sees offered CTC `880011.22`, expected revenue `770022.33`, and invoice total `654321.09`.

### Not changed

- The matching formula and `POST /jobs/{id}/match/` still return 503.
- Duplicate approval still does not merge profiles.
- Retention values are stored and not enforced.
- API permission checks are unchanged. HR still cannot create a placement through the API.

## 2026-10-30 — Review follow-up before Phase 3

PR #1 stays open.

### Changed

- Candidate API no longer returns resume `file`, `parsed_text`, or `file_hash`. `current_ctc` and `expected_ctc` require `candidates.view_candidate_compensation` (not granted to HR by default). Django admin hides the same fields without that permission or `candidates.view_resume_content`.
- `POST /api/v1/jobs/{id}/match/` returns HTTP 503 `matching_unavailable` and does not run the scorer. The jobs screen disables "Find candidates".
- Login route guard re-reads the access token when the location changes, so a successful sign-in leaves the login page.
- Frontend image is `node:22-bookworm-slim`. `frontend/docker-entrypoint.sh` installs dependencies when the `node_modules` volume has no Vite binary.
- `playwright-core` is a devDependency for `frontend/scripts/verify-browser.mjs`.

### Added

- Tests for resume privacy, the five default groups (candidates, JD scope, assignment, interview feedback), and HR placement create returning 403.
- `.github/workflows/test.yml` runs the Django suite on PostgreSQL 16 and `npm run build`.

### Verified

- `python manage.py test apps`: 40 tests, OK.
- `sudo docker compose up --build`: db, redis, backend (`/api/v1/health/` 200), worker (`celery ready`), frontend (Vite 200) after the host `FORWARD` chain allowed container traffic.
- Headless Chrome: consent checkbox blocks save; checking it creates `SW-CAN-00001`; replacing the access token and reloading refreshes it. Screenshots under `/opt/cursor/artifacts/screenshots/`.

### Not changed

- HR still cannot create a placement and still cannot see CTC, fee, or revenue. Left as an open question.
- Duplicate merge is still not implemented. The required future behavior is recorded in `DEVELOPMENT_STATUS.md` and `apps/candidates/reviews.py`.
- The matching formula is still Phase 4.

## 2026-10-30 — Phase 1 foundation and Phase 2 database

Application code, the first migrations, and tests. No Phase 3 admin polish and no Phase 4 matcher fix.

### Added

- Django groups Administrator, Management, Sales Executive, HR Executive, and Team Lead. `bootstrap_groups` creates them once and does not reset later edits unless `--reset` is passed.
- Permission checks on the API. Active superusers bypass them. HR is not granted invoice, payment, or placement-fee permissions.
- URL versioning under `/api/v1/`, a shared error body (`detail`, `code`, `errors`), and `GET /api/v1/health/`.
- Explicit JWT lifetimes (30-minute access token). The React client refreshes once on HTTP 401.
- `SystemConfiguration` for retention days and the privacy notice. Periods stay null until an administrator sets them. `GET`/`PATCH /api/v1/system-configuration/`.
- Client commercial defaults and JD overrides.
- Consent required before a candidate row is stored, plus a consent history row.
- `DuplicateReview`. Approving records an audit entry and does not merge or delete the two profiles.
- One active application per candidate and JD. Rejected and withdrawn rows stay and free the slot.
- `SkillAlias`, interview participants and events, job-assignment history, sequenced credit-note numbers.
- Initial migrations for every app. `python manage.py test apps`: 30 tests, 0 failures, on PostgreSQL 16.
- `frontend/package-lock.json`. `npm run build` passes.

### Changed

- Compose no longer runs `makemigrations`. It migrates, bootstraps groups, then starts the dev server. `.env.example` uses `POSTGRES_HOST=localhost`; Compose overrides the host to `db`.
- Debug off refuses a missing secret and refuses a secret that starts with `dev-only-`.
- `/media/` is not publicly served.
- `createsuperuser` sets role `ADMIN`.
- README matches the commands above.

### Not done

- Match still raises `ValueError` on Django 5.2 (`iterator()` after `prefetch_related()`). Left for Phase 4.
- Duplicate approval does not merge field values.
- Retention is stored and not enforced by a deletion job.
- Docker Compose was not booted here; the daemon was not running. Host `runserver` and Vite were started against PostgreSQL 16.

## 2026-10-30 — Phase 0 audit

Documentation only. No application code, migrations, dependencies, or configuration were changed.

### Added

- `AUDIT_REPORT.md` — architecture, gap, security, test, and phased-delivery audit.
- `DEVELOPMENT_STATUS.md` — per-module status. No feature is marked complete, because none has verified backend behavior, frontend integration, and tests together.
- `CHANGELOG.md` — this file.

### Audit result (no product change)

The starter does not boot from a clean clone until `.env` exists, PostgreSQL is reachable, and initial migrations are generated. `POST /api/v1/jobs/{id}/match/` raises `ValueError` on Django 5.2 and leaves an orphan match run. Several authorization holes were reproduced with Django's test client against a disposable SQLite copy (see the audit). `npm run build` fails typecheck. `python manage.py test` discovers zero tests.

## Baseline — commit `02a65d2` ("first commit")

Imported starter, previously undocumented here. Not re-verified as a finished release.

### Added in that commit

- Django project `backend/` with apps for accounts, organizations, clients, sales, jobs, candidates, applications, recruitment, interviews, placements, billing, matching, reports, and audit.
- React + TypeScript + Vite client `frontend/` with login, shell, and list/create screens for clients, job descriptions, candidates, applications, and a JSON report view.
- `docker-compose.yml` for PostgreSQL 16, Redis 7, Django `runserver`, a Celery worker, and the Vite dev server.
- `.env.example`, Dockerfiles, and `README.md`.

### Not in that commit

- Django migrations, automated tests, Gunicorn, Nginx, Tailwind, S3-compatible storage, signed resume URLs, a lockfile, or a changelog.
