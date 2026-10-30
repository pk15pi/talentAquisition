# Changelog

All notable changes to SynfoTalent are recorded here. The format is based on Keep a Changelog. This file did not exist before the Phase 0 audit; the starter snapshot is described so later entries have a baseline.

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
