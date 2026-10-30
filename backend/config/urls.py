from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from apps.reports.views import OverviewReportView, HRReportView, SalesReportView
urlpatterns = [
 path("admin/", admin.site.urls),
 path("api/v1/auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
 path("api/v1/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
 path("api/v1/", include("apps.accounts.urls")),
 path("api/v1/", include("apps.clients.urls")),
 path("api/v1/", include("apps.sales.urls")),
 path("api/v1/", include("apps.jobs.urls")),
 path("api/v1/", include("apps.candidates.urls")),
 path("api/v1/", include("apps.applications.urls")),
 path("api/v1/", include("apps.interviews.urls")),
 path("api/v1/", include("apps.placements.urls")),
 path("api/v1/", include("apps.billing.urls")),
 path("api/v1/", include("apps.matching.urls")),
 path("api/v1/reports/overview/", OverviewReportView.as_view()),
 path("api/v1/reports/hr/", HRReportView.as_view()),
 path("api/v1/reports/sales/", SalesReportView.as_view()),
]
if settings.DEBUG:
 urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
