#!/usr/bin/env python3
"""
server.py — zero-dependency local backend for the Expense Tracker.

Uses only the Python stdlib (http.server + sqlite3), so it runs with just
`python3 server.py` — no pip install. It is structured so the JSON API can be
swapped to FastAPI later without touching the analytics (which live in ingest.py).

Endpoints (JSON unless noted):
  GET  /api/transactions          all transactions
  GET  /api/statements            per-statement summaries
  GET  /api/summary               totals + by-category
  GET  /api/recurring             detected subscriptions/recurring charges
  GET  /api/anomalies             unusual purchases
  GET  /api/forecast              projected spend
  GET  /api/insights              everything above bundled for the dashboard
  GET  /api/budgets               category budgets
  POST /api/budgets   {category,monthly}      update a budget
  POST /api/ingest    (multipart PDF upload)  parse + store a new statement
  GET  /  and static files                    serves the dashboard

Run:  python3 server.py   then open http://localhost:8765/
"""

import cgi
import json
import os
import tempfile
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import unquote

import db
import ingest

HERE = os.path.dirname(os.path.abspath(__file__))
PORT = int(os.environ.get("PORT", "8765"))

CONN = db.connect()
db.seed_rules(CONN)
# Sync every account (Scotiabank PDF + Tangerine + Amex + BMO + chequing) — idempotent
_n, _accts = db.sync_all(CONN)
print(f"Loaded {db.all_transactions(CONN).__len__()} txns across {len(_accts)} accounts: "
      f"{', '.join(_accts)}")


def compute_insights():
    txns = db.all_transactions(CONN)
    return {
        "summary": ingest.summary(txns),
        "statements": db.all_statements(CONN),
        "recurring": ingest.detect_recurring(txns),
        "anomalies": ingest.detect_anomalies(txns),
        "forecast": ingest.forecast(txns),
        "budgets": db.get_budgets(CONN),
        "accounts": _accts,
    }


