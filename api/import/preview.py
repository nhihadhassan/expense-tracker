import cgi
import hashlib
import urllib.parse
from http.server import BaseHTTPRequestHandler

from api.shared import (MAX_UPLOAD_BYTES, ApiError, handle_error, import_summary,
                        json_response, parse_upload, rest_insert, rest_select,
                        verify_owner)


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            user = verify_owner(self.headers.get("Authorization"))
            length = int(self.headers.get("Content-Length", "0") or 0)
            if length > MAX_UPLOAD_BYTES + 65536:
                raise ApiError("Statement files must be 4 MB or smaller", 413)
            content_type, _ = cgi.parse_header(self.headers.get("Content-Type", ""))
            if content_type != "multipart/form-data":
                raise ApiError("Expected a multipart upload with a file field")
            form = cgi.FieldStorage(
                fp=self.rfile,
                headers=self.headers,
                environ={"REQUEST_METHOD": "POST", "CONTENT_TYPE": self.headers["Content-Type"]},
            )
            item = form["file"] if "file" in form else None
            if item is None or not getattr(item, "file", None):
                raise ApiError("Choose a statement file to preview")
            data = item.file.read(MAX_UPLOAD_BYTES + 1)
            if len(data) > MAX_UPLOAD_BYTES:
                raise ApiError("Statement files must be 4 MB or smaller", 413)

            file_hash = hashlib.sha256(data).hexdigest()
            query = urllib.parse.urlencode({
                "select": "id,summary,committed_at",
                "user_id": f"eq.{user['id']}",
                "file_hash": f"eq.{file_hash}",
                "status": "eq.committed",
                "limit": "1",
            })
            prior = rest_select("exp_imports", query)
            if prior:
                raise ApiError("This exact file was already imported", 409)

            parsed = parse_upload(data, item.filename or "statement")
            summary = import_summary(parsed)
            payload = {key: parsed[key] for key in ("transactions", "chequing", "payments", "statements")}
            rows = rest_insert("exp_imports", [{
                "user_id": user["id"],
                "file_name": parsed["file_name"],
                "file_hash": parsed["file_hash"],
                "institution": parsed["institution"],
                "account": parsed["account"],
                "status": "preview",
                "summary": summary,
                "staged_payload": payload,
            }])
            if not rows:
                raise ApiError("Could not stage this import", 500)
            json_response(self, 200, {"ok": True, "importId": rows[0]["id"], **summary})
        except Exception as exc:
            handle_error(self, exc)
