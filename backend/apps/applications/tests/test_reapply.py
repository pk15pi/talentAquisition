from apps.applications.models import Application
from apps.testkit import SynfoAPITestCase, make_candidate, make_client, make_job


class ReapplyTests(SynfoAPITestCase):
    def test_rejected_application_can_be_followed_by_a_new_active_one(self):
        candidate = make_candidate(self.hr, email="reapply@example.com", phone="9000000001")
        job = make_job(make_client(self.sales), self.sales)
        self.as_user(self.hr)
        first = self.client.post(
            "/api/v1/applications/",
            {"candidate": str(candidate.id), "job": str(job.id), "status": "JOINED"},
            format="json",
        )
        self.assertEqual(first.status_code, 201, first.data)
        self.assertEqual(first.data["status"], "IDENTIFIED")
        rejected = self.client.post(
            f"/api/v1/applications/{first.data['id']}/change-status/",
            {"status": "REJECTED", "remarks": "Not a fit"},
            format="json",
        )
        self.assertEqual(rejected.status_code, 200, rejected.data)
        second = self.client.post(
            "/api/v1/applications/",
            {"candidate": str(candidate.id), "job": str(job.id)},
            format="json",
        )
        self.assertEqual(second.status_code, 201, second.data)
        self.assertNotEqual(first.data["id"], second.data["id"])
        self.assertEqual(Application.objects.filter(candidate=candidate, job=job).count(), 2)
        self.assertTrue(Application.objects.filter(pk=first.data["id"], status="REJECTED").exists())
        blocked = self.client.post(
            "/api/v1/applications/",
            {"candidate": str(candidate.id), "job": str(job.id)},
            format="json",
        )
        self.assertEqual(blocked.status_code, 400)

    def test_joined_application_still_occupies_the_active_slot(self):
        candidate = make_candidate(self.hr, email="joined@example.com", phone="9000000002")
        job = make_job(make_client(self.sales, "Joined Co"), self.sales, "Joined JD")
        self.as_user(self.hr)
        created = self.client.post(
            "/api/v1/applications/",
            {"candidate": str(candidate.id), "job": str(job.id)},
            format="json",
        )
        self.client.post(
            f"/api/v1/applications/{created.data['id']}/change-status/",
            {"status": "JOINED"},
            format="json",
        )
        again = self.client.post(
            "/api/v1/applications/",
            {"candidate": str(candidate.id), "job": str(job.id)},
            format="json",
        )
        self.assertEqual(again.status_code, 400)
        self.assertEqual(Application.objects.filter(candidate=candidate, job=job).count(), 1)

    def test_recruiter_cannot_be_rewritten(self):
        candidate = make_candidate(self.hr, email="attr@example.com", phone="9000000003")
        job = make_job(make_client(self.sales, "Attr Co"), self.sales, "Attr JD")
        self.as_user(self.hr)
        created = self.client.post(
            "/api/v1/applications/",
            {"candidate": str(candidate.id), "job": str(job.id), "recruiter": str(self.lead.id)},
            format="json",
        )
        self.assertEqual(str(created.data["recruiter"]), str(self.hr.id))
        self.client.patch(
            f"/api/v1/applications/{created.data['id']}/",
            {"recruiter": str(self.lead.id), "status": "JOINED"},
            format="json",
        )
        row = Application.objects.get(pk=created.data["id"])
        self.assertEqual(row.recruiter_id, self.hr.id)
        self.assertEqual(row.status, "IDENTIFIED")
