from django.contrib import admin
from .models import Skill, CandidateSkill, JobSkill, MatchRun, MatchResult
admin.site.register([Skill, CandidateSkill, JobSkill, MatchRun, MatchResult])
