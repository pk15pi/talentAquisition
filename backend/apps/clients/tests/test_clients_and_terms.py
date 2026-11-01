from decimal import Decimal

from apps.testkit import SynfoAPITestCase, make_client, make_job


class ClientPermissionTests(SynfoAPITestCase):
    def test_sales_cannot_attach_a_contact_to_another_owners_client(self):
        client = make_client(self.sales, "Owned")
        other = make_client(self.sales_two, "Other")
        self.as_user(self.sales)
        denied = self.client.post(
            "/api/v1/client-contacts/",
            {"client": str(other.id), "name": "Leaked"},
            format="json",
        )
        self.assertEqual(denied.status_code, 403)
        allowed = self.client.post(
            "/api/v1/client-contacts/",
            {"client": str(client.id), "name": "Known"},
            format="json",
        )
        self.assertEqual(allowed.status_code, 201, allowed.data)

    def test_sales_only_lists_owned_clients(self):
        make_client(self.sales, "Mine")
        make_client(self.sales_two, "Theirs")
        self.as_user(self.sales)
        response = self.client.get("/api/v1/clients/")
        self.assertEqual(response.status_code, 200)
        names = {row["company_name"] for row in response.data["results"]}
        self.assertEqual(names, {"Mine"})

    def test_owner_must_hold_own_client_permission(self):
        self.as_user(self.management)
        response = self.client.post(
            "/api/v1/clients/",
            {"company_name": "Nope", "sales_owner": str(self.hr.id)},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_jd_commercial_terms_override_client_defaults(self):
        client = make_client(self.sales)
        client.default_fee_type = "PERCENTAGE"
        client.default_fee_value = Decimal("8.33")
        client.default_guarantee_period_days = 60
        client.save()
        job = make_job(client, self.sales)
        job.fee_value = Decimal("10.00")
        job.guarantee_period_days = 30
        job.save()
        terms = job.effective_commercial_terms()
        self.assertEqual(terms["fee_type"], "PERCENTAGE")
        self.assertEqual(terms["fee_value"], Decimal("10.00"))
        self.assertEqual(terms["guarantee_period_days"], 30)

    def test_job_visibility_follows_permissions_not_role_names(self):
        own = make_job(make_client(self.sales, "S"), self.sales, "Owned JD")
        hidden = make_job(make_client(self.sales_two, "T"), self.sales_two, "Hidden JD")
        self.as_user(self.hr)
        self.assertEqual(self.client.get(f"/api/v1/jobs/{own.id}/").status_code, 404)
        self.as_user(self.lead)
        self.assertEqual(self.client.get(f"/api/v1/jobs/{hidden.id}/").status_code, 200)
        assigned = self.client.post(
            f"/api/v1/jobs/{own.id}/assign/",
            {"recruiter_ids": [str(self.hr.id)]},
            format="json",
        )
        self.assertEqual(assigned.status_code, 200, assigned.data)
        rejected = self.client.post(
            f"/api/v1/jobs/{own.id}/assign/",
            {"recruiter_ids": [str(self.sales.id)]},
            format="json",
        )
        self.assertEqual(rejected.status_code, 400)
        self.as_user(self.hr)
        self.assertEqual(self.client.get(f"/api/v1/jobs/{own.id}/").status_code, 200)
        self.as_user(self.sales)
        self.assertEqual(self.client.post(f"/api/v1/jobs/{own.id}/match/").status_code, 403)
