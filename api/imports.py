import urllib.parse
from http.server import BaseHTTPRequestHandler

from api.shared import handle_error, json_response, rest_select, verify_owner


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            user = verify_owner(self.headers.get("Authorization"))
            query = urllib.parse.urlencode({
                "select": "id,file_name,institution,account,status,summary,error,created_at,committed_at",
                "user_id": f"eq.{user['id']}",
                "order": "created_at.desc",
                "limit": "20",
            })
            rows = rest_select("exp_imports", query)
            json_response(self, 200, {"imports": rows})
        except Exception as exc:
            handle_error(self, exc)
