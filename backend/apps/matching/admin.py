from django.contrib import admin
from .models import Skill, SkillAlias, CandidateSkill, JobSkill, MatchRun, MatchResult
admin.site.register([Skill, SkillAlias, CandidateSkill, JobSkill, MatchRun, MatchResult])
