# SynfoTalent Phase 0 audit

Date: 2026-10-30. Scope: read the existing repository, run safe diagnostics, and write this report. No application code was changed. Migrations were generated only in a disposable copy under `/tmp/st-backend` (SQLite) and were not added to the repo.

Repository at audit: commit `02a65d2` (`first commit`) on `master`. Product name in the README: SynfoTalent, an internal ATS and recruitment CRM for Synfowebs.

## How to read the evidence

- **Project test suite:** `python manage.py test` discovered zero tests. Claims below do not treat that as coverage.
- **Code inspection:** reading the files named in each finding.
- **Import / command:** a command actually run in this environment.
- **Disposable probe:** Django ORM or `APIClient` against a copy of the backend whose settings were patched to SQLite. That copy is not the repo and is not PostgreSQL. Where a probe result is cited, the HTTP status or exception is from that client. Django's test client re-raises uncaught view exceptions instead of returning HTTP 500; those cases say so.

Tool versions resolved while installing the existing manifests (not pinned in a lockfile before this audit):

| Tool | Version |
| --- | --- |
| Python | 3.12.3 |
| Django | 5.2.18 |
| djangorestframework | 3.18.3 |
| djangorestframework-simplejwt | 5.5.1 |
| Celery | 5.6.3 |
| psycopg | 3.3.6 |
| Node | 22.23.4 |
| npm | 10.9.9 |
| Vite (after `npm install`) | 6.4.5 |
| Docker CLI | 29.1.3 (installed during the audit; it was not on the image at start) |
| Docker Compose | 2.40.3 |
| Docker daemon | Not running (`policy-rc.d` denied service start; systemd is not the init here) |
| PostgreSQL server | Not installed. `localhost:5432` connection refused |

## Business requirements, as understood

SynfoTalent is an internal system for one IT-services / talent firm (Synfowebs), not a multi-tenant SaaS product. The commercial object is a client. A sales executive owns the client relationship. HR works a shared candidate database and is assigned to job descriptions. Management watches productivity and revenue. Money is tracked from offer through invoice and payment, and HR is not supposed to see billing or other financial data.

Understood rules, taken from the brief and checked against the code (not invented where the code is silent):

1. A client has one primary sales owner, many contacts, and an ownership-change history. Statuses: Lead, Active, Inactive, Blacklisted.
2. A job description is created by sales, belongs to one client, has a sales owner, and may have several HR assignees with no duplicate assignment. Statuses: Draft, Open, On Hold, Closed, Cancelled. Public id `SW-JD-0001` comes from a database sequence, not from `COUNT(*)`.
3. Candidates are one shared database. They are not copied per JD. Public id `SW-CAN-00001`. Resume versions are kept. The sourcer is recorded. Duplicates are detected from normalized email, normalized phone, and file hash, then reviewed by a person. Same name alone never merges two people.
4. Skills are a master list with category, normalized name, and aliases. Candidate skills carry experience. JD skills are mandatory or preferred and have weights. Skills are not a comma-separated string.
5. Matching is explainable and repeatable, versioned, and stored. Weights: skills 40, experience 25, responsibilities 15, location 10, notice 10. Missing mandatory skills are flagged. The engine never auto-rejects or auto-shortlists.
6. Pipeline statuses: Identified, Contacted, Interested, Shortlisted, Submitted, Client Review, Interview, Selected, Offered, Joined, Rejected, Withdrawn. One active application per candidate and JD. Status history is kept. Rejected rows are kept.
7. Interviews have rounds, interviewers, feedback, pass/fail/pending, reschedule, and history.
8. A placement records selection, offer, offered CTC, joining date, fixed or percent fee, expected revenue, and a guarantee period. Joining is tracked separately from selection.
9. Billing has commercial terms, unique invoice numbers, line items, tax, a link to a placement, partial payments, outstanding balance, credit notes, and refunds or adjustments. Money is `Decimal`. Balances are derived from records inside transactions.
10. Roles: Administrator, Management, Sales Executive, HR Executive, Team Lead, via Django Groups and permissions plus a role field. Enforced in the API. Inactive users cannot log in. Business rows survive an employee leaving.
11. Reports for HR productivity, sales productivity, and a management dashboard, filtered by date, employee, department, client, JD, status, recruiter, and sales executive, using real rows and historical attribution.
12. Candidate consent, a privacy notice, and data retention are in scope.
13. Target shape: modular monolith; Django and DRF; PostgreSQL; JWT; Celery; Redis; React, TypeScript, Tailwind, React Router, Axios; PDF and DOCX resumes; S3-compatible storage with local files in development and short-lived signed URLs; Docker Compose; Nginx; Gunicorn; UUID primary keys on major entities; backend split into models, serializers, views, permissions, services, selectors, tasks, and tests; frontend feature folders.

Where a rule is not decided, it is an open question at the end of this report. It is not implemented "by assumption".

## What stops the app from running

These are configuration and dependency facts from this environment. They are enough to stop a clean clone.

1. **`.env` is missing.** `.gitignore` ignores `.env`. It is not in git. `docker compose config` exits 1 with `env file /workspace/.env not found`. README step 1 says the included `.env` contains development credentials. That file is not in the commit. `.env.example` is the template. Compose `env_file: .env` still points at `.env` even if you pass `--env-file .env.example` (re-tried; same error).
2. **PostgreSQL is required and was not reachable.** Settings use `django.db.backends.postgresql` only. With no `.env`, host is `localhost` and port `5432`. Connection refused. `manage.py test` skipped the database because there are no tests; it did not prove migrate-on-Postgres.
3. **Redis hostname `redis`.** Celery settings default the broker to `redis://redis:6379/0`. Resume parsing and the worker only make sense on the Compose network. Redis was not running on the host.
4. **No migrations in the tree.** A first boot is supposed to create them. The backend command in Compose is `makemigrations` for every app label, then `migrate`, then `runserver`, with the source tree bind-mounted. The first successful boot writes migration modules into `backend/apps/*/migrations/` on the host. Until that happens, `migrate` has nothing to apply.
5. **Docker daemon was not running here**, so images were not built and `docker compose up` was not run. The CLI can render config once `.env` exists (verified by copying the example to `.env`, running `docker compose config`, then deleting `.env`).
6. **Frontend production script fails typecheck** (see section D). `npm run dev` was not started. `npm install` succeeds and `npx vite build` succeeds, so the dev server is likely to start, and the documented `npm run build` does not.
7. **Host-side Django against a copied example `.env` will look for host `db`.** `.env.example` sets `POSTGRES_HOST=db`, which is the Compose service name. The settings default of `localhost` applies only when the variable is unset.

