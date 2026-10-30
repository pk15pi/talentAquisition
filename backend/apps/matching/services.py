from django.utils import timezone
from apps.candidates.models import Candidate
from .models import MatchRun,MatchResult
WEIGHTS={"skills":40,"experience":25,"responsibility":15,"location":10,"notice":10}
def run_matching(job,user):
    run=MatchRun.objects.create(job=job,initiated_by=user)
    job_skills=list(job.job_skills.select_related("skill"))
    candidates=Candidate.objects.filter(is_active=True).prefetch_related("candidate_skills__skill")
    results=[]
    # Phase 4: Django 5.2 raises ValueError when iterator() follows prefetch_related()
    # without chunk_size. Do not treat this engine as working until that call is fixed
    # and the unused skill weights/aliases are actually scored.
    for candidate in candidates.iterator():
        candidate_skill_names={cs.skill.normalized_name.lower() for cs in candidate.candidate_skills.all()}
        required={js.skill.normalized_name.lower() for js in job_skills}
        mandatory={js.skill.normalized_name.lower() for js in job_skills if js.is_mandatory}
        missing=sorted(mandatory-candidate_skill_names)
        skills_score=(len(required & candidate_skill_names)/len(required)*100) if required else 50
        exp=float(candidate.total_experience or 0); low=float(job.experience_min or 0); high=float(job.experience_max or 0)
        experience_score=100 if low<=exp<=high else max(0,100-min(abs(exp-low),abs(exp-high))*20) if high>=low else 0
        location_score=100 if not job.location or job.location.strip().lower() in (candidate.location or "").lower() else 40
        responsibility_score=skills_score
        notice_score=100 if job.notice_period_days is None or candidate.notice_period_days is None or candidate.notice_period_days<=job.notice_period_days else max(0,100-(candidate.notice_period_days-job.notice_period_days))
        overall=(skills_score*40+experience_score*25+responsibility_score*15+location_score*10+notice_score*10)/100
        if missing: overall=min(overall,49)
        results.append(MatchResult(match_run=run,candidate=candidate,skills_score=skills_score,experience_score=experience_score,location_score=location_score,responsibility_score=responsibility_score,notice_period_score=notice_score,overall_score=overall,missing_mandatory_skills=missing,explanation={"matched_skills":sorted(required & candidate_skill_names),"mandatory_requirements_passed":not bool(missing)}))
    MatchResult.objects.bulk_create(results)
    run.candidates_processed=len(results); run.completed_at=timezone.now(); run.save(update_fields=["candidates_processed","completed_at"])
    return run
