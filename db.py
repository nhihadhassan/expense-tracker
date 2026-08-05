#!/usr/bin/env python3
"""
db.py — local SQLite store for the Expense Tracker backend.

Stdlib only (sqlite3). Holds transactions, statements, categorization rules,
budgets, and savings goals. Seeded from the shared ingest module so the parsing
logic stays in one place.
"""

import os
import sqlite3
import uuid
from datetime import date, datetime, timezone

import ingest

HERE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(HERE, "expense.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS transactions(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  date TEXT NOT NULL, merchant TEXT NOT NULL, raw TEXT, field TEXT,
  amount REAL NOT NULL, category TEXT NOT NULL,
  ref TEXT, source TEXT, account TEXT, account_type TEXT,
  UNIQUE(source, ref)
);
CREATE TABLE IF NOT EXISTS statements(
  source TEXT PRIMARY KEY, date TEXT, label TEXT,
  purchases REAL, payments REAL, interest REAL, balance REAL
);
CREATE TABLE IF NOT EXISTS chequing(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  date TEXT, descr TEXT, amount REAL, kind TEXT, balance REAL,
  internal INTEGER, dep_type TEXT, is_income INTEGER, account TEXT,
  UNIQUE(account, date, descr, amount, balance)
);
CREATE TABLE IF NOT EXISTS payments(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  date TEXT, amount REAL, account TEXT
);
CREATE TABLE IF NOT EXISTS rules(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ord INTEGER, keyword TEXT, display TEXT, category TEXT
);
CREATE TABLE IF NOT EXISTS budgets(category TEXT PRIMARY KEY, monthly REAL);
CREATE TABLE IF NOT EXISTS goals(
  id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, target REAL, saved REAL
);
CREATE TABLE IF NOT EXISTS manual_entries(
  id TEXT PRIMARY KEY,
  entry_type TEXT NOT NULL CHECK(entry_type IN ('expense','income')),
  date TEXT NOT NULL,
  amount REAL NOT NULL CHECK(amount > 0),
  name TEXT NOT NULL,
  category TEXT NOT NULL,
  account TEXT NOT NULL DEFAULT 'Manual',
  note TEXT NOT NULL DEFAULT '',
  currency TEXT NOT NULL DEFAULT 'CAD',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_txn_date ON transactions(date);
CREATE INDEX IF NOT EXISTS idx_txn_cat ON transactions(category);
CREATE INDEX IF NOT EXISTS idx_txn_acct ON transactions(account);
CREATE INDEX IF NOT EXISTS idx_manual_entries_date ON manual_entries(date);
"""

DEFAULT_BUDGETS = {
    "Entertainment": 700, "Travel": 400, "Eating out": 300, "Subscriptions": 120,
    "Food": 150, "Shopping": 100, "Health": 60, "Transport": 40,
    "Giving": 50, "Fees & Interest": 80,
}


def connect(path=DB_PATH):
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    _migrate_categories(conn)
    return conn


def _migrate_categories(conn):
    """Apply the three unambiguous category renames without losing saved budgets."""
    aliases = {
        "Food & Dining": "Eating out",
        "Groceries": "Food",
        "Health & Pharmacy": "Health",
    }
    for old, new in aliases.items():
        conn.execute("UPDATE transactions SET category=? WHERE category=?", (new, old))
        conn.execute("UPDATE rules SET category=? WHERE category=?", (new, old))
        old_budget = conn.execute(
            "SELECT monthly FROM budgets WHERE category=?", (old,)).fetchone()
        if old_budget:
            conn.execute(
                "INSERT INTO budgets(category,monthly) VALUES(?,?) "
                "ON CONFLICT(category) DO NOTHING", (new, old_budget["monthly"]))
            conn.execute("DELETE FROM budgets WHERE category=?", (old,))
    conn.commit()


def seed_rules(conn):
    if conn.execute("SELECT COUNT(*) FROM rules").fetchone()[0] == 0:
        conn.executemany("INSERT INTO rules(ord,keyword,display,category) VALUES (?,?,?,?)",
                         [(i, kw, disp, cat) for i, (kw, disp, cat) in enumerate(ingest.MERCHANTS)])
    if conn.execute("SELECT COUNT(*) FROM budgets").fetchone()[0] == 0:
        conn.executemany("INSERT INTO budgets(category,monthly) VALUES (?,?)",
                         list(DEFAULT_BUDGETS.items()))
    conn.commit()


def rules_from_db(conn):
    rows = conn.execute("SELECT keyword,display,category FROM rules ORDER BY ord,id").fetchall()
    return [(r["keyword"], r["display"], r["category"]) for r in rows]


def rules_list(conn):
    return [dict(r) for r in conn.execute(
        "SELECT id,ord,keyword,display,category FROM rules ORDER BY ord,id")]


def reresolve(conn):
    """Re-apply current rules to every stored transaction (after a rule change)."""
    rules = rules_from_db(conn)
    for r in conn.execute("SELECT id,field FROM transactions").fetchall():
        name, cat = ingest.resolve(r["field"] or "", rules)
        conn.execute("UPDATE transactions SET merchant=?,category=? WHERE id=?",
                     (name, cat, r["id"]))
    conn.commit()


def rules_add(conn, keyword, display, category, top=True):
    keyword = (keyword or "").strip().upper()
    if not keyword:
        raise ValueError("keyword required")
    ord_ = (conn.execute("SELECT MIN(ord) FROM rules").fetchone()[0] or 0) - 1 if top \
        else (conn.execute("SELECT MAX(ord) FROM rules").fetchone()[0] or 0) + 1
    conn.execute("INSERT INTO rules(ord,keyword,display,category) VALUES (?,?,?,?)",
                 (ord_, keyword, display or keyword.title(), category))
    reresolve(conn)


def rules_update(conn, rule_id, keyword, display, category):
    conn.execute("UPDATE rules SET keyword=?,display=?,category=? WHERE id=?",
                 ((keyword or "").strip().upper(), display, category, rule_id))
    reresolve(conn)


def rules_delete(conn, rule_id):
    conn.execute("DELETE FROM rules WHERE id=?", (rule_id,))
    reresolve(conn)


def recategorize(conn, merchant, category):
    """Recategorize a merchant: update every rule that produces it, else add a new one."""
    rows = conn.execute("SELECT id FROM rules WHERE display=?", (merchant,)).fetchall()
    if rows:
        conn.executemany("UPDATE rules SET category=? WHERE id=?",
                         [(category, r["id"]) for r in rows])
        reresolve(conn)
        return
    f = conn.execute("SELECT field FROM transactions WHERE merchant=? AND field<>'' LIMIT 1",
                     (merchant,)).fetchone()
    keyword = (f["field"] if f else merchant).upper()
    rules_add(conn, keyword, merchant, category, top=True)


def _insert_cards(conn, txns):
    n = 0
    for r in txns:
        cur = conn.execute(
            "INSERT OR IGNORE INTO transactions"
            "(date,merchant,raw,field,amount,category,ref,source,account,account_type)"
            " VALUES (?,?,?,?,?,?,?,?,?,?)",
            (r["date"], r["merchant"], r["raw"], r.get("field", ""), r["amount"],
             r["category"], r["ref"], r["source"],
             r.get("account", r["source"]), r.get("account_type", "card")))
        n += cur.rowcount
    return n


def _insert_statements(conn, stmts):
    for s in stmts:
        conn.execute(
            "INSERT OR REPLACE INTO statements(source,date,label,purchases,payments,interest,balance)"
            " VALUES (?,?,?,?,?,?,?)",
            (s["source"], s["date"], s["label"], s["purchases"], s["payments"],
             s["interest"], s["balance"]))


def ingest_path(conn, path):
    """Parse one PDF (or all PDFs in a dir) and upsert. Returns count inserted."""
    rules = rules_from_db(conn)
    if os.path.isdir(path):
        txns, stmts = ingest.parse_dir(path, rules)
    else:
        txns, stmt = ingest.parse_pdf(path, rules)
        stmts = [stmt] if stmt else []
    for r in txns:
        r.setdefault("account", "Scotiabank Visa")
    n = _insert_cards(conn, txns)
    _insert_statements(conn, stmts)
    conn.commit()
    return n


def sync_all(conn):
    """Load every account (Scotiabank PDF + Tangerine + Amex + BMO + chequing) into the DB.
    Idempotent — INSERT OR IGNORE dedupes, so it's safe to run on every startup."""
    rules = rules_from_db(conn)
    data = ingest.load_all(rules=rules)
    n = _insert_cards(conn, data["cards"])
    _insert_statements(conn, data["statements"])
    conn.execute("DELETE FROM chequing")           # chequing is file-derived; refresh wholesale
    for r in data["chequing"]:
        conn.execute(
            "INSERT OR IGNORE INTO chequing"
            "(date,descr,amount,kind,balance,internal,dep_type,is_income,account)"
            " VALUES (?,?,?,?,?,?,?,?,?)",
            (r["date"], r["desc"], r["amount"], r["kind"], r["balance"],
             int(r["internal"]), r.get("dep_type"), int(r.get("is_income", False)),
             r["account"]))
    conn.execute("DELETE FROM payments")           # payments are file-derived too
    for p in data.get("payments", []):
        conn.execute("INSERT INTO payments(date,amount,account) VALUES (?,?,?)",
                     (p["date"], p["amount"], p["account"]))
    conn.commit()
    return n, data["accounts"]


def all_transactions(conn):
    return [dict(r) for r in conn.execute(
        "SELECT date,merchant,raw,amount,category,ref,source,account,account_type "
        "FROM transactions ORDER BY date,merchant")]


def all_statements(conn):
    return [dict(r) for r in conn.execute(
        "SELECT date,label,purchases,payments,interest,balance FROM statements ORDER BY date")]


def all_payments(conn):
    return [dict(r) for r in conn.execute(
        "SELECT date,amount,account FROM payments ORDER BY date")]


def all_chequing(conn):
    out = []
    for r in conn.execute(
            "SELECT date,descr,amount,kind,balance,internal,dep_type,is_income,account "
            "FROM chequing ORDER BY date"):
        d = dict(r)
        d["desc"] = d.pop("descr")
        d["internal"] = bool(d["internal"])
        d["is_income"] = bool(d["is_income"])
        out.append(d)
    return out


def get_budgets(conn):
    return {r["category"]: r["monthly"] for r in conn.execute("SELECT category,monthly FROM budgets")}


def set_budget(conn, category, monthly):
    conn.execute("INSERT INTO budgets(category,monthly) VALUES(?,?) "
                 "ON CONFLICT(category) DO UPDATE SET monthly=excluded.monthly", (category, monthly))
    conn.commit()


def _manual_values(data, existing=None):
    current = dict(existing or {})
    merged = {**current, **(data or {})}
    entry_type = str(merged.get("entry_type") or "").strip().lower()
    if entry_type not in ("expense", "income"):
        raise ValueError("entry_type must be expense or income")
    iso_date = str(merged.get("date") or "").strip()
    date.fromisoformat(iso_date)
    amount = round(float(merged.get("amount") or 0), 2)
    if amount <= 0:
        raise ValueError("amount must be greater than zero")
    name = str(merged.get("name") or "").strip()
    category = str(merged.get("category") or "").strip()
    if not name:
        raise ValueError("name is required")
    if not category:
        raise ValueError("category is required")
    now = datetime.now(timezone.utc).isoformat()
    return {
        "id": str(merged.get("id") or uuid.uuid4()),
        "entry_type": entry_type,
        "date": iso_date,
        "amount": amount,
        "name": name[:160],
        "category": category[:80],
        "account": str(merged.get("account") or "Manual").strip()[:120] or "Manual",
        "note": str(merged.get("note") or "").strip()[:500],
        "currency": str(merged.get("currency") or "CAD").strip().upper()[:3] or "CAD",
        "created_at": current.get("created_at") or now,
        "updated_at": now,
    }


def all_manual_entries(conn):
    return [dict(row) for row in conn.execute(
        "SELECT id,entry_type,date,amount,name,category,account,note,currency,created_at,updated_at "
        "FROM manual_entries ORDER BY date DESC,created_at DESC")]


def get_manual_entry(conn, entry_id):
    row = conn.execute(
        "SELECT id,entry_type,date,amount,name,category,account,note,currency,created_at,updated_at "
        "FROM manual_entries WHERE id=?", (entry_id,)).fetchone()
    return dict(row) if row else None


def create_manual_entry(conn, data):
    entry = _manual_values(data)
    conn.execute(
        "INSERT INTO manual_entries"
        "(id,entry_type,date,amount,name,category,account,note,currency,created_at,updated_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        tuple(entry[key] for key in (
            "id", "entry_type", "date", "amount", "name", "category", "account", "note",
            "currency", "created_at", "updated_at")))
    conn.commit()
    return entry


