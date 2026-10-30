# SynfoTalent development status

Updated after Phase 1 (foundation) and Phase 2 (database), 2026-10-30. Phase 3 and later have not been started.

**Completion rule:** a product feature is complete only when backend behavior, frontend integration, and tests have all been verified. Foundation and schema work can be in place without the feature being complete.

**Tests that ran**

| Command | Result |
| --- | --- |
| `python manage.py test apps` against PostgreSQL 16 | 30 tests, OK, 0 failures |
| `python manage.py check` | No issues |
| `python manage.py makemigrations --check --dry-run` | No changes |
| `python manage.py migrate` on the dev database | Applied |
| `npm run build` (`tsc -b && vite build`) | Exit 0 |
| Host `runserver` on 127.0.0.1:8000 and Vite on 127.0.0.1:5173 | Health `200` `{"status":"ok","version":"v1"}`. `/media/resumes/secret.pdf` is `404`. Vite `/login` is `200`. A live superuser create without consent is `400`; with consent it is `201` and `SW-CAN-00001`. |
| `docker compose up` | Not run. The Docker daemon was not running in this environment. |
| Browser click-through of the consent form | Not run. The candidate form includes the new fields; the API consent rule is covered by tests. |
| Frontend unit tests | None exist. |

The 30 tests cover health and API versioning, the error envelope, inactive login, token refresh, superuser bypass, group bootstrap (including "do not reset edits"), HR having no finance permissions, client scoping and the contact ownership check, commercial-term override, JD visibility and assignment permissions, sales being refused `run_match`, re-apply after rejection, the joined application still holding the active slot, frozen recruiter/status on PATCH, consent, duplicate review without a merge, retention settings, business codes, credit-note numbers, skill-alias uniqueness, interview reschedule history, and sales being refused interview reads.

---

## 1. Platform, configuration, and local runtime

- **Module name:** Platform / configuration / Docker
- **Current implementation status:** Foundation is in place and verified on the host against PostgreSQL. Compose was updated and not booted here.
- **Completed features:** None under the full product rule. Verified foundation: committed migrations, container command runs `migrate` and `bootstrap_groups` only, `.env.example` uses `POSTGRES_HOST=localhost` while Compose overrides the database host and Redis URLs, debug-off refuses a missing or `dev-only-` secret, `/media/` is not mounted, `/api/v1/` is versioned, errors use one JSON shape, `/api/v1/health/` checks the database.
- **Pending features:** Gunicorn, Nginx, non-root images, a proven `docker compose up`, S3 storage, signed downloads.
- **Known bugs:** Worker and backend images still run as root and the API process is still `runserver`. Redis is still published without a password.
- **Tests executed:** `manage.py check`, `makemigrations --check`, `migrate`, `test apps` (health, version, media 404, error shape).
- **Tests passed:** Those commands. 30/30 in the suite.
- **Tests failed:** None.
- **Security issues:** Dev secret is intentionally refused when debug is off. Production HTTPS settings are still unset. Media is private only because it is not served; there is no authorized download yet.
- **Next development tasks:** Phase 4 download endpoint, then Phase 10 process model. Do not put `makemigrations` back in the container command.

## 2. Accounts and authentication

- **Module name:** Accounts and authentication
- **Current implementation status:** Partial. Permissions and JWT refresh exist on the backend and are tested. The React client stores the refresh token and retries once on 401. That interceptor was not exercised in a browser.
- **Completed features:** None under the full product rule.
- **Pending features:** Password reset, self-service password change, token blacklist, a user-admin screen. Groups are editable in Django admin, not in the React app.
- **Known bugs:** Access tokens last 30 minutes (`SIMPLE_JWT`). The UI still treats a stored access token as a session until a request fails. `bootstrap_groups` assigns the role's group on save; extra groups are kept.
- **Tests executed:** Inactive token 401, refresh 200, `createsuperuser` role `ADMIN`, superuser with role HR can create a client and list invoices, `GET /users/me/`, bootstrap does not restore a removed HR permission.
- **Tests passed:** All of the above, inside the 30-test run.
- **Tests failed:** None.
- **Security issues:** No login throttle. Tokens stay in `localStorage`. Inactive users cannot obtain a token (tested).
- **Next development tasks:** Phase 5 user screen. Phase 9 throttle and cookie/session review.

## 3. Organizations

