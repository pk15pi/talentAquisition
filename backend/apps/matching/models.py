from django.conf import settings
from django.db import models
from django.db.models import Q
class Skill(models.Model):
    name=models.CharField(max_length=100); normalized_name=models.CharField(max_length=100,unique=True); category=models.CharField(max_length=100,blank=True); aliases=models.JSONField(default=list,blank=True); is_active=models.BooleanField(default=True)
    def __str__(self): return self.name
class CandidateSkill(models.Model):
    candidate=models.ForeignKey("candidates.Candidate",on_delete=models.CASCADE,related_name="candidate_skills")
    skill=models.ForeignKey(Skill,on_delete=models.PROTECT); experience_months=models.PositiveIntegerField(null=True,blank=True)
    class Meta: constraints=[models.UniqueConstraint(fields=["candidate","skill"],name="unique_candidate_skill")]
class JobSkill(models.Model):
    job=models.ForeignKey("jobs.Job",on_delete=models.CASCADE,related_name="job_skills")
    skill=models.ForeignKey(Skill,on_delete=models.PROTECT); is_mandatory=models.BooleanField(default=False); weight=models.PositiveIntegerField(default=1)
    class Meta: constraints=[models.UniqueConstraint(fields=["job","skill"],name="unique_job_skill"),models.CheckConstraint(condition=Q(weight__gte=1,weight__lte=10),name="job_skill_weight_range")]
class MatchRun(models.Model):
    job=models.ForeignKey("jobs.Job",on_delete=models.CASCADE,related_name="match_runs"); initiated_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    engine_version=models.CharField(max_length=30,default="rules-v1"); candidates_processed=models.PositiveIntegerField(default=0)
    started_at=models.DateTimeField(auto_now_add=True); completed_at=models.DateTimeField(null=True,blank=True)
class MatchResult(models.Model):
    match_run=models.ForeignKey(MatchRun,on_delete=models.CASCADE,related_name="results"); candidate=models.ForeignKey("candidates.Candidate",on_delete=models.CASCADE)
    skills_score=models.DecimalField(max_digits=5,decimal_places=2); experience_score=models.DecimalField(max_digits=5,decimal_places=2)
    location_score=models.DecimalField(max_digits=5,decimal_places=2); responsibility_score=models.DecimalField(max_digits=5,decimal_places=2)
    notice_period_score=models.DecimalField(max_digits=5,decimal_places=2); overall_score=models.DecimalField(max_digits=5,decimal_places=2)
    missing_mandatory_skills=models.JSONField(default=list); explanation=models.JSONField(default=dict); created_at=models.DateTimeField(auto_now_add=True)
    class Meta: constraints=[models.UniqueConstraint(fields=["match_run","candidate"],name="unique_candidate_per_match_run"),models.CheckConstraint(condition=Q(overall_score__gte=0,overall_score__lte=100),name="match_score_range")]
