from django.contrib import admin
from .models import Application, ApplicationHistory
admin.site.register([Application, ApplicationHistory])
