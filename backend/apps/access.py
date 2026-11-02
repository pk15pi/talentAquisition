"""Default groups and permission codenames.

Groups are created once by ``bootstrap_groups``. Later edits an administrator
makes in Django admin are left in place, including which users belong to a
group. A new user receives the group for their role only from an explicit
provisioning call (``create_user``, ``create_superuser``, the admin add view,
or the user API create). Saves and logins do not add or remove memberships.
Checks use ``user.has_perm``, which already grants active superusers every
permission and denies inactive users.
"""

ROLE_TO_GROUP = {
    "ADMIN": "Administrator",
    "MANAGEMENT": "Management",
    "SALES": "Sales Executive",
    "HR": "HR Executive",
    "TEAM_LEAD": "Team Lead",
}

GROUP_ADMINISTRATOR = "Administrator"
GROUP_MANAGEMENT = "Management"
GROUP_SALES = "Sales Executive"
GROUP_HR = "HR Executive"
GROUP_TEAM_LEAD = "Team Lead"

# Codename strings are "app_label.codename".
SALES_PERMS = (
    "clients.view_client",
    "clients.add_client",
    "clients.change_client",
    "clients.own_client",
    "clients.view_clientcontact",
    "clients.add_clientcontact",
    "clients.change_clientcontact",
    "clients.view_clientactivity",
    "clients.add_clientactivity",
    "clients.change_clientactivity",
    "jobs.view_job",
    "jobs.add_job",
    "jobs.change_job",
    "sales.view_salesopportunity",
    "sales.add_salesopportunity",
    "sales.change_salesopportunity",
    "candidates.review_duplicate",
    "reports.view_overview_report",
    "reports.view_sales_report",
)

HR_PERMS = (
    "clients.view_client",
    "clients.view_all_clients",
    "clients.view_clientcontact",
    "clients.add_clientcontact",
    "clients.change_clientcontact",
    "clients.view_clientactivity",
    "clients.add_clientactivity",
    "clients.change_clientactivity",
    "jobs.view_job",
    "jobs.add_job",
    "jobs.change_job",
    "jobs.run_match",
    "jobs.be_assigned_recruiter",
    "candidates.view_candidate",
    "candidates.add_candidate",
    "candidates.change_candidate",
    "candidates.review_duplicate",
    "candidates.view_candidatenote",
    "candidates.add_candidatenote",
    "candidates.change_candidatenote",
    "candidates.view_resume",
    "candidates.add_resume",
    "candidates.change_resume",
    "matching.view_skill",
    "matching.add_skill",
    "matching.change_skill",
    "matching.view_candidateskill",
    "matching.add_candidateskill",
    "matching.change_candidateskill",
    "matching.view_jobskill",
    "matching.add_jobskill",
    "matching.change_jobskill",
    "applications.view_application",
    "applications.add_application",
    "applications.change_application",
    "applications.view_all_applications",
    "interviews.view_interview",
    "interviews.add_interview",
    "interviews.change_interview",
    "interviews.view_all_interviews",
    "placements.view_placement",
    "recruitment.view_submission",
    "recruitment.add_submission",
    "recruitment.change_submission",
    "reports.view_overview_report",
    "reports.view_hr_report",
)

TEAM_LEAD_EXTRA = (
    "jobs.view_all_jobs",
    "jobs.assign_recruiter",
    "accounts.view_user",
)