`python manage.py check` exits 0 without a database. That does not mean the API serves traffic.

---

## A. Existing architecture

Modular monolith in one repository.

```
backend/                 Django project package config/
  apps/accounts          custom user
  apps/organizations     Department, CodeSequence
  apps/clients           client CRM
  apps/sales             opportunities
  apps/jobs              job descriptions
  apps/candidates        candidate master, resumes, notes, consent model
  apps/matching          skills and match runs
  apps/applications      pipeline
  apps/recruitment       Submission model only
  apps/interviews
  apps/placements
  apps/billing
  apps/reports           no models; three API views
  apps/audit             AuditLog model only
  apps/common.py         RolePermission
frontend/src
  pages/Login.tsx
  layouts/Layout.tsx
  services/api.ts
  features/{dashboard,clients,jobs,candidates,applications,reports}
docker-compose.yml       db, redis, backend, worker, frontend
```

Request path today: browser (Vite, port 5173) → Axios → Django `runserver` (port 8000) → PostgreSQL. JWT in the `Authorization` header. Celery worker shares the backend image and the media volume. Redis is the broker.

What the target stack asked for and the tree does not contain:

| Target | In the repo |
| --- | --- |
| Django + DRF | Yes. Django 5.2.18 and DRF 3.18.3 install from `requirements.txt`. |
| PostgreSQL | Yes, driver and Compose service. No server in this audit environment. |
| JWT | Yes, SimpleJWT obtain and refresh routes. Refresh unused by the UI. |
| Celery + Redis | Yes, one task (`parse_resume`). |
| React + TypeScript + React Router + Axios | Yes. |
| Tailwind | No. `frontend/src/styles.css` is plain CSS. `package.json` has no Tailwind packages. |
| PDF/DOCX | Yes, `pypdf` and `python-docx`, extension check on upload. |
| S3-compatible storage and signed URLs | No. `FileField` and local `MEDIA_ROOT`. |
| Nginx + Gunicorn | No. No `nginx` config, `gunicorn` not in requirements, no `asgi.py`. |
| UUID PKs on major entities | Mixed. User, Department, Client, SalesOpportunity, Job, Candidate, Application, Placement, Invoice use UUID. Contact, activity, ownership history, assignment, resume, skill, interview, payment, credit note, submission, and match rows use the implicit bigint `AutoField`. |
| Per-app permissions, services, selectors, tasks, tests | Only `apps/common.py` (`RolePermission`), `apps/matching/services.py`, `apps/organizations/utils.py`, and `apps/candidates/tasks.py`. No selectors. No test modules. |
| API versioning | Path prefix `/api/v1/` only. |

Layering inside an app is usually `models.py`, `serializers.py`, `views.py`, `urls.py`, `admin.py`. Views talk to the ORM directly. Matching is the only domain service.

## B. Implemented vs missing modules

"Implemented" here means source exists. It does not mean verified. See `DEVELOPMENT_STATUS.md` for the completion rule.

| Module | Models | API | Admin | UI | Tests | Gap that blocks the business rule |
| --- | --- | --- | --- | --- | --- | --- |
| Accounts | Yes | Users CRUD, JWT | Yes | Login, no user admin UI | No | Groups unused; superuser role defaults to HR |
| Organizations | Yes | No | Yes | No | No | No department API |
| Clients | Yes | CRUD, contacts, activities | Yes | List/create client | No | Ownership not enforced on contact create |
| Sales | Yes | CRUD | Yes | No | No | No role split |
| Jobs | Yes | CRUD, assign, match | Yes | Create, match button | No | Match crashes; no assignment UI |
| Candidates | Yes | CRUD, notes, upload | Yes | Create, search, upload | No | No duplicate review; public media in DEBUG |
| Consent | Model | No | Yes | No | No | Unused |
| Skills / matching | Yes | Skill CRUD; match via jobs | Yes | Match results panel | No | Engine crashes; weights and aliases unused |
| Applications | Yes | CRUD, change-status | Yes | Create, UUID list | No | No transitions; UI cannot change status |
| Submissions | Model | No | Yes | No | No | Whole workflow missing |
| Interviews | Yes | CRUD | Yes | No | No | No role gate, no reschedule history |
| Placements | Yes | CRUD | Yes | No | No | HR can read fees; revenue not calculated |
| Billing | Yes | Invoices, lines, payments | Yes | No | No | Credit notes have no API; totals writable |
| Reports | No | 3 endpoints | n/a | Dashboard + JSON | No | No filters, not the productivity reports |
| Audit | Model | No | Yes | No | No | Nothing writes a row |
| Frontend shell | n/a | n/a | n/a | 6 screens | No | Most Phase 5 pages absent |
| Production edge | n/a | n/a | n/a | n/a | No | No Nginx, Gunicorn, or private object storage |

Screens in the brief that have **no route**: users, contacts, assignment, skills, resume library, match explanation, pipeline board, interviews, placements, invoices, payments, settings, and any report that is not a raw JSON dump.

## C. Backend audit

### Settings and process model

`backend/config/settings.py` loads `../.env` with `python-dotenv`. `DEBUG` is on only when `DJANGO_DEBUG=1`. The code default is off, so a bare `manage.py check` in this audit saw `DEBUG=False` and secret `unsafe-dev-key-change-me`. The example file turns debug on.

REST framework defaults: JWT authentication, `IsAuthenticated`, page number pagination, page size 25. No filter backend, no throttle, no custom exception handler, no schema package. `SIMPLE_JWT` is unset, so library defaults apply (access 5 minutes, refresh 1 day). Confirmed by reading `api_settings` after Django setup.

