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

Docker and Docker Compose are required.

1. The included `.env` contains development-only local credentials. Change the secret key and database password before any shared or production deployment. You can instead copy `.env.example` to `.env` and set your own values.
2. From the project root, run:

   ```bash
   docker compose up --build
   ```

3. Open:
   - Frontend: http://localhost:5173
   - Django API: http://localhost:8000/api/v1/
   - Django Admin: http://localhost:8000/admin/

4. Create the first administrator:

   ```bash
   docker compose exec backend python manage.py createsuperuser
   ```

5. Sign in using the superuser credentials. Create employee accounts in Django Admin and set their SynfoTalent role (`ADMIN`, `MANAGEMENT`, `SALES`, `HR` or `TEAM_LEAD`).

The backend container generates initial migration files for the included Django apps and applies migrations on startup. Keep generated migrations in source control for subsequent development and use `python manage.py migrate` as a deployment release step.

## Local development

### Backend

```bash
cd backend
python -m venv .venv
# Activate the virtual environment
pip install -r requirements.txt
# Set environment variables from the root .env file or your shell
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Run the Celery worker in another terminal after Redis is running:

```bash
celery -A config worker -l info
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

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

## Key design choices

- UUID primary keys for major entities; readable sequential business codes such as `SW-CLI-0001`, `SW-JD-0001`, `SW-CAN-00001`, `SW-APP-00001` and year-prefixed invoice codes.
- One client has one primary sales owner. HR can work on multiple JDs and multiple recruiters can be assigned to one JD.
- Candidate records are shared across authorized HR users. A candidate can have a separate application against many JDs; candidate + JD is unique.
- Sourcing, application recruiter and submission attribution are separate.
- Resume extraction runs asynchronously through Celery/Redis. Files are stored in the local media volume in development.
- Candidate matching is rules-based first. Missing mandatory skills cap the candidate's score so a strong partial match cannot appear fully qualified.

## Important before production

This is a functional **starter/MVP codebase**, not a production-certified ATS. The source has been syntax-checked, but a full Docker/database/frontend integration build could not be run in this environment because package registries and Docker were unavailable.

Before using real candidate data, complete and test:

- Object-level permissions and workflow-specific authorization for every API, including client/contact and candidate-note access.
- Private S3-compatible storage (or equivalent), signed downloads, malware scanning and upload-content validation.
- Candidate duplicate-review/merge workflow and robust resume parsing quality checks.
- Privacy notices, consent/processing-basis records, retention schedules, data-subject request handling and deletion workflows applicable to your operations.
- Complete immutable audit events for sensitive reads/downloads and business changes.
- Invoice tax configuration, credit-note API/workflows, payment reconciliation and financial approval controls.
- Automated unit/API tests, frontend production build, security review, backups and restore drills.
- Production settings: `DEBUG=0`, strong secrets, secure cookies, HTTPS, allowed hosts, logging and monitoring.

Do not expose Django Admin or the development server directly to the public internet. Use a production WSGI/ASGI server behind a reverse proxy and configure a private database and object storage.
