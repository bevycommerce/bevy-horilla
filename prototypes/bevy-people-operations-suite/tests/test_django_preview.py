"""Exercise the staging preview without company settings, models or a database."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest

from django.conf import settings

if not settings.configured:
    settings.configure(INSTALLED_APPS=["django.contrib.auth", "django.contrib.contenttypes"], SECRET_KEY="fictional-preview-test", ROOT_URLCONF=__name__, ALLOWED_HOSTS=["testserver"], LOGIN_URL="/login/")

import django

django.setup()
from django.test import RequestFactory
from django.urls import path, re_path

REPO = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location("preview_under_test", REPO / "horilla" / "people_operations_preview.py")
preview = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preview)
urlpatterns = [path("login/", lambda request: None), re_path(r"^(?P<module>hr|expenses|insurance|daily-updates)(?P<relative>/.*)?$", preview.people_operations_preview)]


class PreviewTests(unittest.TestCase):
    def request(self, module="hr", relative="/", method="get", authenticated=True):
        request = getattr(RequestFactory(), method)("/" + module + (relative or ""))
        request.user = SimpleNamespace(is_authenticated=authenticated)
        response = preview.people_operations_preview(request, module, relative)
        self.addCleanup(response.close)
        return response

    def test_slash_serves_index_instead_of_redirecting_to_itself(self):
        for module in preview.ROUTES:
            with self.subTest(module=module):
                response = self.request(module)
                self.assertEqual(response.status_code, 200)
                self.assertIn("text/html", response["Content-Type"])

    def test_bare_route_redirects_once(self):
        for relative in ("", None):
            response = self.request(relative=relative)
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response["Location"], "/hr/")

    def test_signed_out_users_cannot_read_pages_or_direct_assets(self):
        for relative in ("/", "/seed.mjs", "/expenses/engine.js"):
            response = self.request(relative=relative, authenticated=False)
            self.assertEqual(response.status_code, 302)
            self.assertTrue(response["Location"].startswith("/login/"))

    def test_allowlisted_assets_and_no_store_headers(self):
        for relative in ("/app.js", "/seed.mjs", "/expenses/engine.js"):
            response = self.request(relative=relative)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response["Cache-Control"], "no-store")
            self.assertEqual(response["X-Content-Type-Options"], "nosniff")

    def test_private_source_traversal_tests_and_writes_are_blocked(self):
        for relative in ("/../package.json", "/.env", "/expenses/../seed.mjs", "/test.test.js", "/\\secret"):
            self.assertEqual(self.request(relative=relative).status_code, 404)
        self.assertEqual(self.request("daily-updates", "/schema.sql").status_code, 404)
        self.assertEqual(self.request("insurance", "/apps-script/Code.gs").status_code, 404)
        self.assertEqual(self.request(method="post").status_code, 405)
        self.assertEqual(self.request(method="head").status_code, 200)


if __name__ == "__main__":
    unittest.main()