`INSTALLED_APPS` includes every domain app. `AUTH_USER_MODEL` is `accounts.User`. Time zone `Asia/Kolkata`. `USE_TZ` is true. Media root is `backend/media`. When debug is on, `config/urls.py` adds unauthenticated static serving for that directory.

Celery app lives in `config/celery.py` and is imported from `config/__init__.py`. One task, autodiscovered.

There is no `LOGGING` dict, no health URL, no `ATOMIC_REQUESTS`.

### Permissions

`RolePermission.has_permission` allows the request when the user is authenticated and either `allowed_roles` is unset, the user is a superuser, or `user.role` is in the list. It does not implement `has_object_permission`. Queryset filtering is copy-pasted per view and is not applied to creates.

Roles are a string on the user. `Group` and `Permission` tables come from Django and are never populated by this project. There is no fixture, data migration, or management command.

Views that set `allowed_roles`:

| View | Roles |
| --- | --- |
| Clients | All five roles, then create is narrowed in `perform_create` |
| Jobs | All five |
| Candidates, notes, skills, candidate skills, job skills | Admin, Management, HR, Team Lead |
| Applications | Admin, Management, HR, Team Lead |
| Placements | Admin, Management, HR, Team Lead |
| Invoices, lines, payments | Admin, Management |
| Overview report | All five, with extra branching |
| HR report | Admin, Management, HR, Team Lead |
| Sales report | Admin, Management, Sales |

Views with only `IsAuthenticated`: user viewset (custom checks inside), client contacts, client activities, sales opportunities, interviews.

### Domain behavior that was inspected

Business codes go through `next_business_code` (`select_for_update` on `CodeSequence`). Formats match the brief for JD (`SW-JD-` width 4) and candidate (`SW-CAN-` width 5). Clients use `SW-CLI-` width 4. Applications use `SW-APP-` width 5. Invoices use `SW-INV-{year}-` width 4. Disposable SQLite produced `SW-CLI-0001`, `SW-JD-0001`, `SW-CAN-00001`, and `SW-INV-2026-0001`.

Client owner history is appended in the view on create and when Admin or Management changes `sales_owner`. Job status history is appended on create and when `status` changes. Application history is appended on create and in `change-status` only. None of these histories are exposed as their own read API. The UI does not show them.

`change-status` accepts any value in the enum. It does not consult the previous status.

Matching weights are the approved numbers, then the function crashes (section I, C1) before a score is returned. Alias and weight fields are not inputs to the formula. Responsibility score copies the skill score. A missing mandatory skill caps the total at 49 and is returned as `missing_mandatory_skills`. Application status is not updated by the matcher.

Billing outstanding is `total - sum(payments) - sum(credit notes)` on the model. Payment status updates do not use the credit-note term. Credit notes have no viewset.

### Admin

Most models use `admin.site.register([...])` with Django's default form. `UserAdmin` adds employee code, role, phone, and company join date. It does not show `department`. Sequence rows are editable. This is enough to type data in development and is not an operational admin (no list filters, no inlines, no protection of issued codes).

### N+1 and transactions

Several list views use `select_related` / `prefetch_related` (clients, jobs, candidates, applications, invoices). Invoice `paid_amount` and `outstanding_amount` each run an aggregate per instance, so an invoice page is still query-heavy. Matching calls `iterator()` on a prefetched queryset, which is both a crash and, if rewritten poorly, an N+1. Payment and invoice line saves are not wrapped in a transaction with a row lock. Code allocation is transactional; the following insert of the business row is a separate transaction unless the caller already opened one.

## D. Frontend audit

Stack that is actually installed: React 18, React Router 6, Axios, Vite 6, TypeScript 5.7, `lucide-react`. No Tailwind, no test library, no ESLint config, no `package-lock.json` in git.

Routing (`App.tsx`): unauthenticated users are sent to `/login` when `localStorage.access` is missing. Nested routes under the shell: dashboard, clients, jobs, candidates, applications, reports. Unknown paths redirect home. The gate does not read the JWT expiry or the user's role.

`services/api.ts` sets `Authorization: Bearer` from `localStorage`. `login()` stores `access` and `refresh`. Nothing reads `refresh`. There is no response interceptor.

| Screen | What it calls | What a user cannot do |
| --- | --- | --- |
| Login | `POST /auth/token/` | Refresh, see why a 401 happened beyond a fixed sentence |
| Dashboard | `GET /reports/overview/` | Filter, hide revenue for HR |
| Clients | `GET/POST /clients/`, `GET /users/` | Edit, contacts, activities, status, ownership |
| Jobs | `GET/POST /jobs/`, `POST /jobs/{id}/match/` | Assign recruiters, set skills, edit status. Match cannot succeed until C1 is fixed |
| Candidates | `GET/POST /candidates/`, upload resume | Notes, consent, duplicate review, download via a signed URL |
| Applications | `GET/POST /applications/` | Change status, see names instead of UUIDs |
| Reports | `GET /reports/hr/`, `GET /reports/sales/` | Filters; errors are swallowed; body is `JSON.stringify` |

Build results in this audit:

| Command | Exit | Result |
| --- | --- | --- |
| `npm install` in `frontend/` | 0 | 100 packages added. Lockfile appeared as an untracked file and was deleted so the repo stayed docs-only. |
| `npm run build` (`tsc -b && vite build`) | 1 | `src/services/api.ts(2,45): error TS2339: Property 'env' does not exist on type 'ImportMeta'.` Vite did not run. |
| `npx tsc --noEmit` | 2 | Same error. |
| `npx vite build` | 0 | `dist/index.html` 0.36 kB, CSS 6.16 kB, JS 249.27 kB. Bundle only. `dist/` is gitignored and was removed afterward. |

Cause of the type error: `tsconfig.json` does not include Vite's client types, and there is no `src/vite-env.d.ts` with `/// <reference types="vite/client" />`. `import.meta.env.VITE_API_URL` is therefore illegal to `tsc`. Vite's bundler accepts it.

The UI was not opened in a browser. No dev server was started, because the API had no database.

## E. Database audit

There is **no** `migrations` package under any app in git. Django will not consider those apps when `makemigrations` is run without labels.

