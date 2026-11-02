"""Client submission workflow.

A new submission starts at PENDING. Later moves follow this map. The
application status is left alone: submitting a profile to a client does not
shortlist, reject, or advance the pipeline by itself.
"""

PENDING = "PENDING"
ACKNOWLEDGED = "ACKNOWLEDGED"
SHORTLISTED = "SHORTLISTED"
REJECTED = "REJECTED"
WITHDRAWN = "WITHDRAWN"

SUBMISSION_STATUSES = (PENDING, ACKNOWLEDGED, SHORTLISTED, REJECTED, WITHDRAWN)

SUBMISSION_TRANSITIONS = {
    PENDING: {ACKNOWLEDGED, REJECTED, WITHDRAWN},
    ACKNOWLEDGED: {SHORTLISTED, REJECTED, WITHDRAWN},
    SHORTLISTED: {REJECTED, WITHDRAWN},
    REJECTED: set(),
    WITHDRAWN: set(),
}


def submission_status_allowed(current: str, new_status: str) -> bool:
    if new_status not in SUBMISSION_TRANSITIONS:
        return False
    if new_status == current:
        return True
    return new_status in SUBMISSION_TRANSITIONS.get(current, set())
