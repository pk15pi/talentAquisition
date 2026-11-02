"""Short-lived signed resume download tokens.

The token names the user and the resume. Redeeming it checks that user again
for ``candidates.view_resume_content``. The file is never served from ``/media/``.
"""

from urllib.parse import quote

from django.core.signing import BadSignature, SignatureExpired, TimestampSigner

DOWNLOAD_SALT = "synfotalent-resume-download"
DOWNLOAD_MAX_AGE_SECONDS = 300


def _signer():
    return TimestampSigner(salt=DOWNLOAD_SALT)


def make_download_token(user, resume) -> str:
    return _signer().sign(f"{user.pk}:{resume.pk}")


def download_path(token: str) -> str:
    return f"/api/v1/resume-downloads/?token={quote(token, safe='')}"


def read_download_token(token: str):
    try:
        raw = _signer().unsign(token, max_age=DOWNLOAD_MAX_AGE_SECONDS)
    except SignatureExpired:
        return None, "expired"
    except BadSignature:
        return None, "invalid"
    user_id, separator, resume_id = raw.partition(":")
    if not separator or not user_id or not resume_id:
        return None, "invalid"
    return (user_id, resume_id), None
