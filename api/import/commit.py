import json
import urllib.parse
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler

from api.shared import (ApiError, handle_error, json_response, rest_insert,
                        rest_patch, rest_select, rest_upsert, utc_now,
                        verify_owner)


def _filters(import_id, user_id):
    return urllib.parse.urlencode({"id": f"eq.{import_id}", "user_id": f"eq.{user_id}"})


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            user = verify_owner(self.headers.get("Authorization"))
            length = int(self.headers.get("Content-Length", "0") or 0)
            body = json.loads(self.rfile.read(length) or b"{}")
            import_id = body.get("importId")
            if not import_id:
                raise ApiError("importId is required")
            query = _filters(import_id, user["id"]) + "&select=*"
            rows = rest_select("exp_imports", query)
            if not rows:
                raise ApiError("Import preview not found", 404)
            batch = rows[0]
            if batch["status"] == "committed":
                json_response(self, 200, {"ok": True, "alreadyCommitted": True, **(batch.get("summary") or {})})
                return
            if batch["status"] not in ("preview", "failed", "committing"):
                raise ApiError("This import can no longer be committed", 409)
            expires_at = (batch.get("expires_at") or "").replace("Z", "+00:00")
            if expires_at and datetime.fromisoformat(expires_at) <= datetime.now(timezone.utc):
                rest_patch("exp_imports", _filters(import_id, user["id"]), {
                    "status": "expired", "staged_payload": None,
                })
                raise ApiError("The preview expired; upload the statement again", 410)
            payload = batch.get("staged_payload") or {}
            if not payload:
                raise ApiError("The preview expired; upload the statement again", 410)

            filters = _filters(import_id, user["id"])
            rest_patch("exp_imports", filters, {"status": "committing", "error": None})
            try:
                inserted = {}
                inserted["transactions"] = len(rest_insert(
                    "exp_transactions", payload.get("transactions", []), "dedupe_key"))

                chequing = []
                for row in payload.get("chequing", []):
                    row = dict(row)
                    row["descr"] = row.pop("desc", row.get("descr", ""))
                    chequing.append(row)
                inserted["chequing"] = len(rest_insert("exp_chequing", chequing, "dedupe_key"))
                inserted["payments"] = len(rest_insert(
                    "exp_payments", payload.get("payments", []), "dedupe_key"))
                statements = payload.get("statements", [])
                if statements:
                    rest_upsert("exp_statements", statements, "source")
                inserted["statements"] = len(statements)
                summary = dict(batch.get("summary") or {})
                summary["inserted"] = inserted
                rest_patch("exp_imports", filters, {
                    "status": "committed", "summary": summary, "staged_payload": None,
                    "committed_at": utc_now(), "error": None,
                })
                json_response(self, 200, {"ok": True, **summary})
            except Exception as exc:
                rest_patch("exp_imports", filters, {"status": "failed", "error": str(exc)[:500]})
                raise
        except Exception as exc:
            handle_error(self, exc)
