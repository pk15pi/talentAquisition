# Changelog

All notable changes to SynfoTalent are recorded here. The format is based on Keep a Changelog. This file did not exist before the Phase 0 audit; the starter snapshot is described so later entries have a baseline.

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