- **Module name:** Organizations
- **Current implementation status:** Partial. Department and `CodeSequence` remain. `SystemConfiguration` is the single retention and privacy-notice row. `GET`/`PATCH /api/v1/system-configuration/` is permission-gated. There is a small Django admin form for the same row. No retention number is hardcoded.
- **Completed features:** None under the full product rule. The settings API and sequence helper are tested on the backend only.
- **Pending features:** Department API and UI. A job that actually deletes or archives data when a retention value is set. Frontend settings page.
- **Known bugs:** None found in the sequence or singleton tests. A second configuration row hits the unique `singleton` flag.
- **Tests executed:** Null retention until PATCH, HR 403, management can set 400 days, `SW-JD` / `SW-CAN` sequence values, credit-note number prefix.
- **Tests passed:** Yes, in the suite.
- **Tests failed:** None.
- **Security issues:** Only `organizations.view_systemconfiguration` and `change_systemconfiguration` can read or edit the row. HR does not have those by default.
- **Next development tasks:** Phase 7/9 retention enforcement. Do not invent a default period in code.

## 4. Clients and contacts

- **Module name:** Clients, contacts, ownership history, activities
- **Current implementation status:** Partial. Permission checks replaced role strings. Sales see their own clients. A sales user cannot add a contact to someone else's client (tested). Client commercial defaults exist.
- **Completed features:** None. The client list/create screen does not manage contacts, activities, or commercial terms.
- **Pending features:** Contact UI, ownership-history UI, blacklist behavior (still not specified as a hard block).
- **Known bugs:** Several primary contacts are still allowed. Company names are not unique.
- **Tests executed:** Cross-owner contact 403, own contact 201, sales list scoped to owned clients, assigning an HR user as owner returns 400.
- **Tests passed:** Yes.
- **Tests failed:** None.
- **Security issues:** The previous contact IDOR for sales is covered by a test. Users with `clients.view_all_clients` (HR, management, admin by default) can still see every client.
- **Next development tasks:** Phase 5 contact UI. Phase 4 any remaining child-object checks that tests do not hit (activities follow the same visible-client rule and were not separately requested).

## 5. Sales

- **Module name:** Sales opportunities
- **Current implementation status:** Partial. API uses model permissions and `view_all_salesopportunity` for the full list. No frontend.
- **Completed features:** None.
- **Pending features:** Opportunity UI, stage history.
- **Known bugs:** No automated test calls the opportunity API. Expected value is visible to anyone with `view_salesopportunity`. Sales have that permission for their own rows; management has the view-all permission.
- **Tests executed:** None specific. The module loads and migrates with the suite.
- **Tests passed:** n/a for this module.
- **Tests failed:** None.
- **Security issues:** Grant `view_salesopportunity` only to people who should see expected value.
- **Next development tasks:** Phase 4 tests and Phase 5 UI.

## 6. Jobs

- **Module name:** Jobs, assignments, status history
- **Current implementation status:** Partial. Create/view/assign are permission-based. Assignment writes `JobAssignmentHistory`. JD fee fields override client defaults (tested). `POST …/match/` is still broken.
- **Completed features:** None. The JD screen can create a row and still calls match, which fails.
- **Pending features:** Fix matching (Phase 4). Unassign. Assignment UI. Skill capture on the JD form.
- **Known bugs:** **C1, deferred.** `apps/matching/services.py` calls `queryset.iterator()` after `prefetch_related()` without `chunk_size`. Django 5.2 raises `ValueError` and the match run row is created first. Not changed, because the crash is not in the model layer. Sales receive 403 on match (tested) because they lack `jobs.run_match`. HR has `run_match` and will hit the crash.
- **Tests executed:** HR cannot see an unassigned JD (404). Team lead can. Assigning HR writes success. Assigning a sales user returns 400. Sales match returns 403. Commercial override unit behavior.
- **Tests passed:** Yes.
- **Tests failed:** None. Match success was not tested, on purpose.
- **Security issues:** Match, once fixed, still returns candidate names to whoever has `jobs.run_match`.
- **Next development tasks:** Phase 4 matcher: pass `chunk_size` or drop `iterator()`, score weights and `SkillAlias`, do not leave an orphan run on failure.

## 7. Candidates and resumes

- **Module name:** Candidates, resumes, notes, consent
- **Current implementation status:** Partial. A profile cannot be stored without consent and a privacy-notice version (database check, model `save`, and API). The candidate form sends both. Duplicate email/phone opens a `DuplicateReview` and does not merge. File-hash reviews are queued on upload. Resumes are not publicly served.
- **Completed features:** None. There is no download, no review screen, and upload was not retested against a live Celery worker.
- **Pending features:** Signed download, malware scan, review UI, actual merge, consent withdrawal API.
- **Known bugs:** Phone normalization is still "keep digits", so `+91…` and a national number do not match. Empty email and phone do not open a review (tested). Upload still calls Celery after the row is saved.
- **Tests executed:** ORM create without consent raises, API without consent is 400, API with consent is 201 and writes `CandidateConsent` plus `SW-CAN-…`, notice-version mismatch is 400, approve leaves both rows and writes an audit row with `records_merged: false`, a user stripped of `review_duplicate` cannot decide.
- **Tests passed:** Yes.
- **Tests failed:** None.
- **Security issues:** Files sit on disk with no public URL and no authorized URL. Anyone with `review_duplicate` (every default role group) may approve a review. That matches the owner's rule. The decision does not merge data.
- **Next development tasks:** Phase 4 review API and download. Phase 5 review screen. The form checkbox was not clicked in a browser in this run.

