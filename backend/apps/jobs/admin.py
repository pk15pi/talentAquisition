from django.contrib import admin
from .models import Job, JobAssignment, JobAssignmentHistory, JobStatusHistory
admin.site.register([Job, JobAssignment, JobAssignmentHistory, JobStatusHistory])
