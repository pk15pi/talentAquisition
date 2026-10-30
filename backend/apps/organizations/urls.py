from django.urls import path

from .views import SystemConfigurationView

urlpatterns = [
    path("system-configuration/", SystemConfigurationView.as_view(), name="system-configuration"),
]
