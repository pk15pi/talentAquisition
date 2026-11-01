from django.db.models import Count, Sum
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.access import user_has
from apps.applications.models import Application
from apps.billing.models import Invoice, Payment
from apps.candidates.models import Candidate
from apps.clients.models import Client
from apps.common import RequiresPermission
from apps.jobs.models import Job
from apps.placements.models import Placement


class OverviewReportView(APIView):
    permission_classes = [IsAuthenticated, RequiresPermission]
    required_permission = "reports.view_overview_report"

    def get(self, request, **kwargs):
        user = request.user
        clients = Client.objects.all()
        jobs = Job.objects.filter(status="OPEN")
        if not user_has(user, "clients.view_all_clients"):
            clients = clients.filter(sales_owner=user)
        if not user_has(user, "jobs.view_all_jobs"):
            jobs = jobs.filter(sales_owner=user)
        if user_has(user, "candidates.view_candidate"):
            candidates = Candidate.objects.filter(is_active=True)
        else:
            candidates = Candidate.objects.none()
        applications = Application.objects.all()
        placements = Placement.objects.filter(status="JOINED")
        if not user_has(user, "applications.view_all_applications"):
            applications = applications.filter(recruiter=user)
            placements = placements.filter(application__recruiter=user)
        show_money = user_has(user, "reports.view_financial_report")
        return Response(
            {
                "clients": clients.count(),
                "open_jobs": jobs.count(),
                "candidates": candidates.count(),
                "applications": applications.count(),
                "joined_placements": placements.count() if user_has(user, "placements.view_placement") or show_money else 0,
                "invoiced_revenue": float(Invoice.objects.exclude(status="VOID").aggregate(v=Sum("total"))["v"] or 0) if show_money else 0,
                "payments_received": float(Payment.objects.aggregate(v=Sum("amount"))["v"] or 0) if show_money else 0,
            }
        )


class HRReportView(APIView):
    permission_classes = [IsAuthenticated, RequiresPermission]
    required_permission = "reports.view_hr_report"

    def get(self, request, **kwargs):
        applications = Application.objects.all()
        candidates = Candidate.objects.all()
        if not user_has(request.user, "applications.view_all_applications"):
            applications = applications.filter(recruiter=request.user)
        if not user_has(request.user, "candidates.view_candidate"):
            candidates = Candidate.objects.none()
        elif not user_has(request.user, "applications.view_all_applications"):
            candidates = candidates.filter(sourced_by=request.user)
        rows = applications.values("recruiter__id", "recruiter__first_name", "recruiter__last_name").annotate(applications=Count("id"))
        sourced = candidates.values("sourced_by__id", "sourced_by__first_name", "sourced_by__last_name").annotate(candidates_sourced=Count("id"))
        return Response({"applications_by_recruiter": list(rows), "candidates_sourced_by": list(sourced)})


class SalesReportView(APIView):
    permission_classes = [IsAuthenticated, RequiresPermission]
    required_permission = "reports.view_sales_report"

    def get(self, request, **kwargs):
        jobs = Job.objects.all()
        clients = Client.objects.all()
        if not user_has(request.user, "jobs.view_all_jobs"):
            jobs = jobs.filter(sales_owner=request.user)
        if not user_has(request.user, "clients.view_all_clients"):
            clients = clients.filter(sales_owner=request.user)
        return Response(
            {
                "jds_by_sales_owner": list(jobs.values("sales_owner__id", "sales_owner__first_name", "sales_owner__last_name").annotate(jds=Count("id"))),
                "clients_by_sales_owner": list(clients.values("sales_owner__id", "sales_owner__first_name", "sales_owner__last_name").annotate(clients=Count("id"))),
            }
        )
