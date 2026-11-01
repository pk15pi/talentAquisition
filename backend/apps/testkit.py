from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.candidates.models import Candidate
from apps.clients.models import Client
from apps.jobs.models import Job


class SynfoAPITestCase(APITestCase):
    password = "longpassword1"

    @classmethod
    def setUpTestData(cls):
        call_command("bootstrap_groups")
        User = get_user_model()
        cls.admin = User.objects.create_user("admin", password=cls.password, role="ADMIN")
        cls.management = User.objects.create_user("mgmt", password=cls.password, role="MANAGEMENT")
        cls.sales = User.objects.create_user("sales", password=cls.password, role="SALES")
        cls.sales_two = User.objects.create_user("sales2", password=cls.password, role="SALES")
        cls.hr = User.objects.create_user("hr", password=cls.password, role="HR")
        cls.lead = User.objects.create_user("lead", password=cls.password, role="TEAM_LEAD")
        cls.root = User.objects.create_superuser("root", "root@example.com", cls.password)

    def as_user(self, user):
        self.client.force_authenticate(user=user)


def make_client(owner, name="Acme"):
    return Client.objects.create(company_name=name, sales_owner=owner, created_by=owner, status="ACTIVE")


def make_job(client, owner, title="Engineer"):
    return Job.objects.create(
        client=client,
        title=title,
        jd_text="Build software",
        experience_min=1,
        experience_max=4,
        sales_owner=owner,
        created_by=owner,
        status="OPEN",
    )


def make_candidate(user, email="asha@example.com", phone="9876543210", name="Asha Rao"):
    return Candidate.objects.create(
        full_name=name,
        email=email,
        phone=phone,
        sourced_by=user,
        consent_recorded_at=timezone.now(),
        privacy_notice_version="notice-1",
    )
