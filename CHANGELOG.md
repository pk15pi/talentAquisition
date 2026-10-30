# Changelog

All notable changes to SynfoTalent are recorded here. The format is based on Keep a Changelog. This file did not exist before the Phase 0 audit; the starter snapshot is described so later entries have a baseline.

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
