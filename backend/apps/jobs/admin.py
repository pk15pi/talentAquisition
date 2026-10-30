from django.contrib import admin
from .models import Job, JobAssignment, JobStatusHistory
admin.site.register([Job, JobAssignment, JobStatusHistory])
