# SynfoTalent

**Synfowebs Recruitment Management System – Version 1 starter project**

A modular monolith built with Django REST Framework, PostgreSQL, React + TypeScript, Redis and Celery.

## Included modules

- **Accounts:** custom UUID User model, employee codes and roles.
- **Organizations:** departments and transactional business-code sequences.
- **Clients & Sales:** client CRM, contacts, single sales ownership, ownership history, client activities and sales opportunities.
- **Jobs:** JD management, sales ownership, multiple recruiter assignments and status history.
- **Candidates:** shared candidate master, source attribution, resume versions, consent and notes.
- **Skills & Matching:** skill master, candidate/JD skill mappings and weighted rule-based matching.
- **Applications & Recruitment:** one candidate/JD application, status history and client submissions.
- **Interviews & Placements:** interview rounds and placement tracking.
- **Billing:** invoices, invoice lines, payment records and credit-note model foundations.
- **Reports & Audit:** management overview, HR and sales report endpoints, audit-log model.
- **Frontend:** login, dashboard, clients, JDs, candidates, applications and reports screens.

## Quick start with Docker

Docker and Docker Compose are required. `.env` is not in git.

1. Copy the template and keep `DJANGO_DEBUG=1` for local use. The sample secret starts with `dev-only-` and is refused when debug is off. Replace it before any shared deployment.

   ```bash
   cp .env.example .env
   ```

   `POSTGRES_HOST=localhost` in that file is for a Django process on the host. Compose overrides it to the `db` service, and overrides Celery to `redis://redis:6379`.

2. From the project root, run:

   ```bash
   docker compose up --build
   ```

   The backend container runs `migrate` and `bootstrap_groups`, then the development server. It does not run `makemigrations`.

3. Open:
   - Frontend: http://localhost:5173
   - Django API: http://localhost:8000/api/v1/health/
   - Django Admin: http://localhost:8000/admin/

4. Create the first administrator. `createsuperuser` sets role `ADMIN`. Active superusers bypass permission checks.

   ```bash
   docker compose exec backend python manage.py createsuperuser
   ```

5. Sign in with those credentials. Create other users in Django Admin and set their role. Saving a user puts them in the matching group: Administrator, Management, Sales Executive, HR Executive, or Team Lead. Access is the group's Django permissions, which an administrator can change. Running `bootstrap_groups` again does not reset those edits. Pass `--reset` only when you intend to restore the built-in grants.

   HR does not receive invoice, payment, or placement-fee permissions. Team leads can see every JD. HR sees a JD after they are assigned, unless someone grants `jobs.view_all_jobs`.

Resume files are stored on the media volume and are not served from `/media/`. An authorized download URL is still to be built.

## Local development

### Backend

PostgreSQL must be reachable at `POSTGRES_HOST` (default `localhost`). With debug off, `DJANGO_SECRET_KEY` is required and must not be the `dev-only-` sample.

```bash
cp .env.example .env
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py bootstrap_groups
python manage.py createsuperuser
python manage.py runserver
```

Run the Celery worker in another terminal after Redis is running on localhost (or set `CELERY_BROKER_URL`):

```bash
celery -A config worker -l info
```

Tests (PostgreSQL, 30 tests at the last Phase 1–2 run):

```bash
python manage.py test apps
python manage.py makemigrations --check --dry-run
```

### Frontend

```bash
cd frontend
npm ci
npm run dev
```

`npm run build` typechecks with `tsc` and then builds the Vite bundle.

## API overview

JWT:
- `POST /api/v1/auth/token/`
- `POST /api/v1/auth/token/refresh/`

Core resources:
- `/api/v1/users/`
- `/api/v1/clients/`, `/api/v1/client-contacts/`, `/api/v1/client-activities/` and `/api/v1/sales-opportunities/`
- `/api/v1/jobs/`
- `POST /api/v1/jobs/{id}/assign/` with `{"recruiter_ids": ["<user-uuid>"]}`
- `POST /api/v1/jobs/{id}/match/`
- `/api/v1/candidates/`
- `POST /api/v1/candidates/{id}/upload-resume/` (multipart field: `file`, PDF/DOCX, max 10 MB)
- `/api/v1/skills/`, `/api/v1/candidate-skills/`, `/api/v1/job-skills/`
- `/api/v1/applications/`
- `POST /api/v1/applications/{id}/change-status/` with `{"status": "SUBMITTED", "remarks": "..."}`
- `/api/v1/interviews/`, `/api/v1/placements/`
- `/api/v1/invoices/`, `/api/v1/invoice-lines/`, `/api/v1/payments/`
- `/api/v1/reports/overview/`, `/api/v1/reports/hr/`, `/api/v1/reports/sales/`
- `GET` and `PATCH /api/v1/system-configuration/` for retention days and the privacy notice (no default period)
- `GET /api/v1/users/me/`
- `GET /api/v1/health/` (no authentication)

Creating a candidate requires `consent_acknowledged: true` and `privacy_notice_version`. If system configuration has a notice version, the submitted version must match it. A rejected or withdrawn application stays on file; a new active application for the same candidate and JD is allowed. A second active row is rejected.

## Key design choices

- UUID primary keys for major entities; readable sequential business codes such as `SW-CLI-0001`, `SW-JD-0001`, `SW-CAN-00001`, `SW-APP-00001` and year-prefixed invoice codes.
- One client has one primary sales owner. HR can work on multiple JDs and multiple recruiters can be assigned to one JD.
- Candidate records are shared across users who have `candidates.view_candidate`. One active application is allowed per candidate and JD. Rejected and withdrawn rows stay in history.
- Commercial defaults live on the client. A JD may override fee type, fee value, and guarantee days.
- Sourcing and the application recruiter are set by the server from the signed-in user. Status changes go through `change-status`.
- Resume files are stored locally in development and are not publicly served. Parsing still runs through Celery when a file is uploaded.
- Candidate matching is not usable yet. `run_matching` raises `ValueError` on Django 5.2 because it calls `iterator()` after `prefetch_related()` without `chunk_size`. Weights and aliases are stored and not scored. That fix is Phase 4.

## Important before production

Phase 1 and Phase 2 added a bootable foundation, permission groups, and the initial PostgreSQL migrations. This is still not a production ATS. Do not load real candidate files until downloads are authorized and the match crash is fixed.

Still open:

- Signed, short-lived resume downloads and S3-compatible storage. Uploads save a file; nothing serves it.
- The match engine crash and real skill/alias/weight scoring.
- Duplicate approval records a decision and does not merge the two profiles.
- Retention days are editable and are not enforced by a deletion job.
- Credit-note API, invoice total integrity, and payment races.
- Gunicorn, Nginx, HTTPS, and backups.
- Most screens beyond the original six. The candidate form now asks for consent.

`python manage.py test apps` is the automated suite. `npm run build` is the frontend production build. Docker itself was not started in the Phase 1 verification environment because the daemon was not running; migrate and both dev servers were run on the host against PostgreSQL 16.
