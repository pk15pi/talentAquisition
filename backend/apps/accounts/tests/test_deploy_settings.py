from pathlib import Path
from unittest.mock import patch

from django.contrib.auth.models import Permission
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.test import Client, SimpleTestCase, override_settings

from apps.accounts.throttles import LoginRateThrottle
from apps.candidates.downloads import DOWNLOAD_MAX_AGE_SECONDS
from apps.candidates.models import Resume
from apps.testkit import SynfoAPITestCase, make_candidate
from config.security import DEFAULT_DEV_SECRET, resolve_secret_key
from config.storage import FILESYSTEM_BACKEND, S3_BACKEND, build_storages

ROOT = Path(__file__).resolve().parents[4]
GOOD_SECRET = "prod-" + "a1b2c3d4e5f6" * 5


class SecretKeyPolicyTests(SimpleTestCase):
    def test_debug_off_rejects_missing_sample_short_and_repetitive_keys(self):
        with self.assertRaises(ImproperlyConfigured):
            resolve_secret_key("", debug=False)
        with self.assertRaises(ImproperlyConfigured):
            resolve_secret_key(None, debug=False)
        long_sample = "dev-only-" + ("sample-key-" * 6)
        with self.assertRaises(ImproperlyConfigured):
            resolve_secret_key(long_sample, debug=False)
        with self.assertRaises(ImproperlyConfigured):
            resolve_secret_key("short-but-mixed", debug=False)
        with self.assertRaises(ImproperlyConfigured):
            resolve_secret_key("a" * 60, debug=False)
        self.assertEqual(resolve_secret_key(GOOD_SECRET, debug=False), GOOD_SECRET)

    def test_debug_keeps_the_sample_and_fills_a_missing_key(self):
        self.assertEqual(resolve_secret_key("", debug=True), DEFAULT_DEV_SECRET)
        self.assertEqual(resolve_secret_key("dev-only-local", debug=True), "dev-only-local")


class StorageSelectionTests(SimpleTestCase):
    def test_empty_bucket_stays_on_the_filesystem_without_a_migration(self):
        storages, enabled = build_storages(
            bucket="",
            access_key="",
            secret_key="",
            endpoint_url="",
            region_name="",
            addressing_style="",
            querystring_expire=300,
        )
        self.assertFalse(enabled)
        self.assertEqual(storages["default"]["BACKEND"], FILESYSTEM_BACKEND)
        self.assertEqual(Resume._meta.get_field("file").upload_to, "resumes/%Y/%m/")

    def test_bucket_requires_a_key_pair_and_stays_private(self):
        with self.assertRaises(ImproperlyConfigured):
            build_storages(
                bucket="resumes",
                access_key="only-one",
                secret_key="",
                endpoint_url="",
                region_name="",
                addressing_style="",
                querystring_expire=300,
            )
        storages, enabled = build_storages(
            bucket="resumes",
            access_key="",
            secret_key="",
            endpoint_url="https://s3.example",
            region_name="auto",
            addressing_style="path",
            querystring_expire=300,
        )
        self.assertTrue(enabled)
        options = storages["default"]["OPTIONS"]
        self.assertEqual(storages["default"]["BACKEND"], S3_BACKEND)
        self.assertTrue(options["querystring_auth"])
        self.assertIsNone(options["default_acl"])
        self.assertEqual(options["querystring_expire"], 300)
        self.assertNotIn("access_key", options)
        self.assertEqual(options["endpoint_url"], "https://s3.example")


class DeployArtifactTests(SimpleTestCase):
    def test_production_compose_has_no_runserver_or_source_mount(self):
        prod = (ROOT / "docker-compose.prod.yml").read_text()
        entrypoint = (ROOT / "backend" / "docker-entrypoint.sh").read_text()
        nginx = (ROOT / "deploy" / "nginx" / "default.conf").read_text()
        tls = (ROOT / "deploy" / "nginx" / "tls.conf.example").read_text()
        self.assertNotIn("runserver", prod)
        self.assertNotIn("web-dev", prod)
        self.assertNotIn("./backend:/app", prod)
        self.assertIn('command: ["web"]', prod)
        self.assertNotIn("makemigrations", entrypoint)
        self.assertIn("gunicorn", entrypoint)
        self.assertIn("web-dev", entrypoint)
        self.assertIn("location /media/", nginx)
        self.assertIn("return 404;", nginx)
        self.assertIn("ssl_certificate", tls)
        self.assertIn("location /media/", tls)


class LoginThrottleTests(SynfoAPITestCase):
    def test_token_and_admin_login_posts_are_throttled(self):
        cache.clear()
        # DRF copies the rate map onto the throttle class at import, so the test
        # patches that map instead of replacing REST_FRAMEWORK.
        with patch.dict(LoginRateThrottle.THROTTLE_RATES, {"login": "1/min"}):
            try:
                first = self.client.post(
                    "/api/v1/auth/token/",
                    {"username": "sales", "password": "wrong-password"},
                    format="json",
                )
                second = self.client.post(
                    "/api/v1/auth/token/",
                    {"username": "sales", "password": "wrong-password"},
                    format="json",
                )
                self.assertEqual(first.status_code, 401, first.data)
                self.assertEqual(second.status_code, 429, getattr(second, "data", second.content))

                admin = Client()
                page = admin.post("/admin/login/", {"username": "sales", "password": self.password})
                self.assertEqual(page.status_code, 429)
            finally:
                cache.clear()


class ObjectStorageDownloadTests(SynfoAPITestCase):
    def test_authorized_download_redirects_only_when_object_storage_is_on(self):
        candidate = make_candidate(self.hr, email="object@example.com", phone="9888888882", name="Object Person")
        from django.core.files.uploadedfile import SimpleUploadedFile

        resume = Resume.objects.create(
            candidate=candidate,
            file=SimpleUploadedFile("authorized.pdf", b"%PDF-1.4 object-bytes"),
            original_filename="authorized.pdf",
            file_hash="object-hash",
            parsed_text="OBJECT-PARSED",
            parsing_status="COMPLETED",
            is_primary=True,
            uploaded_by=self.hr,
        )
        permission = Permission.objects.get(content_type__app_label="candidates", codename="view_resume_content")
        self.sales.user_permissions.add(permission)
        self.sales = type(self.sales).objects.get(pk=self.sales.pk)
        self.as_user(self.sales)
        link = self.client.post(f"/api/v1/resumes/{resume.id}/download/")
        self.assertEqual(link.status_code, 200, link.data)
        self.client.force_authenticate(user=None)
        local = self.client.get(link.data["download_path"])
        self.assertEqual(local.status_code, 200)
        self.assertIn(b"object-bytes", b"".join(local.streaming_content))

        with override_settings(RESUME_OBJECT_STORAGE=True):
            with patch.object(
                resume.file.storage,
                "url",
                return_value="https://objects.example/signed?expires=300",
            ) as signed:
                redirected = self.client.get(link.data["download_path"])
        self.assertEqual(redirected.status_code, 302)
        self.assertEqual(redirected["Location"], "https://objects.example/signed?expires=300")
        self.assertEqual(signed.call_args.kwargs["expire"], DOWNLOAD_MAX_AGE_SECONDS)
        self.assertNotIn("/media/", redirected["Location"])
