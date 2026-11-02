"""Rule-based candidate scoring.

Weights are fixed: skills 40, experience 25, responsibilities 15, location 10,
notice period 10. SkillAlias rows (and the skill's own alias list) count as
the same skill. A missing mandatory skill is flagged on the result. It does
not cap the score, reject the candidate, or shortlist them.

The match run row is inserted only after every score has been computed, inside
one transaction. A crash while scoring leaves no run behind.
"""

from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from django.db.models import Prefetch
from django.utils import timezone

from apps.candidates.models import Candidate

from .models import CandidateSkill, MatchResult, MatchRun, SkillAlias

WEIGHTS = {
    "skills": 40,
    "experience": 25,
    "responsibility": 15,
    "location": 10,
    "notice": 10,
}

RESPONSIBILITY_STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "from",
    "that",
    "this",
    "are",
    "was",
    "were",
    "you",
    "your",
    "our",
    "not",
    "but",
    "can",
    "will",
    "into",
    "over",
    "under",
    "than",
    "then",
    "such",
    "each",
    "per",
    "via",
    "job",
    "role",
}


def _clamp_score(value) -> Decimal:
    quantized = Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if quantized < 0:
        return Decimal("0.00")
    if quantized > 100:
        return Decimal("100.00")
    return quantized


def _normalize_token(value) -> str:
    return " ".join((value or "").strip().lower().split())


def _text_tokens(text) -> set[str]:
    import re

    words = re.findall(r"[a-z0-9+#.]{3,}", (text or "").lower())
    return {word for word in words if word not in RESPONSIBILITY_STOPWORDS}


def _alias_index():
    index = {}
    for skill_id, alias in SkillAlias.objects.values_list("skill_id", "normalized_alias"):
        index.setdefault(skill_id, set()).add(_normalize_token(alias))
    return index


def skill_tokens(skill, alias_index) -> set[str]:
    tokens = {_normalize_token(skill.normalized_name)}
    for alias in skill.aliases or []:
        if isinstance(alias, str):
            tokens.add(_normalize_token(alias))
    tokens.update(alias_index.get(skill.id, set()))
    tokens.discard("")
    return tokens


def _resume_text(candidate) -> str:
    resumes = list(candidate.resumes.all())
    primary = next((resume for resume in resumes if resume.is_primary and resume.parsed_text), None)
    if primary:
        return primary.parsed_text
    completed = [resume.parsed_text for resume in resumes if resume.parsed_text]
    return "\n".join(completed)