## 8. Skills and matching

- **Module name:** Skills and rule-based matching
- **Current implementation status:** Models migrated, including `SkillAlias`. The scorer is unchanged and still crashes. No skill UI.
- **Completed features:** None.
- **Pending features:** Use aliases and weights. Score responsibilities from real data. Return the explanation. Fix C1.
- **Known bugs:** C1, described under Jobs. Alias JSON and `SkillAlias` are both stored. The service reads neither.
- **Tests executed:** Two aliases that normalize to `js` violate the unique constraint.
- **Tests passed:** Yes.
- **Tests failed:** None.
- **Security issues:** Same as the match endpoint.
- **Next development tasks:** Phase 4 only. Do not call the engine done.

## 9. Applications and pipeline

- **Module name:** Applications and pipeline
- **Current implementation status:** Partial. One active row per candidate and JD. `REJECTED` and `WITHDRAWN` release the slot and stay in the table. `JOINED` does not release it. Status and recruiter are not writable through PATCH. The screen can still create a row and still shows ids, with no status buttons.
- **Completed features:** None under the full product rule. The re-apply rule is tested through the API.
- **Pending features:** Pipeline UI that calls `change-status` and shows names. Legal transition map (any status is still accepted by `change-status`).
- **Known bugs:** `change-status` does not restrict the graph. A client can jump from Identified to Joined. Tested only as "joined still blocks a second row", not as a forbidden jump.
- **Tests executed:** Create ignores a submitted `JOINED` status and stores Identified. Reject then create a second application. A third active row is 400. Joined plus another create is 400. PATCH cannot change recruiter or status.
- **Tests passed:** Yes.
- **Tests failed:** None.
- **Security issues:** Anyone with `applications.change_application` can set any status. HR and team lead have that permission by default.
- **Next development tasks:** Phase 4 transition service. Phase 5 pipeline board.

## 10. Recruitment submissions

- **Module name:** Client submissions
- **Current implementation status:** Model only, now with a UUID primary key. No API and no UI.
- **Completed features:** None.
- **Pending features:** Submission workflow.
- **Known bugs:** None executed.
- **Tests executed:** Table is created by migrate. No behavior test.
- **Tests passed:** n/a.
- **Tests failed:** None.
- **Security issues:** None beyond the missing feature.
- **Next development tasks:** Phase 4.

## 11. Interviews

- **Module name:** Interviews
- **Current implementation status:** Partial. UUID primary key, participant rows, and an event row on create and on date/result change. The API requires `interviews.view_interview`. Sales do not have it by default.
- **Completed features:** None. No interview screen. Participants have no API.
- **Pending features:** Participant API, reschedule UI, linking a result to the application without auto-reject.
- **Known bugs:** Interviewer is still a free-text field plus an unused participant table. `ON_HOLD` remains an extra result.
- **Tests executed:** Creating an interview writes `CREATED`. Changing the date writes `RESCHEDULED`. Sales `GET /interviews/` is 403. HR receives 200 and the feedback text.
- **Tests passed:** Yes.
- **Tests failed:** None.
- **Security issues:** The old "any logged-in user can read feedback" hole is closed for the default sales group. Anyone later granted `view_interview` or `view_all_interviews` can read feedback. That is the permission model.
- **Next development tasks:** Phase 4 participant API. Phase 5 UI.

## 12. Placements

- **Module name:** Placements
- **Current implementation status:** Partial. List is ordered. Commercial fields are removed from the JSON unless the user has `placements.view_placement_financials`. Writes of those fields require `change_placement_financials`. HR has `view_placement` only.
- **Completed features:** None. No placement screen.
- **Pending features:** Copy effective client/JD terms into the placement instead of the field default of 90 guarantee days. That 90 is still on the model and is not the retention setting.
- **Known bugs:** Expected revenue is still whatever the client sends. HR cannot see the amounts and also cannot create a placement, because create requires the financial permission in the serializer and HR lacks `add_placement`.
- **Tests executed:** HR detail response omits CTC, fee, and revenue and still shows status. HR invoice list is 403. Management sees `1200000.00` and `100000.00`.
- **Tests passed:** Yes.
- **Tests failed:** None.
- **Security issues:** Finance visibility is permission-based. Grant the two placement financial permissions explicitly. They are on Management and Administrator by default, not HR.
- **Next development tasks:** Phase 4 fee calculation. Phase 5 UI.

