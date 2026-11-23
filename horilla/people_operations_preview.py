"""Serve the People Operations prototype as static files.

The pages use fictional review data and are not wired to the HR database.
A staging login is required. The file rules match the prototype's own preview
server so tests, SQL, and hidden files are not served.
"""

from pathlib import Path

from django.contrib.auth.decorators import login_required
from django.http import FileResponse, HttpResponse, HttpResponseNotAllowed, HttpResponseRedirect

ROOT = Path(__file__).resolve().parent.parent / "prototypes" / "bevy-people-operations-suite"
ROUTES = {
    "hr": ROOT / "apps" / "hr-portal" / "web",
    "expenses": ROOT / "apps" / "expenses" / "dist",
    "insurance": ROOT / "apps" / "insurance",
    "daily-updates": ROOT / "apps" / "daily-updates",
}
TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".mjs": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".svg": "image/svg+xml",
    ".pdf": "application/pdf",
}
HEADERS = {
    "Cache-Control": "no-store",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "SAMEORIGIN",
    "Referrer-Policy": "no-referrer",
}


def _response(status, body=""):
    response = HttpResponse(body, status=status, content_type="text/plain; charset=utf-8")
    for key, value in HEADERS.items():
        response[key] = value
    return response


def _preview_file(module, relative):
    if module not in ROUTES:
        return None
    if "\\" in relative or any(part in {"", ".", ".."} or part.startswith(".") for part in relative.split("/")):
        return None
    if module == "insurance" and relative not in {"index.html", "config.js", "logic.js"}:
        return None
    if "/" in relative and not (
        module == "hr" and relative.startswith("expenses/") and "/" not in relative[9:]
    ):
        return None
    name = Path(relative).name
    extension = Path(name).suffix
    if name.endswith((".test.js", ".test.mjs", ".test.cjs")) or name == "backend-check.mjs" or extension not in TYPES:
        return None
    candidate = (ROUTES[module] / relative).resolve()
    root = ROUTES[module].resolve()
    if root not in candidate.parents or not candidate.is_file():
        return None
    return candidate


@login_required
def people_operations_preview(request, module=None, relative=""):
    if request.method not in {"GET", "HEAD"}:
        return HttpResponseNotAllowed(["GET", "HEAD"])
    if module is None:
        page = ROOT / "index.html"
        if not page.is_file():
            return _response(404, "Not found")
        response = FileResponse(page.open("rb"), content_type=TYPES[".html"])
        for key, value in HEADERS.items():
            response[key] = value
        return response
    if not relative:
        return HttpResponseRedirect(f"/{module}/")
    relative = relative[1:] if relative.startswith("/") else relative
    if not relative:
        relative = "index.html"
    target = _preview_file(module, relative)
    if target is None:
        return _response(404, "Not found")
    response = FileResponse(target.open("rb"), content_type=TYPES[target.suffix])
    for key, value in HEADERS.items():
        response[key] = value
    return response
