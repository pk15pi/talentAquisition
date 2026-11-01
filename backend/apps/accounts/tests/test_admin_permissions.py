"""Admin permission, field visibility, and retention tests.

These cover Django admin only. API rules stay in the module tests.
"""

from datetime import timedelta
from decimal import Decimal

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, RequestFactory
from django.utils import timezone

from apps.applications.models import Application, ApplicationHistory
from apps.audit.models import AuditLog
from apps.billing.models import Invoice
from apps.candidates.models import Candidate, DuplicateReview, Resume
from apps.interviews.models import Interview
from apps.jobs.models import JobAssignment, JobAssignmentHistory, JobStatusHistory
from apps.organizations.models import CodeSequence
from apps.placements.models import Placement
from apps.sales.models import SalesOpportunity
from apps.testkit import SynfoAPITestCase, make_candidate, make_client, make_job

PARSED = "PARSED-PHASE3-SECRET"
FILE_HASH = "HASH-PHASE3-SECRET"
CTC = "999999.00"
OFFERED = "880011.22"
REVENUE = "770022.33"
FEE = "6.25"
INVOICE_TOTAL = "654321.09"
FEEDBACK = "FEEDBACK-PHASE3-SECRET"


def grant(user, app_label, codename):
    user.user_permissions.add(Permission.objects.get(content_type__app_label=app_label, codename=codename))


def staff_client(user):
    user_model = get_user_model()
    user_model.objects.filter(pk=user.pk).update(is_staff=True)
    fresh = user_model.objects.get(pk=user.pk)
    client = Client()
    client.force_login(fresh)
    return client, fresh


def _widget_value(widget, value):
    inner = widget
    seen = set()
    while type(inner).__name__ == "RelatedFieldWidgetWrapper" and id(inner) not in seen:
        seen.add(id(inner))
        inner = inner.widget
    if hasattr(inner, "widgets"):
        parts = inner.decompress(value) if value not in (None, "") else [None] * len(inner.widgets)
        rendered = []
        for part, subwidget in zip(parts, inner.widgets):
            formatted = subwidget.format_value(part)
            if isinstance(formatted, (list, tuple)):
                formatted = formatted[0] if len(formatted) == 1 else ""
            rendered.append("" if formatted in (None, False) else formatted)
        return ("split", rendered)
    formatted = inner.format_value(value)
    if isinstance(formatted, (list, tuple)):
        if len(formatted) == 1:
            formatted = formatted[0]
        else:
            return list(formatted)
    if formatted in (None, False, ""):
        return None
    return "on" if formatted is True else formatted


def _store_field(data, key, field, value):
    rendered = _widget_value(field.widget, value)
    if isinstance(rendered, tuple) and rendered[0] == "split":
        for index, part in enumerate(rendered[1]):
            data[f"{key}_{index}"] = part
        return
    if isinstance(rendered, list):
        data[key] = rendered
        return
    if rendered is not None:
        data[key] = rendered


def admin_form_payload(model_admin, user, obj):
    request = RequestFactory().get("/admin/")
    request.user = user
    form_class = model_admin.get_form(request, obj, change=obj is not None)
    form = form_class(instance=obj) if obj is not None else form_class()
    data = {}
    for name, field in form.fields.items():
        _store_field(data, name, field, form[name].value())
    target = obj if obj is not None else model_admin.model()
    formsets, _inlines = model_admin._create_formsets(request, target, change=obj is not None)
    for formset in formsets:
        management = formset.management_form
        for name in management.fields:
            value = management[name].value()
            data[f"{formset.prefix}-{name}"] = "" if value is None else str(value)
        for index, inline_form in enumerate(formset.initial_forms):
            for name, field in inline_form.fields.items():
                _store_field(data, f"{formset.prefix}-{index}-{name}", field, inline_form[name].value())
    data["_save"] = "Save"
    return data