Commands:

| Command | Exit | Output that matters |
| --- | --- | --- |
| `manage.py makemigrations --check --dry-run` | 0 | RuntimeWarning: PostgreSQL connection refused. Then `No changes detected`. This is a false pass. |
| `manage.py makemigrations --dry-run <every model app label>` | 0 | Plans `0001_initial` for organizations, accounts, audit, candidates, clients, jobs, matching, sales, applications, interviews, placements, recruitment, billing. Does not write files when `--dry-run` is set. Confirmed the repo still had no `migrations` directories afterward. |
| Disposable copy: `makemigrations` then `migrate` on SQLite | 0 | All of those migrations applied, plus Django contrib migrations. |

SQLite success is evidence that the model graph has no import cycle and that Django can emit the constraints below. It is **not** evidence that PostgreSQL accepts the SQL. Phase 2 should generate the committed `0001` against PostgreSQL and then stop rewriting it. Do not keep `makemigrations` in the container command after that; editing a shipped `0001` in place will break every database that already applied it.

Constraints Django put into that disposable `0001` (so they are real model metadata, not just comments):

- Candidate indexes on `normalized_email`, `normalized_phone`, `location`.
- `unique_candidate_resume_version`, partial unique `one_primary_resume_per_candidate`.
- Job indexes on `(status, created_at)`, `(client, status)`, `(sales_owner, status)`.
- Checks `job_experience_range_valid`, `job_salary_range_valid`. Unique `(job, recruiter)`.
- Unique `(candidate, skill)`. Unique `(job, skill)`. Check skill weight 1–10.
- Unique `(match_run, candidate)`. Check overall score 0–100.
- Unique `(candidate, job)`. Check application match score null or 0–100. Indexes on `(job, status)`, `(recruiter, status)`, `(candidate, status)`.
- Check placement amounts `>= 0`.
- Check payment amount `> 0`. Check credit-note amount `> 0`.

Not constrained, and called out because the rules need them later:

- No unique on normalized email or phone (blanks must stay allowed; a partial unique is the likely shape, and the exact rule is still an open question for how review interacts with insert).
- No unique file hash.
- No single primary contact per client.
- No check that invoice `total` equals the sum of lines.
- No check that payments plus credits do not exceed `total`.
- Skill aliases are unstructured JSON, not a table, and not unique across skills.
- `Placement` has no default ordering.
- Several major child tables are bigint PKs (section A).

`on_delete=PROTECT` is used for users on most business FKs, so deleting a user who owns history will fail. The user API deactivates instead of deleting, which matches "records survive departure" for the user row. Candidate and client viewsets still expose hard delete. Client delete is blocked once a job exists (`PROTECT` from job to client). Candidate delete cascades resumes.

Code sequences are not rebuilt from `COUNT(*)`. That part of the design matches the brief. Concurrency was not tested. PostgreSQL `select_for_update` was not executed.

## F. API and integration audit

Base path `/api/v1/`. Authentication: `POST /auth/token/`, `POST /auth/token/refresh/`.

Routers (all `DefaultRouter`, so list/detail plus a trailing slash, plus the format suffix):

| Prefix | Notes |
| --- | --- |
| `/users/` | Admin writes. Others read themselves, except Admin, Management, Team Lead read everyone. |
| `/clients/`, `/client-contacts/`, `/client-activities/` | |
| `/sales-opportunities/` | |
| `/jobs/` | Extra `POST …/assign/`, `POST …/match/` |
| `/candidates/`, `/candidate-notes/` | Extra `POST …/upload-resume/` multipart field `file` |
| `/skills/`, `/candidate-skills/`, `/job-skills/` | |
| `/applications/` | Extra `POST …/change-status/` |
| `/interviews/` | |
| `/placements/` | |
| `/invoices/`, `/invoice-lines/`, `/payments/` | |
| `/reports/overview/`, `/reports/hr/`, `/reports/sales/` | |

No routes for: departments, ownership history, job status history, assignment history, submissions, consent, credit notes, match runs as a collection, audit logs, health, OpenAPI schema.

Frontend calls only: token, users (to fill a sales-owner dropdown), clients, jobs, job match, candidates, resume upload, applications, three report URLs. It does not call refresh, assign, skills, notes, change-status, interviews, placements, or billing.

Integration defects:

- Page size 25 with no "next" control. Any list past 25 rows looks complete.
- Application list returns foreign-key UUIDs. The table prints them as the candidate and the JD.
- Match response shape is `{match_run_id, candidates_processed, results}`. The UI reads `results`. That wiring is correct and still fails because the view raises.
- Resume upload sets `Content-Type: multipart/form-data` explicitly. Axios would otherwise set the boundary itself. Worth re-testing when the API is up; it can produce a parse error if the boundary is dropped. Not probed.
- No shared error format. DRF's default `detail` string is what the client probes returned.
- CORS allows `http://localhost:5173` from the example. No credentialed cookie flow; JWT is a header, so this is consistent. Adding the Vite preview origin or an HTTPS origin will need an explicit entry.

## G. Security audit

`manage.py check --deploy` (no `.env`, so fallback secret and `DEBUG=False`) exited 0 and reported:

- `security.W004` HSTS seconds not set
- `security.W008` `SECURE_SSL_REDIRECT` is not true
- `security.W009` `SECRET_KEY` length / uniqueness
- `security.W012` `SESSION_COOKIE_SECURE` is not true
- `security.W016` `CSRF_COOKIE_SECURE` is not true

Those warnings are expected on a local debug box and are unresolved for any deployment that uses this settings module unchanged. There is no production settings split.

Issues, with the strongest evidence available:

| Issue | Evidence | Severity |
| --- | --- | --- |
| Interview feedback is readable by any logged-in user, including Sales | `GET /api/v1/interviews/` as Sales returned 200 and the feedback text | Critical |
| Resume bytes are served from `/media/` with no auth when debug is on | `urls.py` static helper gated on `settings.DEBUG`; example and Compose set `DJANGO_DEBUG=1`; serializer exposes `file`. HTTP GET not performed | Critical |
| Fallback secret is 24 bytes; PyJWT warns on HMAC-SHA256 | Token obtain for an active user printed `InsecureKeyLengthWarning` (key below 32 bytes) | High |
| Sales can create a contact on a client they do not own | `POST /api/v1/client-contacts/` returned 201 and the row existed | High |
| HR can read placement CTC, fee, and expected revenue | `GET /api/v1/placements/` as HR returned 200 with those fields. `GET /api/v1/invoices/` as the same user returned 403 | High |
| No login throttle, JWT in `localStorage`, no refresh rotation, no blacklist | Settings and `api.ts` | Medium |
| Redis published on `6379` with no password | Compose config | Medium |
| Extension-only upload check, no malware scan | `CandidateViewSet.upload_resume` | Medium |
| Audit log is never written, including for future downloads | `AuditLog` has no writers | Medium |
| Containers run as root; API is `runserver` | Dockerfiles and Compose command | Medium |
| Inactive users cannot obtain a token | `POST /auth/token/` for `is_active=False` returned 401. Existing access tokens were not timed out in a probe; SimpleJWT's authenticator checks `is_active` on each request (library behavior, not re-tested here) | Informational, positive |

Object-level authorization is the systematic gap: role lists are view-wide, and child creates trust the foreign key in the body.

Candidate consent and retention are not enforced, so the privacy requirement is unmet. That is missing functionality (section I) as well as a security gap.

## H. Testing status

Only the commands below ran. Nothing else is claimed.

| Command | Where | Exit | Exact result |
| --- | --- | --- | --- |
| `python -m compileall -q apps config manage.py` | `backend/` | 0 | `COMPILEALL_OK` |
| `python manage.py check` | `backend/` | 0 | `System check identified no issues (0 silenced).` |
| `python manage.py check --deploy` | `backend/` | 0 | 5 warnings, listed in section G. Warnings do not fail this command. |
| `python manage.py makemigrations --check --dry-run` | `backend/` | 0 | Connection-refused warning to `localhost:5432`, then `No changes detected`. False pass; see section E. |
| `python manage.py makemigrations --dry-run` plus the 14 app labels | `backend/` | 0 | Initial migration plan printed. No files written. |
| `python manage.py test -v 2` | `backend/` | 0 | `Found 0 test(s).` `Ran 0 tests in 0.000s.` `NO TESTS RAN`. `Skipping setup of unused database(s): default.` |
| `npm install` | `frontend/` | 0 | Installed. |
| `npm run build` | `frontend/` | 1 | TS2339 on `import.meta.env`. |
| `npx tsc --noEmit` | `frontend/` | 2 | Same TS2339. |
| `npx vite build` | `frontend/` | 0 | Production bundle emitted. Not a functional test. |
| `docker compose config` | repo root | 1 | `env file /workspace/.env not found` |
| `docker compose --env-file .env.example config` | repo root | 1 | Same error, because the compose file's `env_file:` is still `.env` |
| `docker compose config` after copying the example to `.env` | repo root | 0 | Resolved five services. `.env` deleted afterward. |
| `docker compose up` | — | Not run | Daemon not running. Would also generate migrations into the working tree. Intentionally skipped. |
| Frontend unit tests | — | Not run | No Jest, Vitest, Testing Library, or test files. |
| Browser / end-to-end | — | Not run | No running UI or API. |
| PostgreSQL `migrate` | — | Not run | Server not installed; port 5432 refused. |
| Celery worker | — | Not run | Redis not available on the host. |

Disposable SQLite copy (not a project test, database file `/tmp/st.sqlite3`, settings patched only in the copy):

- `migrate` applied every generated app migration.
- ORM: duplicate normalized emails both inserted; business codes formatted as above; `run_matching` raised `ValueError` and left one `MatchRun`; an invoice stored `total=1000` with zero lines; `createsuperuser`-equivalent user had `role=HR`.
- `APIClient`: superuser client-create 403; sales cross-client contact 201; inactive token 401; active sales token 200 with `access` and `refresh`; HR invoices 403; HR placements 200 including fee fields; sales interviews 200 including feedback text; job match raised `ValueError` from `JobViewSet.match`.

There is no CI configuration (no `.github/` workflows).

## I. Bugs and missing functionality

Severity is about the current starter if someone uses it with real candidate or fee data, not about polish.

### Critical

| ID | Finding |
| --- | --- |
| C1 | **Matching crashes and writes an orphan run.** `run_matching` prefetches candidate skills and calls `.iterator()` without `chunk_size`. Django 5.2.18 raises `ValueError`. The `MatchRun` insert happens first. Reproduced via ORM (run count 0 → 1) and via `POST /api/v1/jobs/{id}/match/` (exception from `jobs/views.py` line 50). A WSGI worker would respond 500. The JD screen's "Find candidates" button depends on this route. |
| C2 | **Resumes are not private in the documented dev configuration.** Debug static serving plus a stored `FileField` URL. No signed URL, no `django-storages`, no auth wrapper. Code inspection. |
| C3 | **Any authenticated user can read interview feedback.** Sales received HTTP 200 and the feedback body. The view has no `RolePermission` and no queryset filter. |
| C4 | **Schema is not in version control, and the documented boot path writes it.** Missing `migrations/` packages. Bare `makemigrations --check` exits 0. Compose runs `makemigrations` against a bind mount on every start. Two developers, or a restart after a model edit, can generate conflicting files. |

### High