MANAGEMENT_PERMS = (
    "accounts.view_user",
    "clients.view_client",
    "clients.add_client",
    "clients.change_client",
    "clients.view_all_clients",
    "clients.assign_client_owner",
    "clients.own_client",
    "clients.view_clientcontact",
    "clients.add_clientcontact",
    "clients.change_clientcontact",
    "clients.view_clientactivity",
    "clients.add_clientactivity",
    "clients.change_clientactivity",
    "jobs.view_job",
    "jobs.add_job",
    "jobs.change_job",
    "jobs.view_all_jobs",
    "jobs.assign_recruiter",
    "jobs.assign_job_owner",
    "jobs.run_match",
    "candidates.view_candidate",
    "candidates.view_candidate_compensation",
    "candidates.add_candidate",
    "candidates.change_candidate",
    "candidates.review_duplicate",
    "candidates.view_candidatenote",
    "candidates.add_candidatenote",
    "candidates.change_candidatenote",
    "candidates.view_resume",
    "candidates.add_resume",
    "candidates.change_resume",
    "matching.view_skill",
    "matching.add_skill",
    "matching.change_skill",
    "matching.view_candidateskill",
    "matching.add_candidateskill",
    "matching.change_candidateskill",
    "matching.view_jobskill",
    "matching.add_jobskill",
    "matching.change_jobskill",
    "applications.view_application",
    "applications.add_application",
    "applications.change_application",
    "applications.view_all_applications",
    "interviews.view_interview",
    "interviews.add_interview",
    "interviews.change_interview",
    "interviews.view_all_interviews",
    "placements.view_placement",
    "placements.add_placement",
    "placements.change_placement",
    "placements.view_placement_financials",
    "placements.change_placement_financials",
    "recruitment.view_submission",
    "recruitment.add_submission",
    "recruitment.change_submission",
    "billing.view_invoice",
    "billing.add_invoice",
    "billing.change_invoice",
    "billing.view_invoiceline",
    "billing.add_invoiceline",
    "billing.change_invoiceline",
    "billing.view_payment",
    "billing.add_payment",
    "billing.change_payment",
    "billing.view_creditnote",
    "billing.add_creditnote",
    "billing.change_creditnote",
    "sales.view_salesopportunity",
    "sales.add_salesopportunity",
    "sales.change_salesopportunity",
    "sales.view_all_salesopportunity",
    "organizations.view_systemconfiguration",
    "organizations.change_systemconfiguration",
    "reports.view_overview_report",
    "reports.view_hr_report",
    "reports.view_sales_report",
    "reports.view_financial_report",
)

FINANCE_PERMS = (
    "placements.view_placement_financials",
    "placements.change_placement_financials",
    "billing.view_invoice",
    "billing.add_invoice",
    "billing.change_invoice",
    "billing.delete_invoice",
    "billing.view_invoiceline",
    "billing.add_invoiceline",
    "billing.change_invoiceline",
    "billing.delete_invoiceline",
    "billing.view_payment",
    "billing.add_payment",
    "billing.change_payment",
    "billing.delete_payment",
    "billing.view_creditnote",
    "billing.add_creditnote",
    "billing.change_creditnote",
    "billing.delete_creditnote",
    "reports.view_financial_report",
)


def user_has(user, permission: str) -> bool:
    return bool(user and user.is_authenticated and user.has_perm(permission))


def visible_clients(user):
    from apps.clients.models import Client

    queryset = Client.objects.all()
    if user_has(user, "clients.view_all_clients"):
        return queryset
    return queryset.filter(sales_owner=user)


def visible_jobs(user):
    from django.db.models import Q

    from apps.jobs.models import Job

    queryset = Job.objects.all()
    if user_has(user, "jobs.view_all_jobs"):
        return queryset
    return queryset.filter(
        Q(sales_owner=user) | Q(assignments__recruiter=user, assignments__is_active=True)
    ).distinct()


def visible_applications(user):
    from django.db.models import Q

    from apps.applications.models import Application

    queryset = Application.objects.all()
    if user_has(user, "applications.view_all_applications"):
        return queryset
    return queryset.filter(
        Q(recruiter=user)
        | Q(job__sales_owner=user)
        | Q(job__assignments__recruiter=user, job__assignments__is_active=True)
    ).distinct()


def visible_interviews(user):
    from django.db.models import Q

    from apps.interviews.models import Interview

    queryset = Interview.objects.all()
    if user_has(user, "interviews.view_all_interviews"):
        return queryset
    return queryset.filter(
        Q(application__recruiter=user)
        | Q(application__job__sales_owner=user)
        | Q(application__job__assignments__recruiter=user, application__job__assignments__is_active=True)
    ).distinct()


def visible_opportunities(user):
    from apps.sales.models import SalesOpportunity

    queryset = SalesOpportunity.objects.all()
    if user_has(user, "sales.view_all_salesopportunity"):
        return queryset
    return queryset.filter(owner=user)