## 13. Billing

- **Module name:** Billing
- **Current implementation status:** Partial. Invoice, line, payment, and credit-note rows use the permission tables. HR is 403 on invoices. A credit note number is sequenced (`SW-CN-{year}-`). Header totals must be non-negative. There is still no credit-note API and no billing UI.
- **Completed features:** None.
- **Pending features:** Credit-note endpoints, deriving totals only from lines, payment/credit races, tax configuration.
- **Known bugs:** Header totals can still disagree with lines (no new test). Payment status still ignores credit notes. Those stayed out of Phase 2 on purpose.
- **Tests executed:** HR cannot list invoices. Management can. A management user whose groups are cleared is 403 until `billing.view_invoice` is granted directly, while `role` stays `MANAGEMENT`. Credit-note number prefix via the ORM.
- **Tests passed:** Yes.
- **Tests failed:** None.
- **Security issues:** Invoice access is no longer a hardcoded role list. The role label alone does not grant it (tested).
- **Next development tasks:** Phase 4 billing service inside a transaction.

## 14. Reports

- **Module name:** Reports
- **Current implementation status:** Partial. The three endpoints now require report permissions. Financial figures are zero unless `reports.view_financial_report` is held. Filters are still absent. The React page is still a JSON dump.
- **Completed features:** None.
- **Pending features:** Every approved filter and the productivity definitions.
- **Known bugs:** Counts are still all-time. The page still swallows 403s.
- **Tests executed:** HR overview returns `invoiced_revenue` 0.
- **Tests passed:** Yes, that assertion.
- **Tests failed:** None.
- **Security issues:** HR has overview and HR report permissions, not the sales report and not financial figures.
- **Next development tasks:** Phase 7, after attribution is trustworthy.

## 15. Audit, privacy, and consent

- **Module name:** Audit and privacy
- **Current implementation status:** Partial. Consent is required to store a candidate. Retention is a nullable admin setting. Duplicate decisions write `AuditLog`. Most other actions still do not.
- **Completed features:** None.
- **Pending features:** Audit of reads and billing. Consent withdrawal. Retention deletion. Privacy-notice screen.
- **Known bugs:** Audit coverage is only the duplicate decision path.
- **Tests executed:** See candidates and system configuration.
- **Tests passed:** Yes.
- **Tests failed:** None.
- **Security issues:** Resume reads cannot be audited until a download endpoint exists.
- **Next development tasks:** Phase 9.

## 16. Frontend shell

- **Module name:** Frontend
- **Current implementation status:** Partial. `npm run build` succeeds. Axios refreshes the access token once after a 401. The candidate form requires consent and a notice version. Tailwind is still not installed. No component tests.
- **Completed features:** None.
- **Pending features:** The Phase 5 page list. Role-aware navigation. Pagination controls. Hiding Match for users without `jobs.run_match`.
- **Known bugs:** Match button still calls the broken endpoint for users who have the permission. Applications still show raw ids. Reports still render JSON.
- **Tests executed:** `npm run build` exit 0. No browser session. No Vitest.
- **Tests passed:** The production build.
- **Tests failed:** None in that command.
- **Security issues:** Tokens remain in `localStorage`.
- **Next development tasks:** Phase 5, after Phase 4 stops the match crash.

---

## Cross-check

| Area | Backend | Frontend wired | Automated tests | Complete |
| --- | --- | --- | --- | --- |
| Boot, versioning, errors, health | Yes | Build passes; health is not a page | Yes | No |
| Groups and permissions | Yes | No admin UI | Yes | No |
| JWT refresh | Endpoint yes | Interceptor written, not browser-tested | Endpoint yes | No |
| Clients and commercial defaults | Yes | List/create only | Yes for scope, contact denial, terms | No |
| JD assignment and visibility | Yes | Create and match button | Yes, except a successful match | No |
| Consent and duplicate review | Yes | Consent fields on the form | API and model yes; browser no | No |
| One active application | Yes | Create only | Yes | No |
| Interviews | Yes, sales blocked | No page | Yes | No |
| Placement and invoice visibility | Yes | No pages | Yes | No |
| Retention settings | Yes | No page | Yes | No |
| Matching engine | Crashes (C1) | Button calls it | Alias uniqueness only | No |
| Submissions, billing workflows, filtered reports | Missing or model-only | No | Little or none | No |