| ID | Finding |
| --- | --- |
| H1 | Sales can attach a contact to another owner's client (201, row stored). Activities follow the same create path (not separately posted). |
| H2 | HR can read placement commercial fields (reproduced) and the permission class also allows writes. Invoice APIs correctly return 403 for HR. The financial-access rule is only half enforced. |
| H3 | A superuser created the usual way keeps `role=HR` and cannot create clients (403 reproduced). Several other branches key off `role` and ignore `is_superuser` (overview revenue, client update). The README tells you to sign in with that superuser. |
| H4 | Duplicate detection and the review queue do not exist. Two candidates with the same normalized email were stored. File hash is stored and never compared. Name is not used to merge, which matches the rule, because nothing merges. |
| H5 | Skill weights and aliases are ignored. Responsibility score copies the skill score. Mandatory misses cap the score at 49 instead of only flagging. Latent until C1 is fixed, then the scores are still wrong. `services.py` does not mention aliases. |
| H6 | Access tokens last 5 minutes. The UI stores the refresh token and never uses it, and it treats any stored access string as a session. |
| H7 | API pages are 25 rows. Every list screen reads `results` and stops. Data past the first page is invisible. |
| H8 | Application status can move to any enum value. PATCH can change `recruiter` and `sourced_by`, so historical attribution is not frozen. `contacted_at` is never set. The UI cannot change status at all. |
| H9 | Fallback `SECRET_KEY` is shorter than PyJWT's HMAC recommendation (warning reproduced) and shorter than Django's deploy check. The example value is 38 characters, still under the 50-character check. |
| H10 | Candidate and client destroy are the default hard delete. Resume rows cascade with the candidate. Rejected applications and resume versions are not protected from that. |
| H11 | Reports ignore every required filter and do not measure submissions, interviews, or joins. The management "dashboard" is four counts plus all-time invoice sums for finance roles. |
| H12 | `npm run build` fails typecheck (TS2339), so the documented frontend production build does not succeed. |

### Medium

| ID | Finding |
| --- | --- |
| M1 | Phone normalization is "keep digits". Country code and national format do not collide. There is no review task when they should. |
| M2 | Invoice header totals are writable and can disagree with lines (ORM: total 1000, zero lines). Payment status ignores credit notes. Payment updates compare against outstanding that already includes the row being edited. No row lock. |
| M3 | Credit notes, submissions, consent, audit, ownership history, job status history, and assignment changes have no product workflow. Some have models; submissions and credit notes have no API. |
| M4 | Worker `depends_on` backend start, not a finished migrate. No restart policy. A worker that starts too early exits. Redis is on the host port without a password. |
| M5 | `Placement` queryset is unordered. DRF `UnorderedObjectListWarning` during the HR list probe. |
| M6 | Department cannot be set from the user API or the user admin fieldsets. Team Lead can list every user. |
| M7 | Notice score is 100 when either side is null. Location score is 40 on a failed substring check. Both inflate or flatten matches. |
| M8 | No login rate limit. Tokens in `localStorage`. No CSP. |
| M9 | `.env.example` points `POSTGRES_HOST` at `db`, which breaks host `runserver` if the file is copied without edits. README describes a local venv flow and a Compose flow with the same file. |
| M10 | Multiple primary contacts allowed. Blacklisted clients are not blocked from new JDs. |
| M11 | Resume task is enqueued after the row commit. Broker failure leaves `PENDING` forever and can 500 the upload. Parser trusts the filename. No size check inside the task. |
| M12 | Applications UI shows UUIDs. Reports UI hides 403s. Nav items ignore role, so Sales opens Candidates and gets an error from the API. |
| M13 | Docker API image has no `USER`, no `CMD` healthcheck, and runs Django's development server. |
| M14 | `JobSkill.weight` and mandatory flag can be edited by any HR user on any JD. Sales, who own the JD, are not in that view's role list, and the UI never sets skills. Matching has nothing structured to score. |

### Low

| ID | Finding |
| --- | --- |
| L1 | API password minimum length 10; Django's validator default used by `createsuperuser` is 8. |
| L2 | No OpenAPI document, no structured logging, no request id. |
| L3 | UI loads Google fonts from the network at runtime. |
| L4 | No npm lockfile, so frontend installs are not reproducible. |
| L5 | Sequence numbers can gap if the business-row insert fails after the counter increments. Acceptable for ids, worth knowing. |
| L6 | Admin is the default register. Easy to edit a sequence or a generated code. |
| L7 | Interview result adds On Hold, which the brief did not list. Harmless, but it is an extra state. |
| L8 | `Payment` and invoice-line `save()` update the parent as a side effect of the ORM. Admin edits and API edits both do it, which will surprise a future data import. |

### Missing relative to the brief, even where no "bug" exists yet

Groups and permissions; signed resume URLs; S3-compatible storage; consent and retention; duplicate review; submission workflow; interviewers as people plus reschedule history; guarantee-period tracking; credit notes and refunds; report filters; Tailwind; Nginx; Gunicorn; tests; committed migrations.

## J. Recommended phased plan

Principles: do not rebuild the apps that already exist; fill them. Do not generate migrations on container start once a real `0001` is committed. Do not rewrite an applied migration; add a new one. Do not mark a phase done without tests that run on PostgreSQL. Open questions in section "Open questions" should be answered before the phase that would otherwise invent a rule (especially Phase 2 duplicates, Phase 4 HR financial visibility, Phase 6 re-application).

### Phase 1 — Foundation

**Goal:** both apps start, auth is coherent, errors are consistent, the first migration exists and is committed.

**Modify:** `backend/config/settings.py`, `backend/config/urls.py`, `backend/requirements.txt`, `backend/Dockerfile`, `docker-compose.yml`, `.env.example`, `README.md`, `frontend/src/services/api.ts`, `frontend/tsconfig.json`, `frontend/src/App.tsx`, `frontend/src/layouts/Layout.tsx`.

**Create:** `frontend/src/vite-env.d.ts`, `backend/config/asgi.py` only if an ASGI server is actually introduced (not required for Gunicorn sync), `backend/apps/accounts/management/commands/bootstrap_roles.py` (or equivalent) for Groups, a small DRF exception handler module, a health view.

**Work:** copy-example instructions that match reality; `DJANGO_SECRET_KEY` required when debug is off; JWT lifetimes explicit; Axios refresh and 401 handling; role on the login response or a `/users/me/` endpoint; remove `makemigrations` from the Compose command after Phase 2's migration is committed; add `restart` and a backend healthcheck; fix TS2339.

**Risk:** bootstrapping Groups in a command that runs every start must be idempotent. Turning off debug before media auth exists will make resume links 404; that is acceptable only if Phase 1 does not promise downloads.

### Phase 2 — Database

**Goal:** one committed initial migration (or a short series) that matches the approved rules, applied on PostgreSQL.

