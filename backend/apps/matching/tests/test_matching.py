from decimal import Decimal
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile

from apps.applications.models import Application
from apps.candidates.models import Resume
from apps.matching.models import JobSkill, MatchRun, Skill, SkillAlias
from apps.matching.services import run_matching
from apps.testkit import SynfoAPITestCase, make_candidate, make_client, make_job


class MatchingEngineTests(SynfoAPITestCase):
    def setUp(self):
        super().setUp()
        self.company = make_client(self.sales, "Match Client")
        self.job = make_job(self.company, self.sales, "Backend Engineer")
        self.job.jd_text = "backend apis"
        self.job.location = "Pune"
        self.job.experience_min = Decimal("2.0")
        self.job.experience_max = Decimal("5.0")
        self.job.notice_period_days = 30
        self.job.save()
        self.python = Skill.objects.create(name="Python", normalized_name="python")
        SkillAlias.objects.create(skill=self.python, alias="Py")
        self.django = Skill.objects.create(name="Django", normalized_name="django")
        JobSkill.objects.create(job=self.job, skill=self.python, is_mandatory=True, weight=3)
        JobSkill.objects.create(job=self.job, skill=self.django, is_mandatory=False, weight=1)

    def _candidate(self, email, phone, name, skill=None, active=True):
        candidate = make_candidate(self.hr, email=email, phone=phone, name=name)
        candidate.total_experience = Decimal("3.0")
        candidate.location = "Pune"
        candidate.notice_period_days = 15
        candidate.is_active = active
        candidate.save()
        Resume.objects.create(
            candidate=candidate,
            file=SimpleUploadedFile(f"{name}.pdf", b"%PDF resume"),
            original_filename=f"{name}.pdf",
            parsed_text="backend apis",
            parsing_status="COMPLETED",
            is_primary=True,
            uploaded_by=self.hr,
        )
        if skill is not None:
            from apps.matching.models import CandidateSkill

            CandidateSkill.objects.create(candidate=candidate, skill=skill)
        return candidate

    def test_scores_aliases_flags_mandatory_gaps_and_does_not_decide(self):
        alias_skill = Skill.objects.create(name="Py", normalized_name="py")
        matched = self._candidate("alias@example.com", "9100000001", "Alias Person", skill=alias_skill)
        missed = self._candidate("miss@example.com", "9100000002", "Missing Person")
        inactive = self._candidate("inactive@example.com", "9100000003", "Inactive Person", skill=alias_skill, active=False)
        application = Application.objects.create(candidate=matched, job=self.job, recruiter=self.hr)
        before = MatchRun.objects.count()
        self.as_user(self.sales)
        denied = self.client.post(f"/api/v1/jobs/{self.job.id}/match/")
        self.assertEqual(denied.status_code, 403)
        self.assertEqual(MatchRun.objects.count(), before)

        self.as_user(self.lead)
        response = self.client.post(f"/api/v1/jobs/{self.job.id}/match/")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["engine_version"], "rules-v2")
        self.assertEqual(response.data["candidates_processed"], 2)
        self.assertEqual(MatchRun.objects.count(), before + 1)
        by_name = {row["candidate_name"]: row for row in response.data["results"]}
        self.assertNotIn(inactive.full_name, by_name)
        alias_row = by_name["Alias Person"]
        missing_row = by_name["Missing Person"]
        self.assertEqual(alias_row["explanation"]["weights"], {
            "skills": 40,
            "experience": 25,
            "responsibility": 15,
            "location": 10,
            "notice": 10,
        })
        self.assertFalse(alias_row["mandatory_skill_failure"])
        self.assertEqual(alias_row["explanation"]["alias_matches"], [{"skill": "Python", "alias": "py"}])
        self.assertEqual(alias_row["skills_score"], "75.00")
        self.assertEqual(alias_row["responsibility_score"], "100.00")
        self.assertNotEqual(alias_row["skills_score"], alias_row["responsibility_score"])
        self.assertEqual(alias_row["overall_score"], "90.00")
        self.assertEqual(alias_row["explanation"]["automatic_action"], "none")
        self.assertTrue(missing_row["mandatory_skill_failure"])
        self.assertEqual(missing_row["missing_mandatory_skills"], ["Python"])
        self.assertTrue(missing_row["explanation"]["mandatory_skill_failure"])
        self.assertEqual(missing_row["overall_score"], "60.00")
        self.assertGreater(Decimal(missing_row["overall_score"]), Decimal("49"))
        application.refresh_from_db()
        self.assertEqual(application.status, "IDENTIFIED")
        self.assertEqual(Application.objects.filter(job=self.job).count(), 1)

    def test_scoring_failure_does_not_leave_a_match_run(self):
        self._candidate("boom@example.com", "9100000004", "Boom Person")
        before = MatchRun.objects.count()
        with patch("apps.matching.services.score_candidate", side_effect=RuntimeError("boom")):
            with self.assertRaises(RuntimeError):
                run_matching(self.job, self.lead)
        self.assertEqual(MatchRun.objects.count(), before)
