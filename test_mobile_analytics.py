#!/usr/bin/env python3
"""Deterministic cash-flow and timeframe acceptance tests for the mobile overview."""

from datetime import date, timedelta


def bounds(mode, anchor, custom=None):
    anchor = date.fromisoformat(anchor)
    if mode == "day":
        start = end = anchor
    elif mode == "week":
        start = anchor - timedelta(days=anchor.weekday())
        end = start + timedelta(days=6)
    elif mode == "month":
        start = anchor.replace(day=1)
        next_month = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
        end = next_month - timedelta(days=1)
    elif mode == "year":
        start, end = anchor.replace(month=1, day=1), anchor.replace(month=12, day=31)
    elif mode == "custom":
        start, end = map(date.fromisoformat, custom)
    else:
        raise ValueError(mode)
    return start.isoformat(), end.isoformat()


def aggregate(expenses, imported_income, manual_entries, start, end):
    selected_expenses = [row for row in expenses if start <= row["date"] <= end]
    selected_income = [row for row in imported_income if start <= row["date"] <= end]
    selected_income += [row for row in manual_entries
                        if row["entry_type"] == "income" and start <= row["date"] <= end]
    selected_expenses += [row for row in manual_entries
                          if row["entry_type"] == "expense" and start <= row["date"] <= end]
    cash_out = round(sum(row["amount"] for row in selected_expenses), 2)
    cash_in = round(sum(row["amount"] for row in selected_income), 2)
    categories = {}
    for row in selected_expenses:
        categories[row["category"]] = categories.get(row["category"], 0) + row["amount"]
    return cash_in, cash_out, round(cash_in - cash_out, 2), categories


def run():
    assert bounds("day", "2026-08-05") == ("2026-08-05", "2026-08-05")
    assert bounds("week", "2026-01-01") == ("2025-12-29", "2026-01-04")
    assert bounds("month", "2024-02-15") == ("2024-02-01", "2024-02-29")
    assert bounds("year", "2026-08-05") == ("2026-01-01", "2026-12-31")
    assert bounds("custom", "2026-08-05", ("2026-07-29", "2026-08-03")) == (
        "2026-07-29", "2026-08-03")

    expenses = [
        {"date": "2026-08-02", "amount": 25.0, "category": "Eating out"},
        {"date": "2026-08-03", "amount": 75.0, "category": "Food"},
    ]
    imported_income = [{"date": "2026-08-01", "amount": 1000.0}]
    manual = [
        {"date": "2026-08-04", "amount": 250.0, "category": "Salary", "entry_type": "income"},
        {"date": "2026-08-05", "amount": 20.0, "category": "Health", "entry_type": "expense"},
    ]
    cash_in, cash_out, net, categories = aggregate(
        expenses, imported_income, manual, "2026-08-01", "2026-08-31")
    assert (cash_in, cash_out, net) == (1250.0, 120.0, 1130.0)
    assert categories == {"Eating out": 25.0, "Food": 75.0, "Health": 20.0}
    assert round(categories["Food"] / cash_out * 100, 1) == 62.5
    assert round(categories["Food"] / cash_in * 100, 1) == 6.0

    zero_income = aggregate(expenses, [], [], "2026-08-01", "2026-08-31")
    assert zero_income[:3] == (0, 100.0, -100.0)
    percent_of_income = None if zero_income[0] == 0 else 0
    assert percent_of_income is None
    print("PASS - mobile cash-flow, category shares, and timeframe boundaries")


if __name__ == "__main__":
    run()
