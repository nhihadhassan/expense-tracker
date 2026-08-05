#!/usr/bin/env python3
"""Regression tests for local manual expense and income storage."""

import sqlite3
from pathlib import Path

import db


def test_manual_entry_crud():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(db.SCHEMA)
    created = db.create_manual_entry(conn, {
        "entry_type": "expense", "date": "2026-08-05", "amount": 12.345,
        "name": "Lunch", "category": "Eating out", "account": "Cash", "note": "with Rachel",
    })
    assert created["amount"] == 12.35
    assert created["currency"] == "CAD"
    assert db.all_manual_entries(conn)[0]["name"] == "Lunch"

    updated = db.update_manual_entry(conn, created["id"], {
        "entry_type": "income", "amount": 25, "name": "Refund", "category": "Refund",
    })
    assert updated["entry_type"] == "income"
    assert updated["date"] == "2026-08-05"
    assert updated["note"] == "with Rachel"
    assert db.delete_manual_entry(conn, created["id"])
    assert db.all_manual_entries(conn) == []


def test_manual_entry_validation():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(db.SCHEMA)
    for bad in (
        {"entry_type": "transfer", "date": "2026-08-05", "amount": 1, "name": "x", "category": "Other"},
        {"entry_type": "expense", "date": "bad", "amount": 1, "name": "x", "category": "Other"},
        {"entry_type": "expense", "date": "2026-08-05", "amount": 0, "name": "x", "category": "Other"},
    ):
        try:
            db.create_manual_entry(conn, bad)
            raise AssertionError(f"accepted invalid entry: {bad}")
        except (ValueError, TypeError):
            pass


def test_category_and_rls_migration_contract():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(db.SCHEMA)
    conn.execute("insert into transactions(date,merchant,amount,category) values('2026-08-05','Cafe',5,'Food & Dining')")
    conn.execute("insert into budgets(category,monthly) values('Groceries',150)")
    conn.execute("insert into rules(ord,keyword,display,category) values(1,'RX','Pharmacy','Health & Pharmacy')")
    db._migrate_categories(conn)
    assert conn.execute("select category from transactions").fetchone()[0] == "Eating out"
    assert conn.execute("select category from budgets").fetchone()[0] == "Food"
    assert conn.execute("select category from rules").fetchone()[0] == "Health"

    sql = Path("supabase/migrations/20260805013000_mobile_manual_entries.sql").read_text()
    assert "alter table public.exp_manual_entries enable row level security" in sql.lower()
    assert "using (user_id = auth.uid())" in sql
    assert "with check (user_id = auth.uid())" in sql
    assert "amount numeric(12,2)" in sql


if __name__ == "__main__":
    test_manual_entry_crud()
    test_manual_entry_validation()
    test_category_and_rls_migration_contract()
    print("PASS - manual entry CRUD, category migration, and RLS contract")
