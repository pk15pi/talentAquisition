from django.contrib import admin
from django.urls import include, path

from apps.accounts.throttles import ThrottledTokenObtainPairView, ThrottledTokenRefreshView

admin.site.site_header = "SynfoTalent"
admin.site.site_title = "SynfoTalent admin"
admin.site.index_title = "Recruitment operations"

from apps.reports.views import HRReportView, OverviewReportView, SalesReportView
from config.views import HealthView

api_patterns = [
    path("auth/token/", ThrottledTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("auth/token/refresh/", ThrottledTokenRefreshView.as_view(), name="token_refresh"),
    path("health/", HealthView.as_view(), name="health"),
    path("", include("apps.accounts.urls")),
    path("", include("apps.clients.urls")),
    path("", include("apps.sales.urls")),
    path("", include("apps.jobs.urls")),
    path("", include("apps.candidates.urls")),
    path("", include("apps.applications.urls")),
    path("", include("apps.recruitment.urls")),
    path("", include("apps.interviews.urls")),
    path("", include("apps.placements.urls")),
    path("", include("apps.billing.urls")),
    path("", include("apps.matching.urls")),
    path("", include("apps.organizations.urls")),
    path("reports/overview/", OverviewReportView.as_view(), name="report-overview"),
    path("reports/hr/", HRReportView.as_view(), name="report-hr"),
    path("reports/sales/", SalesReportView.as_view(), name="report-sales"),
]

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/<version>/", include(api_patterns)),
]