class AdminPermissionTests(SynfoAPITestCase):
    def setUp(self):
        super().setUp()
        self.own_client = make_client(self.sales, "OWN-CLIENT-PHASE3")
        self.other_client = make_client(self.sales_two, "OTHER-CLIENT-PHASE3")
        self.own_job = make_job(self.own_client, self.sales, "OWN-JD-PHASE3")
        self.other_job = make_job(self.other_client, self.sales_two, "OTHER-JD-PHASE3")
        self.candidate = make_candidate(self.hr, email="phase3@example.com", phone="9000001111", name="Phase Three")
        self.candidate.current_ctc = Decimal(CTC)
        self.candidate.expected_ctc = Decimal("1000.00")
        self.candidate.save()
        self.resume = Resume.objects.create(
            candidate=self.candidate,
            file=SimpleUploadedFile("phase3.pdf", b"%PDF-1.4 phase3"),
            original_filename="phase3.pdf",
            file_hash=FILE_HASH,
            parsed_text=PARSED,
            parsing_status="COMPLETED",
            version=1,
            is_primary=True,
            uploaded_by=self.hr,
        )
        self.application = Application.objects.create(candidate=self.candidate, job=self.own_job, recruiter=self.hr)
        self.interview = Interview.objects.create(
            application=self.application,
            round_name="L1",
            interview_date=timezone.now(),
            feedback=FEEDBACK,
            created_by=self.hr,
        )
        self.placement = Placement.objects.create(
            application=self.application,
            offered_ctc=Decimal(OFFERED),
            agreed_fee_type="PERCENTAGE",
            agreed_fee_value=Decimal(FEE),
            expected_revenue=Decimal(REVENUE),
        )
        self.invoice = Invoice.objects.create(
            client=self.own_client,
            invoice_date=timezone.localdate(),
            due_date=timezone.localdate(),
            subtotal=Decimal(INVOICE_TOTAL),
            total=Decimal(INVOICE_TOTAL),
            created_by=self.management,
        )
        self.audit = AuditLog.objects.create(
            user=self.hr,
            action="phase3_audit_marker",
            entity_type="candidates.Candidate",
            entity_id=str(self.candidate.pk),
            details={"records_merged": False},
        )
        self.sequence = CodeSequence.objects.create(key="phase3-admin", current_value=4)
        SalesOpportunity.objects.create(client=self.own_client, owner=self.sales, title="OWN-OPP-PHASE3")
        SalesOpportunity.objects.create(client=self.other_client, owner=self.sales_two, title="OTHER-OPP-PHASE3")

    def test_staff_flag_and_inactive_superuser_gate_the_admin_site(self):
        client = Client()
        client.force_login(self.sales)
        self.assertEqual(client.get("/admin/clients/client/").status_code, 302)
        staff, _user = staff_client(self.sales)
        self.assertEqual(staff.get("/admin/").status_code, 200)
        self.assertContains(staff.get("/admin/"), "SynfoTalent")
        user_model = get_user_model()
        user_model.objects.filter(pk=self.root.pk).update(is_active=False)
        inactive = Client()
        inactive.force_login(user_model.objects.get(pk=self.root.pk))
        self.assertEqual(inactive.get("/admin/").status_code, 302)

    def test_each_group_opens_only_the_modules_its_permissions_allow(self):
        expected = {
            self.sales: {
                "open": ["/admin/clients/client/", "/admin/jobs/job/", "/admin/sales/salesopportunity/"],
                "deny": [
                    "/admin/candidates/candidate/",
                    "/admin/billing/invoice/",
                    "/admin/billing/payment/",
                    "/admin/billing/creditnote/",
                    "/admin/placements/placement/",
                    "/admin/interviews/interview/",
                    "/admin/applications/application/",
                    "/admin/audit/auditlog/",
                    "/admin/accounts/user/",
                ],
            },
            self.hr: {
                "open": [
                    "/admin/candidates/candidate/",
                    "/admin/clients/client/",
                    "/admin/jobs/job/",
                    "/admin/applications/application/",
                    "/admin/interviews/interview/",
                    "/admin/placements/placement/",
                    "/admin/matching/skill/",
                ],
                "deny": [
                    "/admin/billing/invoice/",
                    "/admin/billing/payment/",
                    "/admin/billing/creditnote/",
                    "/admin/billing/invoiceline/",
                    "/admin/sales/salesopportunity/",
                    "/admin/audit/auditlog/",
                    "/admin/accounts/user/",
                    "/admin/matching/matchrun/",
                ],
            },
            self.lead: {
                "open": ["/admin/accounts/user/", "/admin/jobs/job/", "/admin/placements/placement/"],
                "deny": ["/admin/billing/invoice/", "/admin/audit/auditlog/", "/admin/sales/salesopportunity/"],
            },
            self.management: {
                "open": [
                    "/admin/billing/invoice/",
                    "/admin/billing/payment/",
                    "/admin/placements/placement/",
                    "/admin/accounts/user/",
                    "/admin/organizations/systemconfiguration/",
                    "/admin/candidates/candidate/",
                ],
                "deny": ["/admin/audit/auditlog/", "/admin/organizations/department/"],
            },
            self.admin: {
                "open": [
                    "/admin/audit/auditlog/",
                    "/admin/billing/invoice/",
                    "/admin/organizations/codesequence/",
                    "/admin/organizations/department/",
                    "/admin/candidates/resume/",
                ],
                "deny": [],
            },
        }
        for user, urls in expected.items():
            client, _fresh = staff_client(user)
            for url in urls["open"]:
                response = client.get(url)
                self.assertEqual(response.status_code, 200, f"{user.username} {url} {response.status_code}")
            for url in urls["deny"]:
                response = client.get(url)
                self.assertEqual(response.status_code, 403, f"{user.username} {url} {response.status_code}")

    def test_direct_permission_grant_opens_admin_without_a_role_group(self):
        user_model = get_user_model()
        bare = user_model.objects.create_user("bare", password=self.password, role="HR")
        bare.groups.clear()
        user_model.objects.filter(pk=bare.pk).update(is_staff=True)
        bare = user_model.objects.get(pk=bare.pk)
        client = Client()
        client.force_login(bare)
        # Session login updates last_login, and User.save puts the role group back.
        # Clear it again so this request is permission-only.
        bare.groups.clear()
        self.assertEqual(client.get("/admin/billing/invoice/").status_code, 403)
        self.assertEqual(client.get("/admin/candidates/candidate/").status_code, 403)
        grant(bare, "billing", "view_invoice")
        self.assertEqual(client.get("/admin/billing/invoice/").status_code, 200)
        self.assertEqual(client.get("/admin/candidates/candidate/").status_code, 403)

    def test_active_superuser_bypasses_group_restrictions(self):
        user_model = get_user_model()
        user_model.objects.filter(pk=self.hr.pk).update(is_staff=True, is_superuser=True)
        client = Client()
        client.force_login(user_model.objects.get(pk=self.hr.pk))
        self.assertEqual(client.get("/admin/billing/invoice/").status_code, 200)
        self.assertContains(client.get("/admin/billing/invoice/"), INVOICE_TOTAL)
        resume_page = client.get(f"/admin/candidates/resume/{self.resume.pk}/change/")
        self.assertContains(resume_page, PARSED)
        self.assertContains(resume_page, FILE_HASH)

    def test_object_scope_matches_the_api_visibility_helpers(self):
        sales, _user = staff_client(self.sales)
        client_list = sales.get("/admin/clients/client/")
        self.assertContains(client_list, "OWN-CLIENT-PHASE3")
        self.assertNotContains(client_list, "OTHER-CLIENT-PHASE3")
        self.assertEqual(sales.get(f"/admin/clients/client/{self.other_client.pk}/change/").status_code, 302)
        self.assertEqual(sales.get(f"/admin/clients/client/{self.own_client.pk}/change/").status_code, 200)
        self.assertEqual(sales.get(f"/admin/jobs/job/{self.own_job.pk}/change/").status_code, 200)
        self.assertEqual(sales.get("/admin/clients/client/add/").status_code, 200)
        self.assertEqual(sales.get("/admin/jobs/job/add/").status_code, 200)
        job_list = sales.get("/admin/jobs/job/?q=PHASE3")
        self.assertContains(job_list, "OWN-JD-PHASE3")
        self.assertNotContains(job_list, "OTHER-JD-PHASE3")
        opportunities = sales.get("/admin/sales/salesopportunity/")
        self.assertContains(opportunities, "OWN-OPP-PHASE3")
        self.assertNotContains(opportunities, "OTHER-OPP-PHASE3")

        hr, _user = staff_client(self.hr)
        self.assertContains(hr.get("/admin/clients/client/"), "OTHER-CLIENT-PHASE3")
        self.assertNotContains(hr.get("/admin/jobs/job/"), "OWN-JD-PHASE3")
        self.assertEqual(hr.get(f"/admin/jobs/job/{self.own_job.pk}/change/").status_code, 302)
        self.assertContains(hr.get(f"/admin/interviews/interview/{self.interview.pk}/change/"), FEEDBACK)
        self.assertEqual(sales.get("/admin/interviews/interview/").status_code, 403)

        lead, _user = staff_client(self.lead)
        self.assertContains(lead.get("/admin/jobs/job/"), "OTHER-JD-PHASE3")

    def test_resume_and_compensation_fields_follow_their_permissions(self):
        hr, _user = staff_client(self.hr)
        candidate_page = hr.get(f"/admin/candidates/candidate/{self.candidate.pk}/change/")
        self.assertEqual(candidate_page.status_code, 200)
        self.assertNotIn(PARSED.encode(), candidate_page.content)
        self.assertNotIn(FILE_HASH.encode(), candidate_page.content)
        self.assertNotIn(b"parsed_text", candidate_page.content)
        self.assertNotIn(b"file_hash", candidate_page.content)
        self.assertNotIn(b'type="file"', candidate_page.content)
        self.assertNotIn(b"resumes/", candidate_page.content)
        self.assertNotIn(b"current_ctc", candidate_page.content)
        self.assertNotIn(CTC.encode(), candidate_page.content)
        self.assertContains(candidate_page, "phase3.pdf")
        self.assertEqual(hr.get("/admin/candidates/candidate/add/").status_code, 200)
        resume_page = hr.get(f"/admin/candidates/resume/{self.resume.pk}/change/")
        self.assertNotIn(PARSED.encode(), resume_page.content)
        self.assertNotIn(b'type="file"', resume_page.content)
        changelist = hr.get("/admin/candidates/candidate/")
        self.assertNotIn(CTC.encode(), changelist.content)
        self.assertNotIn(b"current_ctc", changelist.content)

        management, _user = staff_client(self.management)
        self.assertContains(management.get("/admin/candidates/candidate/"), CTC)
        hidden_resume = management.get(f"/admin/candidates/resume/{self.resume.pk}/change/")
        self.assertNotIn(PARSED.encode(), hidden_resume.content)
        self.assertNotIn(FILE_HASH.encode(), hidden_resume.content)

        lead, _user = staff_client(self.lead)
        self.assertNotIn(CTC.encode(), lead.get(f"/admin/candidates/candidate/{self.candidate.pk}/change/").content)

        administrator, _user = staff_client(self.admin)
        visible_resume = administrator.get(f"/admin/candidates/resume/{self.resume.pk}/change/")
        self.assertContains(visible_resume, PARSED)
        self.assertContains(visible_resume, FILE_HASH)
        self.assertIn(b'type="file"', visible_resume.content)

    def test_hr_placement_is_view_only_and_hides_financial_fields(self):
        hr, _user = staff_client(self.hr)
        index = hr.get("/admin/")
        self.assertContains(index, "/admin/placements/placement/")
        self.assertNotContains(index, "/admin/billing/invoice/")
        page = hr.get(f"/admin/placements/placement/{self.placement.pk}/change/")
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, "Offered")
        for secret in (b"offered_ctc", b"agreed_fee", b"expected_revenue", b"guarantee_period", OFFERED.encode(), REVENUE.encode(), FEE.encode()):
            self.assertNotIn(secret, page.content)
        listing = hr.get("/admin/placements/placement/")
        self.assertNotIn(OFFERED.encode(), listing.content)
        self.assertNotIn(b"offered_ctc", listing.content)
        self.assertEqual(hr.get("/admin/placements/placement/add/").status_code, 403)
        self.assertEqual(hr.post(f"/admin/placements/placement/{self.placement.pk}/change/", {"status": "JOINED"}).status_code, 403)
        self.assertEqual(hr.get(f"/admin/placements/placement/{self.placement.pk}/delete/").status_code, 403)
        self.placement.refresh_from_db()
        self.assertEqual(self.placement.status, "OFFERED")
        self.assertEqual(self.placement.offered_ctc, Decimal(OFFERED))

    def test_financial_fields_stay_read_only_without_change_placement_financials(self):
        grant(self.hr, "placements", "change_placement")
        grant(self.hr, "placements", "view_placement_financials")
        client, user = staff_client(self.hr)
        page = client.get(f"/admin/placements/placement/{self.placement.pk}/change/")
        self.assertContains(page, OFFERED)
        self.assertNotIn(b'name="offered_ctc"', page.content)
        payload = admin_form_payload(admin.site._registry[Placement], user, self.placement)
        payload["offered_ctc"] = "1.00"
        payload["expected_revenue"] = "1.00"
        response = client.post(f"/admin/placements/placement/{self.placement.pk}/change/", payload)
        self.assertEqual(response.status_code, 302, response.content[:800])
        self.placement.refresh_from_db()
        self.assertEqual(self.placement.offered_ctc, Decimal(OFFERED))
        self.assertEqual(self.placement.expected_revenue, Decimal(REVENUE))

    def test_management_can_edit_placement_financials_and_see_invoices(self):
        client, user = staff_client(self.management)
        self.assertContains(client.get("/admin/billing/invoice/"), INVOICE_TOTAL)
        self.assertEqual(client.get(f"/admin/billing/invoice/{self.invoice.pk}/change/").status_code, 200)
        self.assertNotIn(b"delete_selected", client.get("/admin/billing/invoice/").content)
        self.assertEqual(client.get(f"/admin/billing/invoice/{self.invoice.pk}/delete/").status_code, 403)
        page = client.get(f"/admin/placements/placement/{self.placement.pk}/change/")
        self.assertContains(page, OFFERED)
        self.assertContains(page, "offered_ctc")
        payload = admin_form_payload(admin.site._registry[Placement], user, self.placement)
        payload["offered_ctc"] = "123.45"
        response = client.post(f"/admin/placements/placement/{self.placement.pk}/change/", payload)
        self.assertEqual(response.status_code, 302, response.content[:800])
        self.placement.refresh_from_db()
        self.assertEqual(self.placement.offered_ctc, Decimal("123.45"))

    def test_clearing_groups_hides_finance_until_the_permission_is_granted(self):
        self.management.groups.clear()
        self.management.user_permissions.clear()
        user_model = get_user_model()
        user_model.objects.filter(pk=self.management.pk).update(is_staff=True)
        user = user_model.objects.get(pk=self.management.pk)
        client = Client()
        client.force_login(user)
        user.groups.clear()
        self.assertEqual(client.get(f"/admin/placements/placement/{self.placement.pk}/change/").status_code, 403)
        grant(user, "placements", "view_placement")
        hidden = client.get(f"/admin/placements/placement/{self.placement.pk}/change/")
        self.assertEqual(hidden.status_code, 200)
        self.assertNotIn(OFFERED.encode(), hidden.content)
        grant(user, "placements", "view_placement_financials")
        visible = client.get(f"/admin/placements/placement/{self.placement.pk}/change/")
        self.assertContains(visible, OFFERED)

    def test_history_audit_and_financial_rows_cannot_be_deleted_or_rewritten(self):
        root, _user = staff_client(self.root)
        history = ApplicationHistory.objects.create(
            application=self.application,
            old_status="",
            new_status="IDENTIFIED",
            changed_by=self.hr,
            remarks="ORIGINAL-HISTORY",
        )
        targets = [
            f"/admin/audit/auditlog/{self.audit.pk}/change/",
            f"/admin/audit/auditlog/{self.audit.pk}/delete/",
            "/admin/audit/auditlog/add/",
            f"/admin/applications/applicationhistory/{history.pk}/change/",
            f"/admin/applications/applicationhistory/{history.pk}/delete/",
            f"/admin/billing/invoice/{self.invoice.pk}/delete/",
            f"/admin/placements/placement/{self.placement.pk}/delete/",
            f"/admin/candidates/candidate/{self.candidate.pk}/delete/",
            f"/admin/accounts/user/{self.hr.pk}/delete/",
            f"/admin/organizations/codesequence/{self.sequence.pk}/delete/",
            f"/admin/clients/client/{self.own_client.pk}/delete/",
        ]
        for url in targets:
            if url.endswith("/delete/") or url.endswith("/add/"):
                self.assertEqual(root.get(url).status_code, 403, url)
            else:
                self.assertEqual(root.get(url).status_code, 200, url)
                self.assertEqual(root.post(url, {"action": "rewritten", "remarks": "rewritten"}).status_code, 403, url)
        self.audit.refresh_from_db()
        self.assertEqual(self.audit.action, "phase3_audit_marker")
        history.refresh_from_db()
        self.assertEqual(history.remarks, "ORIGINAL-HISTORY")
        self.assertNotIn(b"delete_selected", root.get("/admin/audit/auditlog/").content)

    def test_code_sequences_are_editable_only_by_an_active_superuser(self):
        administrator, _user = staff_client(self.admin)
        url = f"/admin/organizations/codesequence/{self.sequence.pk}/change/"
        self.assertEqual(administrator.get(url).status_code, 200)
        self.assertEqual(administrator.post(url, {"key": "phase3-admin", "current_value": "9", "_save": "Save"}).status_code, 403)
        self.sequence.refresh_from_db()
        self.assertEqual(self.sequence.current_value, 4)
        root, _user = staff_client(self.root)
        response = root.post(url, {"key": "phase3-admin", "current_value": "9", "_save": "Save"})
        self.assertEqual(response.status_code, 302, response.content[:500])
        self.sequence.refresh_from_db()
        self.assertEqual(self.sequence.current_value, 9)

    def test_default_groups_cannot_be_deleted_and_non_superusers_cannot_grant_superuser(self):
        root, _user = staff_client(self.root)
        group = Group.objects.get(name="HR Executive")
        self.assertEqual(root.get(f"/admin/auth/group/{group.pk}/delete/").status_code, 403)
        self.assertTrue(Group.objects.filter(name="HR Executive").exists())
        administrator, admin_user = staff_client(self.admin)
        user_url = f"/admin/accounts/user/{self.hr.pk}/change/"
        page = administrator.get(user_url)
        self.assertEqual(page.status_code, 200)
        self.assertNotIn(b'name="is_superuser"', page.content)
        self.assertContains(page, "department")
        payload = admin_form_payload(admin.site._registry[get_user_model()], admin_user, self.hr)
        payload["is_superuser"] = "on"
        response = administrator.post(user_url, payload)
        self.assertEqual(response.status_code, 302, response.content[:800])
        self.hr.refresh_from_db()
        self.assertFalse(self.hr.is_superuser)

    def test_duplicate_review_action_does_not_merge_or_delete(self):
        other = make_candidate(self.hr, email="other-phase3@example.com", phone="9000002222", name="Other Phase")
        review = DuplicateReview.objects.create(
            candidate=self.candidate,
            matched_candidate=other,
            match_type=DuplicateReview.MatchType.EMAIL,
        )
        sales, _user = staff_client(self.sales)
        response = sales.post(
            "/admin/candidates/duplicatereview/",
            {"action": "approve_duplicate_reviews", "index": "0", "_selected_action": str(review.pk)},
        )
        self.assertEqual(response.status_code, 302, response.content[:500])
        review.refresh_from_db()
        self.assertEqual(review.status, DuplicateReview.Status.APPROVED)
        self.assertTrue(Candidate.objects.filter(pk=self.candidate.pk).exists())
        self.assertTrue(Candidate.objects.filter(pk=other.pk).exists())
        log = AuditLog.objects.get(entity_type="candidates.DuplicateReview", entity_id=str(review.pk))
        self.assertFalse(log.details["records_merged"])
        self.assertEqual(sales.get(f"/admin/candidates/duplicatereview/{review.pk}/delete/").status_code, 403)

    def test_admin_history_is_written_from_submitted_forms(self):
        management, management_user = staff_client(self.management)
        client_admin = admin.site._registry[type(self.own_client)]
        payload = admin_form_payload(client_admin, management_user, self.own_client)
        payload["sales_owner"] = str(self.sales_two.pk)
        response = management.post(f"/admin/clients/client/{self.own_client.pk}/change/", payload)
        self.assertEqual(response.status_code, 302, response.content[:1000])
        self.own_client.refresh_from_db()
        self.assertEqual(self.own_client.sales_owner_id, self.sales_two.id)
        self.assertTrue(
            self.own_client.ownership_history.filter(new_owner=self.sales_two, changed_by=self.management).exists()
        )

        lead, lead_user = staff_client(self.lead)
        job_admin = admin.site._registry[type(self.own_job)]
        job_payload = admin_form_payload(job_admin, lead_user, self.own_job)
        job_payload["status"] = "CLOSED"
        response = lead.post(f"/admin/jobs/job/{self.own_job.pk}/change/", job_payload)
        self.assertEqual(response.status_code, 302, response.content[:1000])
        self.assertTrue(
            JobStatusHistory.objects.filter(
                job=self.own_job, old_status="OPEN", new_status="CLOSED", changed_by=self.lead
            ).exists()
        )

        assign_payload = admin_form_payload(job_admin, lead_user, self.own_job)
        prefix = "assignments"
        assign_payload[f"{prefix}-TOTAL_FORMS"] = "1"
        assign_payload[f"{prefix}-INITIAL_FORMS"] = "0"
        assign_payload[f"{prefix}-0-recruiter"] = str(self.hr.pk)
        assign_payload[f"{prefix}-0-is_active"] = "on"
        assign_payload[f"{prefix}-0-id"] = ""
        response = lead.post(f"/admin/jobs/job/{self.own_job.pk}/change/", assign_payload)
        self.assertEqual(response.status_code, 302, response.content[:1200])
        assignment = JobAssignment.objects.get(job=self.own_job, recruiter=self.hr)
        self.assertTrue(
            JobAssignmentHistory.objects.filter(
                job=self.own_job, recruiter=self.hr, action="ASSIGNED", changed_by=self.lead
            ).exists()
        )
        remove_payload = admin_form_payload(job_admin, lead_user, self.own_job)
        remove_payload[f"{prefix}-0-is_active"] = ""
        response = lead.post(f"/admin/jobs/job/{self.own_job.pk}/change/", remove_payload)
        self.assertEqual(response.status_code, 302, response.content[:1200])
        assignment.refresh_from_db()
        self.assertFalse(assignment.is_active)
        self.assertTrue(
            JobAssignmentHistory.objects.filter(
                job=self.own_job, recruiter=self.hr, action="UNASSIGNED", changed_by=self.lead
            ).exists()
        )

        hr, hr_user = staff_client(self.hr)
        application_admin = admin.site._registry[Application]
        application_payload = admin_form_payload(application_admin, hr_user, self.application)
        application_payload["status"] = "SUBMITTED"
        application_payload["recruiter"] = str(self.lead.pk)
        response = hr.post(f"/admin/applications/application/{self.application.pk}/change/", application_payload)
        self.assertEqual(response.status_code, 302, response.content[:1000])
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, "SUBMITTED")
        self.assertEqual(self.application.recruiter_id, self.hr.id)
        self.assertTrue(
            ApplicationHistory.objects.filter(
                application=self.application,
                old_status="IDENTIFIED",
                new_status="SUBMITTED",
                changed_by=self.hr,
            ).exists()
        )

        interview_admin = admin.site._registry[Interview]
        interview_payload = admin_form_payload(interview_admin, hr_user, self.interview)
        later = self.interview.interview_date + timedelta(days=2)
        interview_payload["interview_date_0"] = later.date().isoformat()
        interview_payload["interview_date_1"] = later.time().strftime("%H:%M:%S")
        response = hr.post(f"/admin/interviews/interview/{self.interview.pk}/change/", interview_payload)
        self.assertEqual(response.status_code, 302, response.content[:1000])
        rescheduled = self.interview.events.filter(event_type="RESCHEDULED", changed_by=self.hr)
        self.assertEqual(rescheduled.count(), 1)

    def test_client_and_job_lists_accept_search_and_date_filters(self):
        sales, _user = staff_client(self.sales)
        response = sales.get("/admin/clients/client/?q=OWN-CLIENT&status__exact=ACTIVE&created_at__year=2026")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "OWN-CLIENT-PHASE3")
        jobs = sales.get("/admin/jobs/job/?q=OWN-JD&status__exact=OPEN")
        self.assertEqual(jobs.status_code, 200)
        self.assertContains(jobs, "OWN-JD-PHASE3")