**Modify:** models listed below. **Create:** `migrations/0001_initial.py` (and follow-ups) only after the model edits, generated on PostgreSQL, then committed. Do not hand-edit them after any shared database has applied them.

**Model work before generating `0001`:**

- Partial unique indexes for normalized email and phone where non-blank, plus a `DuplicateReview` (name to be decided) rather than a silent unique that blocks legitimate homonyms. Depends on the open question about insert-vs-queue.
- Alias storage that the matcher can query (child table or a documented JSON contract plus a normalizer).
- `Interview` participants and an interview-event / reschedule table.
- `JobAssignment` event history, not only an `is_active` flag.
- Commercial terms if they are not solely on `Placement` (open question).
- Credit note number sequence, consistent with invoices.
- Ordering on `Placement`.
- UUID decision for child entities that the API already returns as integers (contacts, interviews, payments). Changing a PK after data exists is painful; this starter has no committed data, so Phase 2 is the time.

**Risk:** the SQLite migrate in this audit does not prove PostgreSQL. Generate there. A unique constraint on email that includes empty string will reject every candidate without an email; use a partial unique.

### Phase 3 — Django admin

**Modify:** every `admin.py`. List display, search, read-only codes, inlines for contacts, skills, lines, and history. Remove casual edits of `CodeSequence` or limit them to superusers. Add `department` to the user admin. Register nothing new that bypasses the API rules you are about to enforce; admin is an operator tool and still needs a permission story.

**Risk:** admin uses session auth and ignores `RolePermission`. An `is_staff` HR user could open invoices in admin even after the API is locked. Gate `ModelAdmin` by group in this phase.

### Phase 4 — APIs

Per module, add the missing `permissions.py`, `services.py`, `selectors.py`, and `tests/` the target layout asked for. Keep the existing viewsets; do not replace them with a second stack.

**Priority order:**

1. Fix C1, H5, and return explanation plus mandatory flags. Tests with frozen candidates.
2. Object permissions for contacts, activities, interviews, notes, skills.
3. HR financial split on placements (after the open question).
4. Application transition service; read-only attribution; history included in the serializer the UI needs (names, not only UUIDs).
5. Duplicate review API. Do not auto-merge.
6. Submission API.
7. Interview create/reschedule service.
8. Billing service: totals derived only from lines, payments and credit notes in one transaction, outstanding derived, status derived.
9. Signed download view; stop serving `MEDIA` via Django static.
10. Pagination contract documented; filters via `django-filter` or equivalent where lists need them.
11. `select_related` audits and a query-count test on the hot lists.

**Modify:** the existing `views.py`, `serializers.py`, `urls.py` in each app, plus `apps/common.py`.

**Risk:** behavior changes (403s that are 201 today) will break the thin UI. Update the UI in the same phase or hide the buttons. Do not leave "Find candidates" calling a 500.

### Phase 5 — Frontend pages

Build only against the Phase 4 contract. No dead buttons: if the API is absent, do not render the control.

**Modify:** existing feature files. **Create** feature folders for users, contacts, assignments, skills, interviews, placements, billing, settings. Add route guards from the current user's role.

Pages from the brief: login (exists), dashboard (exists, not filtered), users, clients, contacts, JDs, assignment, candidates, resume upload (partial), matching, applications, pipeline, interviews, placements, invoices, payments, HR report, sales report, management report, settings.

**Risk:** role guards in React are not authorization. Phase 4 must already enforce the same rules.

### Phase 6 — End-to-end workflows

Exercise, with automated API tests and one UI path each:

- Sales: create client, add contact, create JD, see ownership history.
- HR: assigned JD only (if that is the decision), add candidate, upload resume, resolve a duplicate, map skills, run match, open an application, move status legally, schedule and reschedule an interview, record a submission.
- Recruitment: one candidate, many JDs; rejected row remains; second active application for the same pair behaves as the answered open question.
- Billing: placement fee → invoice lines → partial payment → credit note → outstanding.
- Management: dashboard numbers match the rows just created, including after an owner change (old owner keeps historical credit).

**Risk:** doing this phase before Phase 4 freezes the wrong workflow into the UI.

### Phase 7 — Reporting

Replace the three count endpoints with query objects that take the approved filters and use historical tables (ownership history, application history, submission, interview). HR endpoint must not aggregate fees. Add tests that seed a known month and assert the totals.

**Modify:** `apps/reports/views.py`, `frontend/src/features/reports/Reports.tsx`, `frontend/src/features/dashboard/Dashboard.tsx`.

**Risk:** reporting on mutable `recruiter` FKs will lie until H8 is fixed. Phase 7 depends on Phase 4 attribution.

### Phase 8 — Testing and bug fixing

Backend: pytest or Django `TestCase` on PostgreSQL, one module at a time, including the probes from this audit (C1, C3, H1, H2, H3, H4, inactive login). Frontend: Vitest plus Testing Library for login, role redirect, and one form per module. Fix only bugs those tests catch; do not restyle.

**Create:** `backend/pytest.ini` or per-app `tests.py` / `tests/`, `frontend` test script. A CI workflow that runs `manage.py check`, `makemigrations --check` **with app labels** (or, better, fails if migrations drift after they exist), `manage.py test`, and `npm run build`.

**Risk:** `makemigrations --check` without labels will stay green even if a new app forgets its migrations package. The CI command must list labels or the apps must all have a `migrations` package.

### Phase 9 — Security review

Threat-pass the findings in section G after the fixes: resume download, interview queryset, contact object permission, placement field permissions, throttles, secret length, CORS list, debug default off, media unmounted from public URLs, audit rows for downloads and billing, consent gate if the business requires it, retention job. Re-run `check --deploy` against a production settings module and record the remaining warnings that a reverse proxy is expected to cover (HSTS, redirect).

**Risk:** a checklist that is not re-tested will drift. Each item needs the test from Phase 8.

### Phase 10 — Production preparation and docs

Gunicorn in the backend image, Nginx (or the platform proxy) for TLS, static, and media denial. Non-root user. No bind-mount of source. No `runserver`. Private S3-compatible bucket, signed URLs with a short TTL, local filesystem storage behind the same download view in development. Backups for PostgreSQL and the object store. Update `README.md` so it no longer claims `.env` is committed or that a full integration build was impossible; point operators at this audit's successor runbook.

