from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.management import call_command

from apps.testkit import SynfoAPITestCase


class FoundationTests(SynfoAPITestCase):
    def test_health_and_version(self):
        response = self.client.get("/api/v1/health/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "ok")
        self.assertEqual(response.data["version"], "v1")
        unknown = self.client.get("/api/v2/health/")
        self.assertEqual(unknown.status_code, 404)

    def test_media_is_not_public(self):
        response = self.client.get("/media/resumes/secret.pdf")
        self.assertEqual(response.status_code, 404)

    def test_unauthenticated_error_shape(self):
        response = self.client.get("/api/v1/clients/")
        self.assertEqual(response.status_code, 401)
        self.assertIn("detail", response.data)
        self.assertIn("code", response.data)
        self.assertIn("errors", response.data)

    def test_inactive_user_cannot_obtain_a_token(self):
        self.sales.is_active = False
        self.sales.save(update_fields=["is_active"])
        response = self.client.post(
            "/api/v1/auth/token/",
            {"username": "sales", "password": self.password},
            format="json",
        )
        self.assertEqual(response.status_code, 401)

    def test_refresh_returns_a_new_access_token(self):
        issued = self.client.post(
            "/api/v1/auth/token/",
            {"username": "sales", "password": self.password},
            format="json",
        )
        self.assertEqual(issued.status_code, 200)
        refreshed = self.client.post(
            "/api/v1/auth/token/refresh/",
            {"refresh": issued.data["refresh"]},
            format="json",
        )
        self.assertEqual(refreshed.status_code, 200)
        self.assertIn("access", refreshed.data)

    def test_createsuperuser_defaults_to_admin_role(self):
        User = get_user_model()
        boss = User.objects.create_superuser("boss", "boss@example.com", self.password)
        self.assertEqual(boss.role, "ADMIN")
        self.assertTrue(boss.groups.filter(name="Administrator").exists())

    def test_superuser_bypasses_role_restrictions(self):
        self.root.role = "HR"
        self.root.save()
        self.as_user(self.root)
        client = self.client.post("/api/v1/clients/", {"company_name": "Root Co"}, format="json")
        self.assertEqual(client.status_code, 201, client.data)
        invoices = self.client.get("/api/v1/invoices/")
        self.assertEqual(invoices.status_code, 200)

    def test_current_user_endpoint(self):
        self.as_user(self.sales)
        response = self.client.get("/api/v1/users/me/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["username"], "sales")

    def test_bootstrap_does_not_reset_group_edits(self):
        group = Group.objects.get(name="HR Executive")
        invoice_perm = Permission.objects.get(content_type__app_label="billing", codename="view_invoice")
        self.assertFalse(group.permissions.filter(pk=invoice_perm.pk).exists())
        extra = Permission.objects.get(content_type__app_label="jobs", codename="view_all_jobs")
        removed = Permission.objects.get(content_type__app_label="jobs", codename="run_match")
        group.permissions.add(extra)
        group.permissions.remove(removed)
        call_command("bootstrap_groups")
        self.assertTrue(group.permissions.filter(pk=extra.pk).exists())
        self.assertFalse(group.permissions.filter(pk=removed.pk).exists())
        self.assertFalse(group.permissions.filter(pk=invoice_perm.pk).exists())

    def test_hr_group_has_no_finance_permissions_by_default(self):
        group = Group.objects.get(name="HR Executive")
        codes = set(group.permissions.values_list("codename", flat=True))
        self.assertNotIn("view_invoice", codes)
        self.assertNotIn("view_placement_financials", codes)
        self.assertNotIn("view_financial_report", codes)
        self.assertIn("review_duplicate", codes)
