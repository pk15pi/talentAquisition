from django.contrib import admin
from .models import Interview, InterviewEvent, InterviewParticipant
admin.site.register([Interview, InterviewEvent, InterviewParticipant])
