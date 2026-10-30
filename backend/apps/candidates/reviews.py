from .models import Candidate, DuplicateReview, Resume


def queue_identity_duplicate_reviews(candidate: Candidate):
    """Open a pending review when email or phone matches another person. Never merges."""
    if candidate.normalized_email:
        others = Candidate.objects.filter(normalized_email=candidate.normalized_email).exclude(pk=candidate.pk)
        for other in others:
            DuplicateReview.objects.get_or_create(
                candidate=candidate,
                matched_candidate=other,
                match_type=DuplicateReview.MatchType.EMAIL,
                defaults={"status": DuplicateReview.Status.PENDING},
            )
    if candidate.normalized_phone:
        others = Candidate.objects.filter(normalized_phone=candidate.normalized_phone).exclude(pk=candidate.pk)
        for other in others:
            DuplicateReview.objects.get_or_create(
                candidate=candidate,
                matched_candidate=other,
                match_type=DuplicateReview.MatchType.PHONE,
                defaults={"status": DuplicateReview.Status.PENDING},
            )


def queue_file_hash_reviews(candidate: Candidate, digest: str):
    if not digest:
        return
    other_ids = (
        Resume.objects.filter(file_hash=digest)
        .exclude(candidate=candidate)
        .values_list("candidate_id", flat=True)
        .distinct()
    )
    for other_id in other_ids:
        DuplicateReview.objects.get_or_create(
            candidate=candidate,
            matched_candidate_id=other_id,
            match_type=DuplicateReview.MatchType.FILE_HASH,
            defaults={"status": DuplicateReview.Status.PENDING},
        )
