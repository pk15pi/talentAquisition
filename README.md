# SynfoTalent

Recruitment management system for Synfowebs. Django REST Framework, PostgreSQL 16, React, Redis, and Celery.

The GitHub default branch is **`master`**. `main` exists and points at the same commit as `master` when packaging landed. Open pull requests against `master`. Phases 0–5 are on `master`. This branch keeps the unmerged production packaging (Gunicorn, Nginx, non-root images, private resumes) and stacks the completion work on it. Do not merge it without review.

## What is running today

- Accounts, organizations, clients, sales opportunities, jobs, candidates, skills, matching, applications, submissions, interviews, placements, billing, and reports.
- Django admin for those modules, gated by Django permissions. HR does not get invoice, payment, or placement-fee permissions, and does not get `candidates.view_resume_content` by default.
- React workspace: login, dashboard, users, clients, opportunities, job descriptions, candidates, duplicate review, applications, interviews, submissions, placements, billing, reports, and settings.
- Resume files are private. `/media/` is not a public route. An authorized user with `candidates.view_resume_content` calls `POST /api/v1/resumes/{id}/download/` and then opens the short-lived `/api/v1/resume-downloads/?token=` path. With `AWS_STORAGE_BUCKET_NAME` set, that path redirects to a short-lived object-storage URL. HR and Management do not have the permission by default.
- React also has an opportunities screen. Duplicate review can approve without merging, or merge into a chosen surviving profile. Candidates can withdraw recorded consent. Retention runs from Celery beat when an administrator has set a period.

This is deployable as a process. It is not a finished ATS. The gaps are listed at the end of this file.

## Local development

Docker is optional. `.env` is not committed.

```bash
cp .env.example .env
```

Keep `DJANGO_DEBUG=1` on a laptop. The sample secret starts with `dev-only-` and is refused when debug is off.

### Docker Compose (development)

`POSTGRES_HOST=localhost` in `.env` is for Django on the host. Development Compose overrides it to the `db` service and points Celery at `redis://redis:6379`. Redis is published on port 6379 **without a password** for that laptop broker. Do not expose that port on a shared machine.

```bash
docker compose up --build
```

The backend container runs `migrate` and `bootstrap_groups`, then `runserver`. It does not run `makemigrations`. The frontend container is the Vite dev server on port 5173, running as the `node` user. The API container runs as uid 1000.

- App: http://localhost:5173
- API: http://localhost:8000/api/v1/health/
- Admin: http://localhost:8000/admin/

```bash
docker compose exec backend python manage.py createsuperuser
```

`createsuperuser` sets role `ADMIN`. Active superusers bypass permission checks.

### Host processes

PostgreSQL must be reachable at `POSTGRES_HOST`.

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py bootstrap_groups
python manage.py createsuperuser
python manage.py runserver
```

Celery, with Redis on localhost:

```bash
celery -A config worker -l info
```

Frontend:

```bash
cd frontend
npm ci
npm run dev
```

`npm run build` typechecks with `tsc -b` and builds the Vite bundle. `npm test` runs Vitest.

### Groups

A new user is placed in Administrator, Management, Sales Executive, HR Executive, or Team Lead when the account is created. Later saves, logins, and `bootstrap_groups` do not change membership. Add or remove groups on the user form when access should change. `bootstrap_groups --reset` restores the built-in grants on the groups themselves and still does not rewrite membership.

Team leads can see every JD. HR sees a JD after they are assigned, unless someone grants `jobs.view_all_jobs`.

## Production

Use `docker-compose.prod.yml` by itself. Do not combine it with `docker-compose.yml`. That file is the development stack and still runs `runserver`.

Production Compose:

- Runs Gunicorn in the backend container (`web`). There is no `runserver` and no `makemigrations`.
- Runs the same image for the Celery worker.
- Builds the frontend and serves `dist` with Nginx. The default API base baked into that image is `/api/v1` (same origin).
- Proxies `/api/` and `/admin/` to Gunicorn and serves `collectstatic` output from a volume.
- Returns 404 for `/media/`. The media volume is mounted only on the backend and the worker.
- Runs backend, worker, and Nginx as non-root users. Postgres and Redis are not published on the host.
- Requires `REDIS_PASSWORD` and uses it for the broker, the result backend, and the shared throttle cache.

### 1. Configure the environment

```bash
cp .env.example .env
```

Edit `.env`:

1. Generate a secret of at least 50 characters that does not start with `dev-only-`:

   ```bash
   python3 -c "import secrets; print(secrets.token_urlsafe(64))"
   ```

   Put it in `DJANGO_SECRET_KEY`. Production Compose forces `DJANGO_DEBUG=0`. A missing, short, repetitive, or `dev-only-` key refuses to boot.

2. Set `POSTGRES_PASSWORD` and `REDIS_PASSWORD` to long random values. `REDIS_PASSWORD` must be letters and digits only so it can be embedded in `redis://` URLs.

