import urllib.parse
from http.server import BaseHTTPRequestHandler

from api.shared import (ApiError, handle_error, json_response, rest_patch,
                        rest_select, verify_owner)


class handler(BaseHTTPRequestHandler):
    def do_DELETE(self):
        try:
            user = verify_owner(self.headers.get("Authorization"))
            path = urllib.parse.urlparse(self.path).path.rstrip("/")
            import_id = path.rsplit("/", 1)[-1]
            if not import_id or import_id in ("preview", "commit"):
                raise ApiError("Import id is required")
            filters = urllib.parse.urlencode({"id": f"eq.{import_id}", "user_id": f"eq.{user['id']}"})
            current = rest_select("exp_imports", filters + "&select=status")
            if not current:
                raise ApiError("Import preview not found", 404)
            if current[0]["status"] not in ("preview", "failed"):
                raise ApiError("Only an uncommitted preview can be cancelled", 409)
            rows = rest_patch("exp_imports", filters, {
                "status": "cancelled", "staged_payload": None, "error": None,
            })
            if not rows:
                raise ApiError("Import preview not found", 404)
            json_response(self, 200, {"ok": True})
        except Exception as exc:
            handle_error(self, exc)
