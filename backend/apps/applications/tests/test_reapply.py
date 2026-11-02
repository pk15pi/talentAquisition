from apps.applications.models import Application, ApplicationHistory
from apps.applications.services import PIPELINE
from apps.testkit import SynfoAPITestCase, make_candidate, make_client, make_job


def move(client, application_id, status):
    return client.post(
        f"/api/v1/applications/{application_id}/change-status/",
        {"status": status},
        format="json",
    )


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
        jumped = move(self.client, created.data["id"], "JOINED")
        self.assertEqual(jumped.status_code, 400, jumped.data)
        self.assertEqual(jumped.data["code"], "invalid_transition")
        self.assertEqual(Application.objects.get(pk=created.data["id"]).status, "IDENTIFIED")
        for status in PIPELINE[1:]:
            step = move(self.client, created.data["id"], status)
            self.assertEqual(step.status_code, 200, step.data)
            self.assertEqual(step.data["status"], status)
        self.assertEqual(Application.objects.get(pk=created.data["id"]).status, "JOINED")
        blocked_exit = move(self.client, created.data["id"], "REJECTED")
        self.assertEqual(blocked_exit.status_code, 400, blocked_exit.data)
        self.assertEqual(Application.objects.get(pk=created.data["id"]).status, "JOINED")
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

    def test_illegal_jump_does_not_write_history_and_withdrawn_frees_the_slot(self):
        candidate = make_candidate(self.hr, email="withdraw@example.com", phone="9000000004")
        job = make_job(make_client(self.sales, "Withdraw Co"), self.sales, "Withdraw JD")
        self.as_user(self.hr)
        created = self.client.post(
            "/api/v1/applications/",
            {"candidate": str(candidate.id), "job": str(job.id)},
            format="json",
        )
        self.assertEqual(created.status_code, 201, created.data)
        self.assertEqual(created.data["candidate_name"], candidate.full_name)
        self.assertEqual(created.data["job_title"], job.title)
        before = ApplicationHistory.objects.filter(application_id=created.data["id"]).count()
        illegal = move(self.client, created.data["id"], "OFFERED")
        self.assertEqual(illegal.status_code, 400, illegal.data)
        self.assertEqual(illegal.data["code"], "invalid_transition")
        self.assertIn("CONTACTED", illegal.data["errors"]["allowed_statuses"])
        self.assertEqual(ApplicationHistory.objects.filter(application_id=created.data["id"]).count(), before)
        legal = move(self.client, created.data["id"], "WITHDRAWN")
        self.assertEqual(legal.status_code, 200, legal.data)
        self.assertEqual(legal.data["status"], "WITHDRAWN")
        again = self.client.post(
            "/api/v1/applications/",
            {"candidate": str(candidate.id), "job": str(job.id)},
            format="json",
        )
        self.assertEqual(again.status_code, 201, again.data)