3. Set `DJANGO_ALLOWED_HOSTS` to the public hostname plus `127.0.0.1` (the container health check uses `127.0.0.1`).

4. Set `CSRF_TRUSTED_ORIGINS` to the public admin origin, including the scheme, for example `https://talent.example.com`.

5. Leave `CORS_ALLOWED_ORIGINS` empty when the browser loads the SPA from that same host. Set it only if the SPA is served from a different origin.

6. Leave `AWS_STORAGE_BUCKET_NAME` empty to store resumes on the media volume. See object storage below if you set it.

7. Leave `VITE_API_URL` as `/api/v1` for the production image. That value is **baked at image build**, not read from the container environment at runtime. A change requires a rebuild of the `web` service.

`DJANGO_DEBUG=1` in `.env` does not turn production Compose back into the dev server. The compose file forces debug off. Do not point this file at a development database that still uses the sample secret.

### 2. Build and start

```bash
docker compose -f docker-compose.prod.yml up --build -d
```

The backend entrypoint applies committed migrations, runs `bootstrap_groups`, runs `collectstatic`, then execs Gunicorn. The worker waits until those migrations are present. Neither container generates migrations.

Open `http://<host>:8080/` (or `WEB_HTTP_PORT`). Health: `http://<host>:8080/api/v1/health/`. Admin: `http://<host>:8080/admin/`.

Port 8080 in this default file is plain HTTP inside the container (host port 8080). Use it on a private network, or put TLS in front before anyone uses a real password. Admin session cookies are marked Secure when debug is off, so the admin session will not stick on plain HTTP. The JWT API still accepts `Authorization: Bearer` over HTTP, which is not appropriate for a public network.

### 3. Create the first administrator

```bash
docker compose -f docker-compose.prod.yml exec backend python manage.py createsuperuser
```

Migrations and group bootstrap already ran on startup. Run `bootstrap_groups` again only when you want to create missing groups. Pass `--reset` only when you intend to restore the built-in permission grants.

### 4. TLS

Nginx is the TLS boundary. Django does not redirect HTTP to HTTPS (`SECURE_SSL_REDIRECT` is off) because Gunicorn is on the Docker network and the health check is HTTP. Django does set HSTS and Secure cookies when debug is off, and it trusts `X-Forwarded-Proto` from the proxy.

Two supported layouts:

- **Load balancer terminates TLS.** Keep `deploy/nginx/default.conf`. Configure the load balancer to talk to the web container and to send `X-Forwarded-Proto: https`. Do not publish Gunicorn (the production file does not).
- **Nginx terminates TLS.** Mount `deploy/nginx/tls.conf.example` over `/etc/nginx/conf.d/default.conf` and mount `fullchain.pem` and `privkey.pem` at `/etc/nginx/certs/`. Publish host `80:8080` and `443:8443`. Port 8080 redirects to HTTPS except `/api/v1/health/`. The example is not selected by default so a host without certificates can still boot.

HSTS preload stays off unless `DJANGO_HSTS_PRELOAD=1`. `DJANGO_HSTS_INCLUDE_SUBDOMAINS=1` by default. Set it to `0` if this process must not pin sibling subdomains. Turning include-subdomains off makes `manage.py check --deploy` report `security.W005` again.

### 5. Deploy check

On a production-shaped environment (`DJANGO_DEBUG=0` and a real secret):

```bash
python manage.py check --deploy --fail-level WARNING
python manage.py makemigrations --check --dry-run
```

`check --deploy` is expected to silence two warnings and fail on any other warning:

- `security.W008` — HTTPS redirect is Nginx's or the load balancer's job. Turning it on inside Gunicorn would redirect the container health check.
- `security.W021` — HSTS preload is opt-in.

Run that command with the production environment. A laptop `.env` with `DJANGO_DEBUG=1` will still report the debug warnings.

### 6. Backups

