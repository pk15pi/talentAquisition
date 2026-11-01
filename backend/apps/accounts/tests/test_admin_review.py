from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import Client

from apps.accounts.tests.test_admin_permissions import admin_form_payload, grant, staff_client
from apps.billing.models import Invoice, InvoiceLine
from apps.candidates.models import Candidate, CandidateConsent
from apps.organizations.models import SystemConfiguration
from apps.placements.models import Placement
from apps.testkit import SynfoAPITestCase, make_candidate, make_client, make_job


SECRET_CTC = "999999.00"
SECRET_OFFERED = "880011.22"
SECRET_REVENUE = "770022.33"
SECRET_PARSED = "PARSED-REVIEW-SECRET"
SECRET_HASH = "HASH-REVIEW-SECRET"


class RoleGroupProvisioningTests(SynfoAPITestCase):
    def test_removed_membership_survives_login_and_profile_updates(self):
        extra = Group.objects.create(name="Extra Desk")
        self.hr.groups.clear()
        self.hr.groups.add(extra)
        client = Client()
        self.assertTrue(client.login(username="hr", password=self.password))
        self.hr.refresh_from_db()
        self.assertFalse(self.hr.groups.filter(name="HR Executive").exists())
        self.assertTrue(self.hr.groups.filter(name="Extra Desk").exists())

        self.hr.phone = "9000011111"
        self.hr.role = "SALES"
        self.hr.save()
        self.hr.refresh_from_db()
        self.assertEqual(set(self.hr.groups.values_list("name", flat=True)), {"Extra Desk"})

        call_command("bootstrap_groups")
        self.hr.refresh_from_db()
        self.assertEqual(set(self.hr.groups.values_list("name", flat=True)), {"Extra Desk"})

    def test_new_users_receive_only_their_role_group_and_keep_later_additions(self):
        user_model = get_user_model()
        created = user_model.objects.create_user("provisioned", password=self.password, role="HR")
        self.assertTrue(created.groups.filter(name="HR Executive").exists())
        extra = Group.objects.create(name="Weekend Desk")
        created.groups.add(extra)
        created.first_name = "Provisioned"
        created.save()
        self.assertEqual(
            set(created.groups.values_list("name", flat=True)),
            {"HR Executive", "Weekend Desk"},
        )
        boss = user_model.objects.create_superuser("boss2", "boss2@example.com", self.password)
        self.assertTrue(boss.groups.filter(name="Administrator").exists())

        self.as_user(self.admin)
        response = self.client.post(
            "/api/v1/users/",
            {"username": "api-sales", "password": "longpassword1", "role": "SALES"},
            format="json",
        )
        self.assertEqual(response.status_code, 201, getattr(response, "data", response.content[:500]))
        api_user = user_model.objects.get(username="api-sales")
        self.assertTrue(api_user.groups.filter(name="Sales Executive").exists())


