from datetime import datetime

from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common import RequiresPermission, query_uuid, INVALID_QUERY_ID

from .queries import hr_report, overview, sales_report

def report_filters(request):
    params = request.query_params
    filters = {}
    for name in ("date_from", "date_to"):
        raw = (params.get(name) or "").strip()
        if not raw:
            filters[name] = None
            continue
        try:
            filters[name] = datetime.strptime(raw, "%Y-%m-%d").date()
        except ValueError as exc:
            raise ValidationError({name: "Use YYYY-MM-DD."}) from exc
    if filters["date_from"] and filters["date_to"] and filters["date_from"] > filters["date_to"]:
        raise ValidationError({"date_to": "date_to is earlier than date_from."})
    for name in ("client", "job", "recruiter", "sales_executive", "department", "employee"):
        parsed = query_uuid(params.get(name))
        if parsed is INVALID_QUERY_ID:
            raise ValidationError({name: "Must be a UUID."})
        filters[name] = parsed
    status = (params.get("status") or "").strip()
    filters["status"] = status or None
    if status:
        from apps.applications.models import Application
        from apps.clients.models import Client
        from apps.jobs.models import Job

        known = set(Application.Status.values) | set(Client.Status.values) | set(Job.Status.values)
        if status not in known:
            raise ValidationError({"status": "Unknown status."})
    return filters


class OverviewReportView(APIView):
    permission_classes = [IsAuthenticated, RequiresPermission]
    required_permission = "reports.view_overview_report"

    def get(self, request, **kwargs):
        return Response(overview(request.user, report_filters(request)))


class HRReportView(APIView):
    permission_classes = [IsAuthenticated, RequiresPermission]
    required_permission = "reports.view_hr_report"

    def get(self, request, **kwargs):
        return Response(hr_report(request.user, report_filters(request)))


class SalesReportView(APIView):
    permission_classes = [IsAuthenticated, RequiresPermission]
    required_permission = "reports.view_sales_report"

    def get(self, request, **kwargs):
        return Response(sales_report(request.user, report_filters(request)))