**Modify:** `backend/Dockerfile`, `docker-compose.yml`, new `deploy/` or `nginx/` config, `README.md`.

**Risk:** switching storage changes resume URLs already saved in `FileField`. Do it before real files exist, or write a one-time path migration.

### Suggested sequence

Phase 1 and Phase 2 are blockers. Phase 3 can overlap the end of Phase 2. Phase 4 before Phase 5 for each module; do not wait to finish every API before starting the first page, but do not build a page against a 500. Phase 6 after the sales, HR, and billing slices of Phase 4–5. Phase 7 after attribution is frozen. Phase 8 should start in Phase 1 with a single smoke test and grow; it is listed late because the bulk of the suite lands after behavior exists. Phase 9 and 10 last.

## K. Commands to run the existing app

These are the commands the repository documents, plus the corrections this audit found. They were **not** all executed here. Section H lists what was executed.

### Docker Compose (intended path)

```bash
cp .env.example .env
# Edit DJANGO_SECRET_KEY. POSTGRES_HOST=db is correct for Compose
# and wrong for a venv on the host.
docker compose up --build
```

Then open `http://localhost:5173`, `http://localhost:8000/api/v1/`, and `http://localhost:8000/admin/`.

```bash
docker compose exec backend python manage.py createsuperuser
```

Set that user's SynfoTalent role to `ADMIN` in Django admin before using the React client-create form. The default role is `HR`, and client create returns 403 (H3).

The first backend start will write migration files into `backend/` because of the Compose command. Review them before committing. Expect "Find candidates" to fail until C1 is fixed. Expect resume links under `/media/` to be fetchable without a token while `DJANGO_DEBUG=1`.

`docker compose config` fails until `.env` exists.

### Host-side backend

Needs PostgreSQL and Redis on the host, not the Compose hostnames.

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export DJANGO_SECRET_KEY=replace-with-a-long-random-string
export DJANGO_DEBUG=1
export DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
export POSTGRES_DB=synfotalent
export POSTGRES_USER=synfotalent
export POSTGRES_PASSWORD=synfotalent_dev_password
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export CELERY_BROKER_URL=redis://localhost:6379/0
export CELERY_RESULT_BACKEND=redis://localhost:6379/1
python manage.py makemigrations accounts organizations clients sales jobs candidates applications recruitment interviews placements billing matching audit
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Worker, after Redis is up:

```bash
celery -A config worker -l info
```

`makemigrations` without those labels will print `No changes detected` and create nothing (reproduced).

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Dev server listens on `0.0.0.0:5173` (`package.json`). `npm run build` currently exits 1. `npx vite build` exits 0 and still does not typecheck.

### Diagnostics used in this audit

```bash
python manage.py check
python manage.py check --deploy
python manage.py makemigrations --check --dry-run
python manage.py test -v 2
npm run build
npx tsc --noEmit
npx vite build
docker compose config
```

## L. Estimated work remaining

This is scope, not a calendar.

The starter is a wide skeleton: 14 Django apps, models for almost every business noun, thin CRUD for most of them, and six React screens. The completion bar in `DEVELOPMENT_STATUS.md` is unmet everywhere. Remaining work is not a rewrite. It is concentrated in:

- **Runtime blockers (Phase 1–2):** env story, committed PostgreSQL migrations, container command, TypeScript build, JWT refresh. Small surface, high leverage. A handful of files, plus the first migration series.
- **Correctness blockers (Phase 4, first slice):** matching crash and scoring rules, object permissions, HR financial fields, duplicate review, application transitions. This is the largest backend slice. Every existing `views.py` is touched; several new service and test modules are created.
- **Missing product surface:** submission workflow, interview history, credit notes, consent, audit writers, all unbuilt screens (users through settings). Roughly as much UI as already exists, again, for the missing modules, and the existing screens need a second pass (UUIDs, pagination, roles).
- **Proof (Phase 6–8):** there are zero tests today. The suite has to be created, including the probes already reproduced in this audit so they cannot regress.
- **Production (Phase 9–10):** storage, signed URLs, Gunicorn, Nginx, secrets, backups. No code for this exists yet.

Until Phase 4 fixes C1, H1, H2, and H4, the system should not hold real resumes or fee data. The models are a usable base. The behavior on top of them is not yet the approved process.

## Open questions

These were not answered by the code or the README. They are not decided by this audit.

1. After Rejected or Withdrawn, may the same candidate have another application on the same JD? The table allows only one row forever.
2. Who may create a JD: Sales only, or also HR and Team Lead? The API allows all three, plus Admin and Management.
3. Does HR see every JD, or only assigned JDs?
4. Does Blacklisted block new JDs and submissions, or is it a label only?
5. Is Team Lead an HR lead, a sales lead, or both? The role can assign recruiters and read placements, and cannot open the sales report.
6. Are offered CTC, fee, and expected revenue on a placement "financial" and therefore hidden from HR, or is the restriction only invoices and payments?
7. Is the currency INR (the UI prints ₹)? Is tax GST with a breakup, and is a percent fee applied to annual CTC?
8. Do commercial terms live on the client, the JD, the placement, or all three?
9. Who approves a duplicate merge, and which candidate id survives?
10. Is consent required before a candidate row or a client submission may be stored?
11. What is the retention period, and which privacy law applies? The repo does not say.
12. Are responsibilities structured rows, or text to be scored from the JD and the resume? Today the 15-point factor is a copy of the skill score.
13. Are interviewers users, free text, or both?
14. May the sales owner of a JD see candidate names and interview feedback for that JD?
15. Must a client have exactly one primary contact?
16. Is `SW-INV-{year}-0001` acceptable as the statutory invoice number?
17. Should `is_superuser` bypass role checks, or must every account, including the first administrator, have an explicit role?
18. Is hard delete forbidden for clients, candidates, and applications, with deactivation as the only path?

## Files added by this audit

- `AUDIT_REPORT.md`
- `DEVELOPMENT_STATUS.md`
- `CHANGELOG.md`

No other repository files were intentionally changed.