PostgreSQL is the system of record. Redis is the Celery broker and the throttle cache. The AOF file keeps queued tasks across a Redis restart. Do not treat Redis as a backup of candidates, invoices, or resumes.

Postgres, from the production project directory:

```bash
docker compose -f docker-compose.prod.yml exec -T db \
  pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" > "synfotalent-$(date +%F).sql"
```

Restore into an empty database with `psql`. Take a dump before applying new migrations.

Resumes, when the bucket name is empty, live in the `media_data` volume (keys under `resumes/`). Copy that volume off the host. When a bucket is set, enable versioning or replication on the bucket and back that up. The database only stores the object key.

### 7. Private resumes and object storage

Local disk and object storage share the download view. `POST /api/v1/resumes/{id}/download/` still requires `candidates.view_resume_content` and returns `/api/v1/resume-downloads/?token=`. The token lasts 5 minutes. Opening it checks the user and the permission again.

- With no `AWS_STORAGE_BUCKET_NAME`, the view streams the file from the media volume. `/media/<path>` stays 404.
- With a bucket set, the same view redirects to a presigned URL that expires in `AWS_QUERYSTRING_EXPIRE` seconds (default 300). The bucket ACL is not public. Set both `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`, or leave both empty for an instance role. `AWS_S3_ENDPOINT_URL` is the S3-compatible endpoint (MinIO, R2, and others). `AWS_S3_ADDRESSING_STYLE=path` is the usual MinIO setting.

`FileField` paths stay `resumes/YYYY/MM/<filename>`. There is no migration. If a volume already holds files, copy those keys into the bucket before setting `AWS_STORAGE_BUCKET_NAME`. Production has no candidate files yet, so a new bucket can start empty.

### 8. Login and API limits

JWT obtain, JWT refresh, and `POST /admin/login/` share the `THROTTLE_LOGIN` limit (default 30 requests per minute per IP). Other API clients use `THROTTLE_ANON` and `THROTTLE_USER`. `GET /api/v1/health/` is not throttled so the load balancer can probe it.

Production Compose sets `CACHE_URL` to Redis so the Gunicorn workers share one counter. Without `CACHE_URL`, the counter is per process (fine for `runserver`, weak for several Gunicorn workers).

## Tests

```bash
cd backend
python manage.py test apps
python manage.py check --deploy --fail-level WARNING
python manage.py makemigrations --check --dry-run
cd ../frontend
npm ci
npm run build
npm test
```

The Django commands need PostgreSQL 16. `DJANGO_DEBUG=0` needs a non-sample secret of at least 50 characters. GitHub Actions runs the Django suite, the deploy check, the migration check, and `npm run build`.

## API map

JWT:

- `POST /api/v1/auth/token/`
- `POST /api/v1/auth/token/refresh/`

`GET /api/v1/health/` does not require a token. `GET /api/v1/users/me/` returns the caller's permissions for the shell. Those permissions are not what authorizes a write. The API checks Django permissions.

Creating a candidate requires `consent_acknowledged: true` and `privacy_notice_version`. If system configuration has a notice version, the submitted version must match it. The server does not invent a consent timestamp. A rejected or withdrawn application stays on file. A new active application for the same candidate and JD is allowed. A second active row is rejected.

Resume upload: `POST /api/v1/candidates/{id}/upload-resume/` with multipart field `file` (PDF or DOCX, max 10 MB).

Matching weights are skills 40, experience 25, responsibilities 15, location 10, and notice period 10. A missing mandatory skill is flagged. The engine does not shortlist or reject anyone.

Duplicate approval does not merge. `POST /api/v1/duplicate-reviews/{id}/merge/` with `surviving_candidate_id` does. The other profile stays as an alias. Consent is not copied. Who may merge is `candidates.review_duplicate`.

`POST /api/v1/candidates/{id}/withdraw-consent/` records withdrawal only when consent was actually stored. It does not delete the profile.

Retention: `python manage.py enforce_retention`, or Celery beat (`beat` in both Compose files). A null period skips that category.

Report filters: `date_from`, `date_to`, `status`, `client`, `job`, `recruiter`, `sales_executive`, `department`, `employee`.

## Still not production-complete

- Job sales-owner changes are not stored in a history table. Client credit uses ownership history. JD credit uses the current sales owner.
- Department editing, password reset, and refresh-token blacklist are not built. The browser stores JWTs in `localStorage`.
- Resumes are not malware-scanned.
- HR was not granted placement create, placement financial fields, invoice access, or resume content. That split is unchanged.
