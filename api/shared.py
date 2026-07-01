"""Shared auth, parsing, dedupe, and Supabase REST helpers for Vercel Functions."""

import csv
import hashlib
import json
import os
import re
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

import ingest

MAX_UPLOAD_BYTES = 4 * 1024 * 1024
OWNER_EMAIL = os.environ.get("OWNER_EMAIL", "nhihad.hassan@gmail.com").lower()
SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
PUBLISHABLE_KEY = os.environ.get("SUPABASE_PUBLISHABLE_KEY", "")
SECRET_KEY = os.environ.get("SUPABASE_SECRET_KEY", "")


class ApiError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


def require_config(secret=False):
    missing = [name for name, value in (
        ("SUPABASE_URL", SUPABASE_URL),
        ("SUPABASE_PUBLISHABLE_KEY", PUBLISHABLE_KEY),
        ("SUPABASE_SECRET_KEY", SECRET_KEY if secret else "ok"),
    ) if not value]
    if missing:
        raise ApiError("Hosted imports are not configured: " + ", ".join(missing), 503)


def _request(method, url, headers=None, body=None):
    data = None if body is None else json.dumps(body, separators=(",", ":")).encode()
    req = urllib.request.Request(url, data=data, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            raw = response.read()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", "replace")
        try:
            detail = json.loads(raw).get("message") or json.loads(raw).get("msg") or raw
        except json.JSONDecodeError:
            detail = raw
        raise ApiError(str(detail or f"Upstream request failed ({exc.code})"), exc.code)


def verify_owner(authorization):
    require_config()
    if not authorization or not authorization.startswith("Bearer "):
        raise ApiError("Authentication required", 401)
    token = authorization[7:].strip()
    user = _request("GET", f"{SUPABASE_URL}/auth/v1/user", {
        "apikey": PUBLISHABLE_KEY,
        "Authorization": f"Bearer {token}",
    })
    if not user or (user.get("email") or "").lower() != OWNER_EMAIL:
        raise ApiError("This account is not authorized", 403)
    return user


def _admin_headers(prefer=None):
    require_config(secret=True)
    headers = {"apikey": SECRET_KEY, "Content-Type": "application/json"}
    # Legacy service-role JWTs require Authorization. New sb_secret keys are
    # authenticated by the API gateway through the apikey header.
    if SECRET_KEY.count(".") == 2:
        headers["Authorization"] = f"Bearer {SECRET_KEY}"
    if prefer:
        headers["Prefer"] = prefer
    return headers


def rest_select(table, query=""):
    suffix = ("?" + query) if query else ""
    return _request("GET", f"{SUPABASE_URL}/rest/v1/{table}{suffix}", _admin_headers()) or []


def rest_insert(table, rows, on_conflict=None):
    if not rows:
        return []
    query = ""
    prefer = "return=representation"
    if on_conflict:
        query = "?on_conflict=" + urllib.parse.quote(on_conflict)
        prefer = "resolution=ignore-duplicates,return=representation"
    return _request("POST", f"{SUPABASE_URL}/rest/v1/{table}{query}",
                    _admin_headers(prefer), rows) or []


def rest_upsert(table, rows, on_conflict):
    if not rows:
        return []
    query = "?on_conflict=" + urllib.parse.quote(on_conflict)
    return _request("POST", f"{SUPABASE_URL}/rest/v1/{table}{query}",
                    _admin_headers("resolution=merge-duplicates,return=representation"), rows) or []


def rest_patch(table, filters, values):
    return _request("PATCH", f"{SUPABASE_URL}/rest/v1/{table}?{filters}",
                    _admin_headers("return=representation"), values) or []


def clean_filename(name):
    return re.sub(r"[^A-Za-z0-9._ -]+", "_", os.path.basename(name or "statement"))[:160]


def _canonical_amount(value):
    return f"{float(value or 0):.2f}"


def add_dedupe_keys(rows, kind):
    seen = {}
    for row in rows:
        if kind == "transaction":
            parts = [kind, row.get("account", ""), row.get("date", ""),
                     row.get("raw") or row.get("merchant", ""), _canonical_amount(row.get("amount"))]
        elif kind == "payment":
            parts = [kind, row.get("account", ""), row.get("date", ""), "",
                     _canonical_amount(row.get("amount"))]
        else:
            parts = [kind, row.get("account", ""), row.get("date", ""), row.get("descr") or row.get("desc", ""),
                     _canonical_amount(row.get("amount")), _canonical_amount(row.get("balance")) if row.get("balance") is not None else ""]
        base = "|".join(parts)
        occurrence = seen.get(base, 0)
        seen[base] = occurrence + 1
        row["dedupe_key"] = hashlib.sha256(f"{base}|{occurrence}".encode()).hexdigest()


def _write_temp(data, suffix):
    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    try:
        tmp.write(data)
        return tmp.name
    finally:
        tmp.close()


def _tangerine_from_text(text, filename, kind):
    from Tangerine import normalize_tangerine

    records = normalize_tangerine.parse(text.splitlines(), kind)
    if not records:
        raise ApiError("No Tangerine transactions were found in this statement")
    rendered = normalize_tangerine.render_cc(records) if kind == "cc" else normalize_tangerine.render_chq(records)
    path = _write_temp(rendered.encode(), ".md")
    try:
        if kind == "cc":
            tx = ingest.parse_tangerine_cc(path)
            pay = ingest._tangerine_cc_payments(path)
            return "Tangerine", "Tangerine Mastercard", tx, [], pay, []
        chq = ingest.parse_tangerine_chq(path)
        return "Tangerine", "Tangerine Chequing", [], chq, [], []
    finally:
        os.unlink(path)


def _tangerine_kind(text):
    from Tangerine import normalize_tangerine

    records = normalize_tangerine.parse(text.splitlines(), "cc")
    if not records:
        raise ApiError("No supported Tangerine transactions were found")
    balances = sum(row.get("balance") is not None for row in records)
    cards = sum(bool(row.get("card")) for row in records)
    if balances > cards and balances >= max(1, len(records) // 4):
        return "chq"
    if cards:
        return "cc"
    low = text.lower()
    if "| balance |" in low or "chequing" in low:
        return "chq"
    if "| cash-back |" in low or "payment/credit" in low:
        return "cc"
    raise ApiError("Could not determine whether this is Tangerine chequing or credit-card data")


def _parse_pdf(path, filename):
    scotia_text = ingest.extract_text(path)
    if "Statement Date" in scotia_text and ingest.ROW_RE.search(scotia_text):
        tx, statement = ingest.parse_pdf(path)
        for row in tx:
            row["source"] = filename
            row["account"] = "Scotiabank Visa"
            row["account_type"] = "card"
        payments = ingest.parse_scotia_payments_file(path)
        if statement:
            statement["source"] = filename
        return "Scotiabank", "Scotiabank Visa", tx, [], payments, [statement] if statement else []

    try:
        from markitdown import MarkItDown
        converted = MarkItDown().convert(path).text_content
    except Exception as exc:
        raise ApiError("This PDF could not be read. For BMO, export CSV instead.") from exc
    kind = _tangerine_kind(converted)
    return _tangerine_from_text(converted, filename, kind)


def _parse_csv(path):
    with open(path, newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        headers = {h.strip() for h in (reader.fieldnames or []) if h}
    if {"Date", "Transaction", "Charges $"}.issubset(headers):
        return "American Express", "Amex", ingest.parse_amex_csv(path), [], ingest._amex_payments(path), []
    if {"Date", "Description", "Direction"}.issubset(headers):
        return "BMO", "BMO Mastercard", ingest.parse_bmo_csv(path), [], ingest._bmo_payments(path), []
    raise ApiError("Unsupported CSV columns. Upload an Amex or BMO bank export.")


def parse_upload(data, filename):
    filename = clean_filename(filename)
    if not data:
        raise ApiError("The uploaded file is empty")
    if len(data) > MAX_UPLOAD_BYTES:
        raise ApiError("Statement files must be 4 MB or smaller", 413)
    ext = os.path.splitext(filename)[1].lower()
    if ext not in (".pdf", ".csv", ".md"):
        raise ApiError("Upload a PDF, CSV, or normalized Tangerine Markdown file")
    path = _write_temp(data, ext)
    try:
        if ext == ".pdf":
            parsed = _parse_pdf(path, filename)
        elif ext == ".csv":
            parsed = _parse_csv(path)
        else:
            text = data.decode("utf-8-sig", "replace")
            low = text.lower()
            has_card_marker = bool(re.search(r"\*{2,}\d{4}", text))
            has_tangerine_table = "| date | description |" in low and ("| balance |" in low or "| cash-back |" in low)
            if not has_card_marker and not has_tangerine_table:
                raise ApiError("Only normalized Tangerine Markdown is supported")
            kind = _tangerine_kind(text)
            parsed = _tangerine_from_text(text, filename, kind)
    finally:
        os.unlink(path)

    institution, account, tx, chq, payments, statements = parsed
    for row in tx:
        row.setdefault("account", account)
        row.setdefault("account_type", "card")
    add_dedupe_keys(tx, "transaction")
    add_dedupe_keys(chq, "chequing")
    add_dedupe_keys(payments, "payment")
    dates = [r["date"] for group in (tx, chq, payments) for r in group if r.get("date")]
    if not dates:
        raise ApiError("No supported transactions were found")
    warnings = []
    uncategorized = sum(1 for row in tx if row.get("category") == "Other")
    if uncategorized:
        warnings.append(f"{uncategorized} transaction(s) need categorization")
    return {
        "institution": institution,
        "account": account,
        "file_name": filename,
        "file_hash": hashlib.sha256(data).hexdigest(),
        "transactions": tx,
        "chequing": chq,
        "payments": payments,
        "statements": statements,
        "date_from": min(dates),
        "date_to": max(dates),
        "warnings": warnings,
        "uncategorized": uncategorized,
    }


def existing_keys(table, keys):
    found = set()
    for start in range(0, len(keys), 80):
        chunk = keys[start:start + 80]
        values = ",".join(chunk)
        query = "select=dedupe_key&dedupe_key=in.(" + urllib.parse.quote(values, safe=",()") + ")"
        found.update(row["dedupe_key"] for row in rest_select(table, query))
    return found


def import_summary(parsed):
    mapping = (("transactions", "exp_transactions"), ("chequing", "exp_chequing"),
               ("payments", "exp_payments"))
    duplicate_counts = {}
    new_counts = {}
    for key, table in mapping:
        rows = parsed[key]
        existing = existing_keys(table, [row["dedupe_key"] for row in rows])
        duplicate_counts[key] = sum(1 for row in rows if row["dedupe_key"] in existing)
        new_counts[key] = len(rows) - duplicate_counts[key]
    total = sum(float(row.get("amount") or 0) for row in parsed["transactions"])
    return {
        "institution": parsed["institution"], "account": parsed["account"],
        "dateFrom": parsed["date_from"], "dateTo": parsed["date_to"],
        "parsed": {key: len(parsed[key]) for key in ("transactions", "chequing", "payments", "statements")},
        "new": new_counts, "duplicates": duplicate_counts,
        "purchaseTotal": round(total, 2), "uncategorized": parsed["uncategorized"],
        "warnings": parsed["warnings"],
        "sample": [{k: row.get(k) for k in ("date", "merchant", "amount", "category")}
                   for row in parsed["transactions"][:8]],
    }


def json_response(handler, status, payload):
    body = json.dumps(payload, separators=(",", ":")).encode()
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def handle_error(handler, exc):
    if isinstance(exc, ApiError):
        json_response(handler, exc.status, {"error": str(exc)})
    else:
        json_response(handler, 500, {"error": "Unexpected import error"})


def utc_now():
    return datetime.now(timezone.utc).isoformat()