class BillingAdminPermissionTests(SynfoAPITestCase):
    def setUp(self):
        super().setUp()
        self.company = make_client(self.sales, "BILLING-CLIENT")
        self.hidden_company = make_client(self.sales_two, "HIDDEN-BILLING-CLIENT")
        self.job = make_job(self.company, self.sales, "Billing JD")
        self.candidate = make_candidate(self.hr, email="bill@example.com", phone="9000004444", name="Bill Candidate")
        from apps.applications.models import Application

        application = Application.objects.create(candidate=self.candidate, job=self.job, recruiter=self.hr, status="OFFERED")
        self.placement = Placement.objects.create(
            application=application,
            offered_ctc=Decimal(SECRET_OFFERED),
            agreed_fee_type="PERCENTAGE",
            agreed_fee_value=Decimal("6.25"),
            expected_revenue=Decimal(SECRET_REVENUE),
        )
        self.invoice = Invoice.objects.create(
            client=self.company,
            invoice_date="2026-11-01",
            due_date="2026-11-01",
            subtotal=Decimal("10.00"),
            total=Decimal("10.00"),
            created_by=self.management,
        )

    def _clerk(self, username, *codes):
        user_model = get_user_model()
        clerk = user_model.objects.create_user(username, password=self.password, role="HR")
        clerk.groups.clear()
        for app_label, codename in codes:
            grant(clerk, app_label, codename)
        return staff_client(clerk)

    def test_invoice_view_alone_cannot_add_or_change_children_or_open_their_admins(self):
        client, user = self._clerk("viewer", ("billing", "view_invoice"))
        page = client.get(f"/admin/billing/invoice/{self.invoice.pk}/change/")
        self.assertEqual(page.status_code, 200)
        self.assertNotContains(page, 'class="add-row"')
        self.assertContains(page, 'name="lines-MAX_NUM_FORMS" value="0"')
        for url in (
            "/admin/billing/invoiceline/",
            "/admin/billing/payment/",
            "/admin/billing/creditnote/",
            "/admin/billing/invoiceline/add/",
            "/admin/billing/payment/add/",
            "/admin/billing/creditnote/add/",
        ):
            self.assertEqual(client.get(url).status_code, 403, url)
        from django.contrib import admin

        payload = admin_form_payload(admin.site._registry[Invoice], user, self.invoice)
        self.assertIn("lines-TOTAL_FORMS", payload)
        payload["lines-TOTAL_FORMS"] = "1"
        payload["lines-INITIAL_FORMS"] = "0"
        payload["lines-0-description"] = "Smuggled line"
        payload["lines-0-quantity"] = "1"
        payload["lines-0-unit_amount"] = "5.00"
        payload["lines-0-tax_rate"] = "0"
        payload["lines-0-placement"] = str(self.placement.pk)
        payload["lines-0-id"] = ""
        response = client.post(f"/admin/billing/invoice/{self.invoice.pk}/change/", payload)
        self.assertEqual(response.status_code, 403)
        self.assertFalse(InvoiceLine.objects.filter(description="Smuggled line").exists())
        self.assertEqual(client.get(f"/admin/billing/invoice/{self.invoice.pk}/delete/").status_code, 403)

    def test_invoice_line_cannot_select_an_unauthorized_placement_or_leak_fees(self):
        denied, denied_user = self._clerk(
            "denied",
            ("billing", "view_invoice"),
            ("billing", "change_invoice"),
            ("billing", "view_invoiceline"),
            ("billing", "add_invoiceline"),
            ("billing", "change_invoiceline"),
        )
        autocomplete = denied.get(
            "/admin/autocomplete/",
            {"app_label": "billing", "model_name": "invoiceline", "field_name": "placement", "term": "Bill"},
        )
        self.assertEqual(autocomplete.status_code, 403)
        self.assertNotIn(SECRET_OFFERED.encode(), autocomplete.content)
        from django.contrib import admin

        payload = admin_form_payload(admin.site._registry[Invoice], denied_user, self.invoice)
        payload["lines-TOTAL_FORMS"] = "1"
        payload["lines-INITIAL_FORMS"] = "0"
        payload["lines-0-description"] = "Linked line"
        payload["lines-0-quantity"] = "1"
        payload["lines-0-unit_amount"] = "5.00"
        payload["lines-0-tax_rate"] = "0"
        payload["lines-0-placement"] = str(self.placement.pk)
        payload["lines-0-id"] = ""
        response = denied.post(f"/admin/billing/invoice/{self.invoice.pk}/change/", payload)
        self.assertNotEqual(response.status_code, 302)
        self.assertFalse(InvoiceLine.objects.filter(placement=self.placement).exists())

        viewer, _user = self._clerk(
            "viewer",
            ("billing", "view_invoice"),
            ("billing", "view_invoiceline"),
            ("placements", "view_placement"),
        )
        allowed = viewer.get(
            "/admin/autocomplete/",
            {"app_label": "billing", "model_name": "invoiceline", "field_name": "placement", "term": "Bill"},
        )
        self.assertEqual(allowed.status_code, 200)
        self.assertIn(b"Bill Candidate", allowed.content)
        self.assertNotIn(SECRET_OFFERED.encode(), allowed.content)
        self.assertNotIn(SECRET_REVENUE.encode(), allowed.content)
        line_page = viewer.get(f"/admin/billing/invoice/{self.invoice.pk}/change/")
        self.assertNotIn(SECRET_OFFERED.encode(), line_page.content)
        self.assertNotIn(SECRET_REVENUE.encode(), line_page.content)

    def test_invoice_client_widget_hides_clients_the_user_cannot_view(self):
        client, _user = staff_client(self.sales)
        grant(self.sales, "billing", "view_invoice")
        grant(self.sales, "billing", "add_invoice")
        self.sales = type(self.sales).objects.get(pk=self.sales.pk)
        browser = Client()
        browser.force_login(self.sales)
        found = browser.get(
            "/admin/autocomplete/",
            {"app_label": "billing", "model_name": "invoice", "field_name": "client", "term": "BILLING-CLIENT"},
        )
        self.assertEqual(found.status_code, 200)
        self.assertIn(b"BILLING-CLIENT", found.content)
        self.assertNotIn(b"HIDDEN-BILLING-CLIENT", found.content)
        add_page = browser.get("/admin/billing/invoice/add/")
        self.assertNotIn(b"HIDDEN-BILLING-CLIENT", add_page.content)


