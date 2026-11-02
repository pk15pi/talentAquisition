# SynfoTalent final audit baseline

Date: 2026-11-02. Inspector: completion pass on `master` at `635cc4d` (merge of PR #5, Phase 5 frontend). No application code was changed for this document. A parallel cloud agent, "Production deployment prep" (`bc-64130237-fd50-5ec8-a1d1-a677d6d1757a`), was still inspecting and had not pushed a branch. Its mission is Phase 10 deploy (Gunicorn, Nginx, non-root images, prod compose, secret/CORS/throttle hardening). This baseline does not treat that uncommitted work as present.

**Completion rule** (from `DEVELOPMENT_STATUS.md`): a product feature is complete only when backend behavior, frontend integration, and tests have all been verified.

## Evidence collected in this pass

| Check | Result |
| --- | --- |
| `git rev-parse HEAD` | `635cc4d0ebd1227e3bf27987f8e1fbf1a8e4f25d` on `master` |
| `python manage.py test apps` | PostgreSQL 16.15, **82 tests, OK**, 43.2s. Host `localhost`, database `synfotalent`. |
| `npm test` (`vitest run`) | **13 tests, passed** |
| Code read | Models, services, views, admin, access lists, Phase 5 pages, `AUDIT_REPORT.md`, `DEVELOPMENT_STATUS.md`, `CHANGELOG.md` |
| Browser in this pass | Not re-run. Phase 5's headless Chrome notes in `DEVELOPMENT_STATUS.md` are prior evidence, not repeated here. |
| Deploy processes | `backend/docker-entrypoint.sh` still `exec python manage.py runserver`. No Gunicorn, no Nginx config, Dockerfiles have no `USER`. |

Prior recorded Phase 5 run (same commit's notes): `manage.py check` clean, `makemigrations --check --dry-run` clean, `npm run build` exit 0. Those three commands were not repeated before this document.

## Standing decisions that the code already follows

| Decision | Status | Evidence |
| --- | --- | --- |
| HR placements are view-only; no CTC, fees, revenue, or guarantee; no add/change | COMPLETE | `HR_PERMS` has only `placements.view_placement`. Serializer strips financial fields. Admin and `Placements.tsx` hide them. Tests in `test_finance_permissions.py` and `test_admin_permissions.py`. |
| Do not fabricate consent; admin create needs explicit consent or a documented basis | COMPLETE for create | API requires `consent_acknowledged` and a notice version (`candidates/serializers.py`). Admin uses `NON_CONSENT_BASES` and nullable `consent_recorded_at` (`candidates/0003`). |
| No auto-merge by name | COMPLETE as a refusal | `reviews.py` queues email, phone, and file hash only. `decide()` sets `records_merged: false`. No name match. |
| Matching weights 40/25/15/10/10 | COMPLETE | `apps/matching/services.py` `WEIGHTS`. Tested in `test_matching.py`. |
| Financial totals come from lines, payments, and credit notes | PARTIAL | API ignores header totals and locks the invoice (`billing/services.py`). Admin `InvoiceAdmin.readonly_fields` omits `subtotal`, `tax_amount`, and `total`, so a typed header can disagree until the next line save (`billing/admin.py`). |
| Role groups are not restored on login or save | COMPLETE | `User.save` does not assign groups. `bootstrap_groups` does not rewrite an existing group unless `--reset`. Tested. |
| Superusers keep admin bypass | COMPLETE | `user.has_perm` for active superusers. Documented in `apps/access.py`. |

## Gap register

Labels: **COMPLETE** (backend + UI + tests), **PARTIAL** (real behavior, a missing surface or missing proof), **MISSING** (not built), **DEFECTIVE** (built behavior contradicts a decided rule), **N/A** (explicitly out of this product or blocked on an unanswered question, with no code pretending otherwise).

### 1. Security and privacy

| Requirement | Status | Evidence |
| --- | --- | --- |
| Role matrix in API, admin, frontend, IDOR, autocomplete | PARTIAL | Default groups in `apps/access.py`. Object querysets for clients, jobs, applications, interviews, opportunities. Billing autocomplete rejects unseen FKs (`billing/admin.py`, `test_admin_review.py`). Contact cross-owner is 403. Sales interview list is 403. Frontend `Permit` hides routes from `permissions` on `/users/me/`. Gaps: placement and billing lists are permission-wide, not row-scoped (default grants are also wide). Candidate notes without a `candidate` query return every note the permission allows. That matches the shared candidate database, not a second owner scope. |
| Resume privacy and signed download | PARTIAL | Serializer omits file, parsed text, and hash. `/media/` is unrouted (`test_foundation.py`). `POST /resumes/{id}/download/` and `GET /resume-downloads/?token=` re-check `candidates.view_resume_content` (`candidates/downloads.py`, `test_resume_download.py`). HR and Management are not granted that permission. The React candidate page can request a link only when the permission is held. No browser proof in this pass. Download is not written to `AuditLog`. |
| Consent capture | COMPLETE for storage | API and admin. Browser proof is the Phase 5 note, not this pass. |
| Consent withdrawal | MISSING | `consent_withdrawn_at` and `CandidateConsent.withdrawn_at` exist, with check `candidate_consent_withdrawal_after_grant`. No API action, no admin action, no screen. API update marks the timestamps read-only. |
| Duplicate merge per the rules in `reviews.py` | MISSING | `decide()` only records a decision. Rules that are written and not implemented: explicit surviving profile, keep each person's sourcing and consent, relink applications, interviews, submissions, and other FKs, keep the other row as an audited alias, record field conflicts, log actor, time, source, and destination. One person's consent is not the other's. Open question 9 in `AUDIT_REPORT.md` (which role may merge) is still unanswered. |
| Retention enforcement | MISSING | `SystemConfiguration` stores four nullable day counts. No Celery beat schedule. The only task is `parse_resume`. README and status both say the numbers are not enforced. |
| Audit coverage | DEFECTIVE relative to the privacy goal | `AuditLog` is written only in `DuplicateReview.decide` (`candidates/models.py`). Downloads, billing, consent, and retention do not write a row. `ip_address` is never set. |
| Background failure notification | MISSING | `parse_resume` sets `parsing_status=FAILED` and retries twice. Nothing records the final failure for an operator, and there is no notification model or mail call. |
| Login throttle, cookie session, S3 | MISSING | Left for the production-prep agent where it is deploy hardening. Tokens stay in `localStorage`. |

### 2. Data integrity and finance

| Requirement | Status | Evidence |
| --- | --- | --- |
| Invoice, payment, and credit-note integrity on the API | COMPLETE | Locks, derived totals, outstanding, status, rollback test in `test_billing_service.py`. |
| Same integrity in Django admin | DEFECTIVE | Header totals are editable. Payment and credit-note inlines call `Model.save()` and do not use `remaining_capacity`. |
| Placement commercial copy and HR view-only | COMPLETE | `test_commercial_terms.py`, finance permission tests, admin, `Placements.tsx`. |
| Concurrency | PARTIAL | API uses `select_for_update`. Admin saves do not. |

### 3. Core workflows

| Requirement | Status | Evidence |
| --- | --- | --- |
| Client CRM and ownership history | PARTIAL | API create/update writes `ClientOwnershipHistory`. Phase 5 client page has contacts, activities, and commercial fields. No dedicated history panel was confirmed as a first-class screen; the API does not expose history as its own route. |
| Sales opportunities and attribution | PARTIAL | API and `test_opportunities.py` enforce owner scope and `view_all_salesopportunity` for reassignment. No React route (`App.tsx` has no opportunities path). |
| JD assignment history | COMPLETE for the write path | `JobAssignmentHistory` on assign. API and admin. The jobs page assigns recruiters. |
| JD sales-owner history | MISSING | `Job.sales_owner` can change in the API and admin with no owner-history row. Client ownership is the only sales-owner history table. |
| Candidate database | PARTIAL | Shared profiles, consent, notes, skills, upload. Phase 5 page exists. |
| Matching engine, explanations, mandatory skills | COMPLETE | Weights as decided. Mandatory skill sets `mandatory_skill_failure` and does not cap the score or change the application. `rules-v2`. Jobs page shows the explanation and hides Find candidates without `jobs.run_match`. Tested. |
| Application transition graph | COMPLETE | `applications/services.py` and the same map in admin and `workflow.ts`. Tested, including re-apply after reject or withdraw and the joined slot. |
| Interviews, participants, history | PARTIAL | Create and reschedule write events. Participant API tested. Phase 5 interviews page exists. Sales are 403. No separate "link result to application" automation, and none was specified. |
| Submissions | PARTIAL | API status map tested. Phase 5 page exists. Application status is not changed by a submission. |

### 4. Reporting

| Requirement | Status | Evidence |
| --- | --- | --- |
| HR, sales, and overview endpoints | PARTIAL | Three endpoints, permission-gated. HR overview forces `invoiced_revenue` to 0 (`reports/views.py`). |
| Filters (date, employee, department, client, JD, status, recruiter, sales executive) | MISSING | Views accept no query parameters. `Reports.tsx` calls the bare URLs. |
| Historical attribution | DEFECTIVE for owner changes | Sales and overview group clients and jobs by the current `sales_owner`. `ClientOwnershipHistory` is never read by reports. After a transfer, the previous owner loses the client count. Application recruiter is frozen on PATCH, so recruiter counts are closer to historical, but they are not filtered by `ApplicationHistory`. |

### 5. Frontend

| Requirement | Status | Evidence |
| --- | --- | --- |
| Phase 5 modules | PARTIAL | Routes: dashboard, clients, jobs, candidates, duplicates, applications, interviews, submissions, placements, billing, reports, users, settings. Vitest covers navigation, consent payload, pipeline buttons, HR placement amounts, report zeros, duplicate approve, billing totals, blank retention. |
| Sales opportunity screen | MISSING | Permission exists. No page. |
| Duplicate merge control | MISSING | Page copy says the decision does not merge. Vitest asserts there is no merge button. |
| Consent withdrawal control | MISSING | |
| Report filters | MISSING | |
| Tailwind | COMPLETE | Tailwind 4 is installed and used. |
| Role-negative UI | PARTIAL | Vitest plus the Phase 5 Chrome note. Not re-run in this pass. |

### 6. Operations

| Requirement | Status | Evidence |
| --- | --- | --- |
| PostgreSQL migrations committed | COMPLETE | Apps have `migrations` packages. Consent migration `candidates/0003` is the only follow-up. `test apps` applied them on PostgreSQL 16.15 in this pass. |
| Celery worker | PARTIAL | Compose worker runs `parse_resume`. No beat service. |
| Gunicorn, Nginx, non-root, private media at the edge, env secrets | MISSING in git | Private media is true only because Django does not mount `/media/`. The production-prep agent is scoped to this row and had not committed. This completion branch should not rewrite that deploy work out from under it. |
| Department API and UI | MISSING | `Department` is admin-only. No product rule in code says the API must exist beyond the original target list. Left as a gap, not invented here. |
| Password reset | MISSING | Not specified beyond the Phase 1 status note. |
| Malware scan and S3 | MISSING | Named as later work. No scanner contract exists. |

## Open questions (not decided by this baseline)

Taken from `AUDIT_REPORT.md` and still unanswered in code comments. Implementations after this document must not invent answers.

1. Who may perform a duplicate merge (open question 9). The how is specified in `reviews.py`. The who is not.
2. Whether retention deletes rows or only archives them, and whether candidates and applications with protected children may be removed (open question 18 asks if hard delete is forbidden).
3. Whether blacklisted clients block new jobs.
4. Whether a JD sales-owner change must be historized the way client ownership is. No table exists.
5. Currency and tax breakup beyond the stored `tax_rate` on a line.
6. Whether interviewers must be users. The model allows a user or a name.

## What this baseline will not count as done

Deploy hardening that the other agent is implementing. Anything that would require a new business rule from the open list above, unless the existing schema already forces the safe behavior (for example, `PROTECT` already stops a delete).