def score_candidate(job, candidate, job_skills, alias_index) -> dict:
    """Score one candidate. Does not write and does not read resume text into the result."""
    candidate_tokens = set()
    for candidate_skill in candidate.candidate_skills.all():
        candidate_tokens.update(skill_tokens(candidate_skill.skill, alias_index))

    matched_skills = []
    missing_skills = []
    missing_mandatory = []
    alias_matches = []
    matched_weight = 0
    total_weight = 0
    for job_skill in job_skills:
        tokens = skill_tokens(job_skill.skill, alias_index)
        total_weight += job_skill.weight
        overlap = tokens & candidate_tokens
        if overlap:
            matched_weight += job_skill.weight
            matched_skills.append(job_skill.skill.name)
            exact = _normalize_token(job_skill.skill.normalized_name) in candidate_tokens
            if not exact:
                alias = sorted(overlap)[0]
                alias_matches.append({"skill": job_skill.skill.name, "alias": alias})
        else:
            missing_skills.append(job_skill.skill.name)
            if job_skill.is_mandatory:
                missing_mandatory.append(job_skill.skill.name)

    if total_weight:
        skills_score = _clamp_score(Decimal(matched_weight) / Decimal(total_weight) * Decimal(100))
    else:
        skills_score = Decimal("50.00")

    experience = candidate.total_experience if candidate.total_experience is not None else Decimal("0")
    low = job.experience_min if job.experience_min is not None else Decimal("0")
    high = job.experience_max if job.experience_max is not None else Decimal("0")
    if high < low:
        experience_score = Decimal("0.00")
    elif low <= experience <= high:
        experience_score = Decimal("100.00")
    else:
        gap = min(abs(experience - low), abs(experience - high))
        experience_score = _clamp_score(Decimal(100) - (gap * Decimal(20)))

    job_location = (job.location or "").strip()
    candidate_location = candidate.location or ""
    if not job_location:
        location_score = Decimal("100.00")
        location_matched = True
    elif job_location.lower() in candidate_location.lower():
        location_score = Decimal("100.00")
        location_matched = True
    else:
        location_score = Decimal("40.00")
        location_matched = False

    job_terms = _text_tokens(job.jd_text)
    resume_text = _resume_text(candidate)
    resume_terms = _text_tokens(resume_text)
    if job_terms and resume_terms:
        overlap_terms = job_terms & resume_terms
        responsibility_score = _clamp_score(Decimal(len(overlap_terms)) / Decimal(len(job_terms)) * Decimal(100))
        responsibility_available = True
    else:
        overlap_terms = set()
        responsibility_score = Decimal("0.00")
        responsibility_available = bool(resume_terms) and bool(job_terms)

    job_notice = job.notice_period_days
    candidate_notice = candidate.notice_period_days
    if job_notice is None or candidate_notice is None or candidate_notice <= job_notice:
        notice_score = Decimal("100.00")
        notice_within = True
    else:
        notice_score = _clamp_score(Decimal(100) - Decimal(candidate_notice - job_notice))
        notice_within = False

    overall = _clamp_score(
        (
            skills_score * WEIGHTS["skills"]
            + experience_score * WEIGHTS["experience"]
            + responsibility_score * WEIGHTS["responsibility"]
            + location_score * WEIGHTS["location"]
            + notice_score * WEIGHTS["notice"]
        )
        / Decimal(100)
    )
    mandatory_failure = bool(missing_mandatory)
    explanation = {
        "weights": WEIGHTS,
        "matched_skills": sorted(matched_skills),
        "missing_skills": sorted(missing_skills),
        "missing_mandatory_skills": sorted(missing_mandatory),
        "mandatory_skill_failure": mandatory_failure,
        "mandatory_requirements_passed": not mandatory_failure,
        "alias_matches": sorted(alias_matches, key=lambda item: (item["skill"], item["alias"])),
        "experience": {
            "candidate_years": str(experience),
            "required_min": str(low),
            "required_max": str(high),
        },
        "location": {
            "job": job_location,
            "candidate": candidate_location,
            "matched": location_matched,
        },
        "responsibility": {
            "source": "resume_text",
            "available": responsibility_available,
            "matched_terms": sorted(overlap_terms),
        },
        "notice_period": {
            "job_days": job_notice,
            "candidate_days": candidate_notice,
            "within_limit": notice_within,
        },
        "automatic_action": "none",
    }
    return {
        "candidate": candidate,
        "skills_score": skills_score,
        "experience_score": experience_score,
        "location_score": location_score,
        "responsibility_score": responsibility_score,
        "notice_period_score": notice_score,
        "overall_score": overall,
        "missing_mandatory_skills": sorted(missing_mandatory),
        "explanation": explanation,
    }


def _scored_rows(job):
    alias_index = _alias_index()
    job_skills = list(job.job_skills.select_related("skill"))
    candidates = (
        Candidate.objects.filter(is_active=True)
        .prefetch_related(
            Prefetch("candidate_skills", queryset=CandidateSkill.objects.select_related("skill")),
            "resumes",
        )
        .order_by("id")
    )
    # Django 5.2 rejects iterator() after prefetch_related() unless chunk_size is set.
    rows = []
    for candidate in candidates.iterator(chunk_size=200):
        rows.append(score_candidate(job, candidate, job_skills, alias_index))
    return rows


def run_matching(job, user):
    rows = _scored_rows(job)
    with transaction.atomic():
        run = MatchRun.objects.create(
            job=job,
            initiated_by=user,
            engine_version="rules-v2",
            candidates_processed=len(rows),
        )
        MatchResult.objects.bulk_create(
            [
                MatchResult(
                    match_run=run,
                    candidate=row["candidate"],
                    skills_score=row["skills_score"],
                    experience_score=row["experience_score"],
                    location_score=row["location_score"],
                    responsibility_score=row["responsibility_score"],
                    notice_period_score=row["notice_period_score"],
                    overall_score=row["overall_score"],
                    missing_mandatory_skills=row["missing_mandatory_skills"],
                    explanation=row["explanation"],
                )
                for row in rows
            ]
        )
        run.completed_at = timezone.now()
        run.save(update_fields=["completed_at", "candidates_processed"])
    return run
