from django.db.models import Count,Sum
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from apps.common import RolePermission
from apps.clients.models import Client
from apps.jobs.models import Job
from apps.candidates.models import Candidate
from apps.applications.models import Application
from apps.placements.models import Placement
from apps.billing.models import Invoice,Payment
class OverviewReportView(APIView):
    permission_classes=[IsAuthenticated,RolePermission]
    allowed_roles=("ADMIN","MANAGEMENT","SALES","HR","TEAM_LEAD")
    def get(self,request):
        clients=Client.objects.all(); jobs=Job.objects.filter(status="OPEN"); candidates=Candidate.objects.filter(is_active=True); applications=Application.objects.all(); placements=Placement.objects.filter(status="JOINED")
        if request.user.role=="SALES": clients=clients.filter(sales_owner=request.user); jobs=jobs.filter(sales_owner=request.user); candidates=Candidate.objects.none(); applications=Application.objects.none(); placements=Placement.objects.none()
        elif request.user.role=="HR": applications=applications.filter(recruiter=request.user); placements=placements.filter(application__recruiter=request.user)
        return Response({"clients":clients.count(),"open_jobs":jobs.count(),"candidates":candidates.count(),"applications":applications.count(),"joined_placements":placements.count(),"invoiced_revenue":float(Invoice.objects.exclude(status="VOID").aggregate(v=Sum("total"))["v"] or 0) if request.user.role in ("ADMIN","MANAGEMENT") else 0,"payments_received":float(Payment.objects.aggregate(v=Sum("amount"))["v"] or 0) if request.user.role in ("ADMIN","MANAGEMENT") else 0})
class HRReportView(APIView):
    permission_classes=[IsAuthenticated,RolePermission]
    allowed_roles=("ADMIN","MANAGEMENT","HR","TEAM_LEAD")
    def get(self,request):
        applications=Application.objects.all(); candidates=Candidate.objects.all()
        if request.user.role=="HR": applications=applications.filter(recruiter=request.user); candidates=candidates.filter(sourced_by=request.user)
        rows=applications.values("recruiter__id","recruiter__first_name","recruiter__last_name").annotate(applications=Count("id"))
        sourced=candidates.values("sourced_by__id","sourced_by__first_name","sourced_by__last_name").annotate(candidates_sourced=Count("id"))
        return Response({"applications_by_recruiter":list(rows),"candidates_sourced_by":list(sourced)})
class SalesReportView(APIView):
    permission_classes=[IsAuthenticated,RolePermission]
    allowed_roles=("ADMIN","MANAGEMENT","SALES")
    def get(self,request):
        jobs=Job.objects.all(); client_qs=Client.objects.all()
        if request.user.role=="SALES": jobs=jobs.filter(sales_owner=request.user); client_qs=client_qs.filter(sales_owner=request.user)
        rows=jobs.values("sales_owner__id","sales_owner__first_name","sales_owner__last_name").annotate(jds=Count("id"))
        clients=client_qs.values("sales_owner__id","sales_owner__first_name","sales_owner__last_name").annotate(clients=Count("id"))
        return Response({"jds_by_sales_owner":list(rows),"clients_by_sales_owner":list(clients)})
