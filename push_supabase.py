#!/usr/bin/env python3
"""
push_supabase.py — load all parsed data into the hosted Supabase tables (exp_*).

Parsing stays local (where the EBCDIC/CSV logic works); this just POSTs the
results to PostgREST. Run AFTER temporarily relaxing RLS, then re-lock.
Re-run anytime you add statements — it upserts/refreshes wholesale.

Usage:  python3 push_supabase.py
"""

import json
import os
import urllib.request

import db
import ingest

SUPABASE_URL = "https://zgafubhzhxikuknihmnu.supabase.co"
ANON_KEY = "sb_publishable_HMICK42AzL2W_Tpb6VutDQ_HawfnbWM"
HEADERS = {
    "apikey": ANON_KEY,
    "Authorization": f"Bearer {ANON_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal",
}


def _req(method, path, body=None):
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(url, data=data, headers=HEADERS, method=method)
    with urllib.request.urlopen(r) as resp:
        return resp.status


def wipe(table):
    # delete all rows (id >= 0 matches everything; PostgREST requires a filter)
    _req("DELETE", f"{table}?id=gte.0") if table not in ("exp_statements", "exp_budgets") \
        else _req("DELETE", f"{table}?{'source' if table=='exp_statements' else 'category'}=neq.__none__")


def insert(table, rows, chunk=500):
    for i in range(0, len(rows), chunk):
        _req("POST", table, rows[i:i + chunk])


def main():
    data = ingest.load_all()
    rules = ingest.MERCHANTS

    txns = [{
        "date": r["date"], "merchant": r["merchant"], "raw": r["raw"],
        "field": r.get("field", ""), "amount": r["amount"], "category": r["category"],
        "ref": r["ref"], "source": r["source"],
        "account": r.get("account"), "account_type": r.get("account_type", "card"),
    } for r in data["cards"]]

    chq = [{
        "date": r["date"], "descr": r["desc"], "amount": r["amount"], "kind": r["kind"],
        "balance": r["balance"], "internal": r["internal"], "dep_type": r.get("dep_type"),
        "is_income": r.get("is_income", False), "account": r["account"],
    } for r in data["chequing"]]

    pays = [{"date": p["date"], "amount": p["amount"], "account": p["account"]}
            for p in data["payments"]]

    stmts = [{"source": s["source"], "date": s["date"], "label": s["label"],
              "purchases": s["purchases"], "payments": s["payments"],
              "interest": s["interest"], "balance": s["balance"]}
             for s in data["statements"]]

    rule_rows = [{"ord": i, "keyword": kw, "display": disp, "category": cat}
                 for i, (kw, disp, cat) in enumerate(rules)]
    budget_rows = [{"category": k, "monthly": v} for k, v in db.DEFAULT_BUDGETS.items()]

    for table in ("exp_transactions", "exp_chequing", "exp_payments", "exp_statements",
                  "exp_rules", "exp_budgets"):
        wipe(table)
    insert("exp_transactions", txns)
    insert("exp_chequing", chq)
    insert("exp_payments", pays)
    insert("exp_statements", stmts)
    insert("exp_rules", rule_rows)
    insert("exp_budgets", budget_rows)

    print(f"Pushed: {len(txns)} txns, {len(chq)} chequing, {len(pays)} payments, "
          f"{len(stmts)} statements, {len(rule_rows)} rules, {len(budget_rows)} budgets")


if __name__ == "__main__":
    main()