class Handler(BaseHTTPRequestHandler):
    def _json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass  # quiet

    def do_GET(self):
        p = unquote(self.path.split("?")[0])
        try:
            if p == "/api/transactions":
                return self._json(db.all_transactions(CONN))
            if p == "/api/statements":
                return self._json(db.all_statements(CONN))
            if p == "/api/chequing":
                return self._json(db.all_chequing(CONN))
            if p == "/api/payments":
                return self._json(db.all_payments(CONN))
            if p == "/api/summary":
                return self._json(ingest.summary(db.all_transactions(CONN)))
            if p == "/api/recurring":
                return self._json(ingest.detect_recurring(db.all_transactions(CONN)))
            if p == "/api/anomalies":
                return self._json(ingest.detect_anomalies(db.all_transactions(CONN)))
            if p == "/api/forecast":
                return self._json(ingest.forecast(db.all_transactions(CONN)))
            if p == "/api/insights":
                return self._json(compute_insights())
            if p == "/api/budgets":
                return self._json(db.get_budgets(CONN))
            if p == "/api/rules":
                return self._json(db.rules_list(CONN))
        except Exception as e:  # surface errors as JSON
            return self._json({"error": str(e)}, 500)
        return self._static(p)

    def do_POST(self):
        try:
            if self.path == "/api/budgets":
                n = int(self.headers.get("Content-Length", 0))
                data = json.loads(self.rfile.read(n) or b"{}")
                db.set_budget(CONN, data["category"], float(data["monthly"]))
                return self._json({"ok": True, "budgets": db.get_budgets(CONN)})
            if self.path == "/api/ingest":
                return self._ingest_upload()
            if self.path == "/api/rules":
                n = int(self.headers.get("Content-Length", 0))
                d = json.loads(self.rfile.read(n) or b"{}")
                action = d.get("action")
                if action == "add":
                    db.rules_add(CONN, d["keyword"], d.get("display", ""), d["category"])
                elif action == "update":
                    db.rules_update(CONN, d["id"], d["keyword"], d.get("display", ""), d["category"])
                elif action == "delete":
                    db.rules_delete(CONN, d["id"])
                else:
                    return self._json({"error": "unknown action"}, 400)
                return self._json({"ok": True, "rules": db.rules_list(CONN),
                                   "summary": ingest.summary(db.all_transactions(CONN))})
            if self.path == "/api/recategorize":
                n = int(self.headers.get("Content-Length", 0))
                d = json.loads(self.rfile.read(n) or b"{}")
                db.recategorize(CONN, d["merchant"], d["category"])
                return self._json({"ok": True, "rules": db.rules_list(CONN)})
        except Exception as e:
            return self._json({"error": str(e)}, 500)
        self._json({"error": "not found"}, 404)

    def _ingest_upload(self):
        ctype, _ = cgi.parse_header(self.headers.get("Content-Type", ""))
        if ctype != "multipart/form-data":
            return self._json({"error": "expected multipart/form-data with a 'file' field"}, 400)
        form = cgi.FieldStorage(fp=self.rfile, headers=self.headers,
                                environ={"REQUEST_METHOD": "POST",
                                         "CONTENT_TYPE": self.headers["Content-Type"]})
        item = form["file"] if "file" in form else None
        if item is None or not item.file:
            return self._json({"error": "no file uploaded"}, 400)
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(item.file.read())
            tmp_path = tmp.name
        try:
            # preserve original filename as source so dedupe works across re-uploads
            src = os.path.basename(item.filename or os.path.basename(tmp_path))
            rules = db.rules_from_db(CONN)
            txns, stmt = ingest.parse_pdf(tmp_path, rules)
            for r in txns:
                r["source"] = src                       # uploaded PDFs are Scotiabank-format
                r["account"] = "Scotiabank Visa"
            inserted = db._insert_cards(CONN, txns)
            if stmt:
                stmt["source"] = src
                CONN.execute(
                    "INSERT OR REPLACE INTO statements(source,date,label,purchases,payments,interest,balance)"
                    " VALUES (?,?,?,?,?,?,?)",
                    (src, stmt["date"], stmt["label"], stmt["purchases"], stmt["payments"],
                     stmt["interest"], stmt["balance"]))
            CONN.commit()
            return self._json({"ok": True, "file": src, "parsed": len(txns),
                               "inserted": inserted, "total": CONN.execute(
                                   "SELECT COUNT(*) FROM transactions").fetchone()[0]})
        finally:
            os.unlink(tmp_path)

    def _static(self, p):
        rel = "expense-dashboard.html" if p in ("/", "") else p.lstrip("/")
        path = os.path.normpath(os.path.join(HERE, rel))
        if not path.startswith(HERE) or not os.path.isfile(path):
            return self._json({"error": "not found"}, 404)
        ctype = ("text/html" if path.endswith(".html") else
                 "application/javascript" if path.endswith(".js") else
                 "text/css" if path.endswith(".css") else "application/octet-stream")
        with open(path, "rb") as f:
            body = f.read()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def _addresses():
    """Best-effort list of (label, host) this server is reachable at."""
    import socket
    import subprocess
    out = [("On this Mac", "localhost")]
    try:                                            # LAN IP (same Wi-Fi)
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        out.append(("On your Wi-Fi (LAN)", s.getsockname()[0]))
        s.close()
    except OSError:
        pass
    try:                                            # Tailscale IP, if installed/up
        ip = subprocess.run(["tailscale", "ip", "-4"], capture_output=True,
                            text=True, timeout=2).stdout.strip().splitlines()
        if ip:
            out.append(("On your phone via Tailscale", ip[0]))
    except (OSError, subprocess.SubprocessError):
        pass
    return out


def main():
    print("Expense Tracker backend — open one of these:")
    for label, host in _addresses():
        print(f"  {label:30} http://{host}:{PORT}/")
    print("  (For phone access, install Tailscale on this Mac + your phone — see TUNNEL_SETUP.md)")
    HTTPServer(("", PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
