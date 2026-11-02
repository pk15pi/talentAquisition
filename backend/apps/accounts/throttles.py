"""Login throttles for the JWT endpoints and the Django admin form.

Rates come from ``DEFAULT_THROTTLE_RATES['login']``. Production Compose points
the cache at Redis so Gunicorn workers share one counter. Without ``CACHE_URL``
the counter is per process.
"""

from django.http import HttpResponse
from rest_framework.throttling import SimpleRateThrottle
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView


class LoginRateThrottle(SimpleRateThrottle):
    scope = "login"

    def get_cache_key(self, request, view):
        return self.cache_format % {"scope": self.scope, "ident": self.get_ident(request)}


class ThrottledTokenObtainPairView(TokenObtainPairView):
    throttle_classes = [LoginRateThrottle]


class ThrottledTokenRefreshView(TokenRefreshView):
    throttle_classes = [LoginRateThrottle]


class AdminLoginRateLimitMiddleware:
    """Count POST /admin/login/ before CSRF so a missing token still costs a try."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method == "POST" and request.path.rstrip("/") == "/admin/login":
            throttle = LoginRateThrottle()
            if not throttle.allow_request(request, None):
                return HttpResponse(
                    "Too many login attempts. Try again shortly.",
                    status=429,
                    content_type="text/plain",
                )
        return self.get_response(request)