class CandidateConsentAdminTests(SynfoAPITestCase):
    def _post_candidate(self, client, user, **overrides):
        from django.contrib import admin

        payload = admin_form_payload(admin.site._registry[Candidate], user, None)
        payload.update(
            {
                "full_name": "Admin Created",
                "email": "admin-created@example.com",
                "phone": "9000005555",
                "privacy_notice_version": "notice-1",
                "processing_basis": "consent",
                "source": "OTHER",
            }
        )
        payload.update(overrides)
        return client.post("/admin/candidates/candidate/add/", payload)

    def test_admin_create_requires_consent_evidence_and_does_not_invent_it(self):
        client, user = staff_client(self.hr)
        missing = self._post_candidate(client, user)
        self.assertEqual(missing.status_code, 200, missing.content[:500])
        self.assertFalse(Candidate.objects.filter(email="admin-created@example.com").exists())
        self.assertFalse(CandidateConsent.objects.filter(source="admin").exists())

        confirmed = self._post_candidate(client, user, consent_confirmed="on")
        self.assertEqual(confirmed.status_code, 302, confirmed.content[:1000])
        created = Candidate.objects.get(email="admin-created@example.com")
        self.assertIsNotNone(created.consent_recorded_at)
        consent = created.consents.get()
        self.assertEqual(consent.processing_basis, "consent")
        self.assertEqual(consent.recorded_by_id, self.hr.id)
        self.assertEqual(consent.privacy_notice_version, "notice-1")
        self.assertTrue(Candidate.objects.filter(normalized_email="admin-created@example.com").count(), 1)

    def test_admin_create_accepts_a_documented_non_consent_basis_without_a_consent_timestamp(self):
        client, user = staff_client(self.hr)
        response = self._post_candidate(
            client,
            user,
            email="basis@example.com",
            phone="9000006666",
            processing_basis="legitimate_interest",
            basis_documentation="Employer instruction dated 2026-11-01 to retain this profile for an open role.",
        )
        self.assertEqual(response.status_code, 302, response.content[:1000])
        created = Candidate.objects.get(email="basis@example.com")
        self.assertIsNone(created.consent_recorded_at)
        consent = created.consents.get()
        self.assertEqual(consent.processing_basis, "legitimate_interest")
        self.assertIn("Employer instruction", consent.purpose)
        self.assertEqual(consent.recorded_by_id, self.hr.id)

    def test_admin_create_rejects_a_notice_version_that_does_not_match_configuration(self):
        config = SystemConfiguration.load()
        config.privacy_notice_version = "notice-9"
        config.save()
        client, user = staff_client(self.hr)
        response = self._post_candidate(client, user, consent_confirmed="on", privacy_notice_version="notice-1")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Candidate.objects.filter(email="admin-created@example.com").exists())
        matched = self._post_candidate(
            client,
            user,
            email="matched-notice@example.com",
            phone="9000007777",
            consent_confirmed="on",
            privacy_notice_version="notice-9",
        )
        self.assertEqual(matched.status_code, 302, matched.content[:800])


class SensitiveAdminLeakTests(SynfoAPITestCase):
    def setUp(self):
        super().setUp()
        from django.core.files.uploadedfile import SimpleUploadedFile

        from apps.applications.models import Application
        from apps.candidates.models import Resume

        self.company = make_client(self.sales, "LEAK-CLIENT")
        self.job = make_job(self.company, self.sales, "Leak JD")
        self.candidate = make_candidate(self.hr, email="leak@example.com", phone="9000008888", name="Leak Candidate")
        self.candidate.current_ctc = Decimal(SECRET_CTC)
        self.candidate.expected_ctc = Decimal("1000.00")
        self.candidate.save()
        self.resume = Resume.objects.create(
            candidate=self.candidate,
            file=SimpleUploadedFile("leak.pdf", b"%PDF-1.4 leak"),
            original_filename="leak.pdf",
            file_hash=SECRET_HASH,
            parsed_text=SECRET_PARSED,
            parsing_status="COMPLETED",
            version=1,
            is_primary=True,
            uploaded_by=self.hr,
        )
        application = Application.objects.create(candidate=self.candidate, job=self.job, recruiter=self.hr, status="OFFERED")
        self.placement = Placement.objects.create(
            application=application,
            offered_ctc=Decimal(SECRET_OFFERED),
            agreed_fee_type="FIXED",
            agreed_fee_value=Decimal("50.00"),
            expected_revenue=Decimal(SECRET_REVENUE),
        )

    def test_hr_cannot_see_resume_content_or_compensation_in_admin_surfaces(self):
        hr, _user = staff_client(self.hr)
        surfaces = [
            hr.get("/admin/candidates/candidate/"),
            hr.get(f"/admin/candidates/candidate/{self.candidate.pk}/change/"),
            hr.get("/admin/candidates/resume/"),
            hr.get(f"/admin/candidates/resume/{self.resume.pk}/change/"),
            hr.get("/admin/placements/placement/"),
            hr.get(f"/admin/placements/placement/{self.placement.pk}/change/"),
            hr.get(f"/admin/applications/application/{self.placement.application_id}/change/"),
            hr.get(
                "/admin/autocomplete/",
                {"app_label": "applications", "model_name": "application", "field_name": "candidate", "term": "Leak"},
            ),
        ]
        for response in surfaces:
            self.assertEqual(response.status_code, 200, response.content[:200])
            for secret in (SECRET_CTC, SECRET_PARSED, SECRET_HASH, SECRET_OFFERED, SECRET_REVENUE, "resumes/"):
                self.assertNotIn(secret.encode(), response.content)
        self.assertNotIn(b'type="file"', surfaces[1].content)
        self.assertNotIn(b'type="file"', surfaces[3].content)
        self.assertIn(b"leak.pdf", surfaces[1].content)
        self.assertIn(b"Leak Candidate", surfaces[6].content)