def update_manual_entry(conn, entry_id, data):
    existing = get_manual_entry(conn, entry_id)
    if not existing:
        raise KeyError("manual entry not found")
    entry = _manual_values({**(data or {}), "id": entry_id}, existing)
    conn.execute(
        "UPDATE manual_entries SET entry_type=?,date=?,amount=?,name=?,category=?,account=?,note=?,"
        "currency=?,updated_at=? WHERE id=?",
        (entry["entry_type"], entry["date"], entry["amount"], entry["name"], entry["category"],
         entry["account"], entry["note"], entry["currency"], entry["updated_at"], entry_id))
    conn.commit()
    return get_manual_entry(conn, entry_id)


def delete_manual_entry(conn, entry_id):
    cur = conn.execute("DELETE FROM manual_entries WHERE id=?", (entry_id,))
    conn.commit()
    return bool(cur.rowcount)


def bootstrap(path=DB_PATH):
    """Create the DB, seed rules/budgets, and load every account."""
    conn = connect(path)
    seed_rules(conn)
    n, accounts = sync_all(conn)
    total = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
    chq = conn.execute("SELECT COUNT(*) FROM chequing").fetchone()[0]
    print(f"Synced {n} new card txns ({total} total across {len(accounts)} accounts: "
          f"{', '.join(accounts)}); {chq} chequing rows into {path}")
    return conn


if __name__ == "__main__":
    bootstrap()
