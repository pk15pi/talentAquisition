"""Choose local disk or private S3-compatible storage.

Resume ``FileField`` values stay ``resumes/%Y/%m/<filename>``. Turning a bucket
on does not rewrite those keys. Copy any existing objects to the same keys
before setting ``AWS_STORAGE_BUCKET_NAME``. There is no schema migration.
"""

from django.core.exceptions import ImproperlyConfigured

FILESYSTEM_BACKEND = "django.core.files.storage.FileSystemStorage"
STATICFILES_BACKEND = "django.contrib.staticfiles.storage.StaticFilesStorage"
S3_BACKEND = "storages.backends.s3.S3Storage"
# Collected admin assets must be readable by Nginx (uid 101). Resume uploads keep
# the tighter FILE_UPLOAD_* modes and are not mounted into the web container.
STATICFILES_OPTIONS = {
    "file_permissions_mode": 0o644,
    "directory_permissions_mode": 0o755,
}


def build_storages(
    *,
    bucket: str,
    access_key: str,
    secret_key: str,
    endpoint_url: str,
    region_name: str,
    addressing_style: str,
    querystring_expire: int,
) -> tuple[dict, bool]:
    staticfiles = {"BACKEND": STATICFILES_BACKEND, "OPTIONS": STATICFILES_OPTIONS}
    bucket = (bucket or "").strip()
    access_key = (access_key or "").strip()
    secret_key = (secret_key or "").strip()
    endpoint_url = (endpoint_url or "").strip()
    region_name = (region_name or "").strip()
    addressing_style = (addressing_style or "").strip()
    if not bucket:
        return (
            {"default": {"BACKEND": FILESYSTEM_BACKEND}, "staticfiles": staticfiles},
            False,
        )
    if bool(access_key) != bool(secret_key):
        raise ImproperlyConfigured(
            "Set both AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY, or leave both empty to use an instance role."
        )
    if querystring_expire < 1:
        raise ImproperlyConfigured("AWS_QUERYSTRING_EXPIRE must be at least 1 second.")
    options = {
        "bucket_name": bucket,
        "querystring_auth": True,
        "querystring_expire": querystring_expire,
        "default_acl": None,
        "file_overwrite": False,
        "object_parameters": {"CacheControl": "private, no-store"},
    }
    if endpoint_url:
        options["endpoint_url"] = endpoint_url
    if region_name:
        options["region_name"] = region_name
    if access_key:
        options["access_key"] = access_key
        options["secret_key"] = secret_key
    if addressing_style:
        options["addressing_style"] = addressing_style
    return (
        {"default": {"BACKEND": S3_BACKEND, "OPTIONS": options}, "staticfiles": staticfiles},
        True,
    )
