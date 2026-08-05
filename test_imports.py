#!/usr/bin/env python3
"""Focused regression tests for hosted statement parsing and deduplication."""

import os
import tempfile
import zlib

import ingest
from api.shared import ApiError, MAX_UPLOAD_BYTES, _tangerine_kind, parse_upload


def _fake_scotia_pdf(text):
    encoded = text.encode("cp037")
    stream = zlib.compress(b"(" + encoded + b")")
    tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    try:
        tmp.write(b"%PDF-1.4\nstream\n" + stream + b"\nendstream\n%%EOF")
        return tmp.name
    finally:
        tmp.close()


def test_scotia_year_rollover():
    path = _fake_scotia_pdf(
        "Statement Date Jan 5, 2026 "
        "123 Dec 30 Dec 31 TEST MERCHANT TORONTO ON 10.00"
    )
    try:
        rows, _statement = ingest.parse_pdf(path)
        assert len(rows) == 1, rows
        assert rows[0]["date"] == "2025-12-30", rows[0]
    finally:
        os.unlink(path)


def test_csv_detection_and_stable_dedupe():
    amex = (
        "Date,Transaction,Charges $,Credits $,Sub-Category\n"
        "01/02/2026,TEST STORE,12.34,0,Retail\n"
    ).encode()
    first = parse_upload(amex, "renamed-export.csv")
    second = parse_upload(amex, "another-name.csv")
    assert first["institution"] == "American Express"
    assert first["account"] == "Amex"
    assert first["transactions"][0]["dedupe_key"] == second["transactions"][0]["dedupe_key"]

    bmo = (
        "Date,Description,Amount,Direction,AbsAmount,Account,CardLast4\n"
        "2026-01-02,TEST CAFE,-9.50,out,9.50,card,1234\n"
        "2026-01-03,PAYMENT,50.00,in,50.00,card,1234\n"
    ).encode()
    parsed = parse_upload(bmo, "bmo.csv")
    assert parsed["institution"] == "BMO"
    assert len(parsed["transactions"]) == 1
    assert len(parsed["payments"]) == 1

    tangerine = (
        "# Tangerine Chequing\n\n"
        "| Date | Description | Amount | Type | Balance |\n"
        "| --- | --- | ---: | --- | ---: |\n"
        "| Feb 3, 2026 | TEST DEBIT | -$25.00 | Withdrawal | $975.00 |\n"
    ).encode()
    chequing = parse_upload(tangerine, "chequing.md")["chequing"][0]
    assert chequing["desc"] == "TEST DEBIT"
    expected = "chequing|Tangerine Chequing|2026-02-03|TEST DEBIT|25.00|975.00|0"
    import hashlib
    assert chequing["dedupe_key"] == hashlib.sha256(expected.encode()).hexdigest()
    assert _tangerine_kind(tangerine.decode()) == "chq"

    credit = (
        "| Date | Description | Card | Amount | Type | Cash-Back |\n"
        "| --- | --- | --- | ---: | --- | ---: |\n"
        "| Feb 3, 2026 | TEST PURCHASE | ***1234 | $25.00 | Purchase | |\n"
    )
    assert _tangerine_kind(credit) == "cc"


def test_scotia_and_generic_csv_mapping():
    scotia = (
        "Date,Amount,Type of Transaction,Description,Sub-description\n"
        "2026-08-01,-18.25,Debit,TEST CAFE,TORONTO\n"
        "2026-08-02,50.00,Credit,PAYMENT,\n"
    ).encode()
    parsed = parse_upload(scotia, "scotia.csv")
    assert parsed["institution"] == "Scotiabank"
    assert len(parsed["transactions"]) == 1
    assert len(parsed["payments"]) == 1

    generic = (
        "Posted,Details,Value,Balance\n"
        "05/08/2026,Corner store,-12.50,987.50\n"
        "06/08/2026,Payroll,1500.00,2487.50\n"
    ).encode()
    try:
        parse_upload(generic, "new-bank.csv")
        raise AssertionError("unknown CSV did not request mapping")
    except ApiError as exc:
        assert exc.status == 422
        assert exc.details["mappingRequired"] is True
        assert exc.details["headers"] == ["Posted", "Details", "Value", "Balance"]

    mapped = parse_upload(generic, "new-bank.csv", mapping={
        "date": "Posted", "description": "Details", "amount": "Value", "balance": "Balance",
        "dateFormat": "dmy", "expenseSign": "negative", "accountType": "bank",
        "account": "Daily Chequing", "institution": "Example Bank",
    })
    assert mapped["institution"] == "Example Bank"
    assert mapped["transactions"][0]["amount"] == 12.5
    assert mapped["chequing"][0]["amount"] == 1500
    assert mapped["date_from"] == "2026-08-05"


def test_upload_limits_and_validation():
    try:
        parse_upload(b"x" * (MAX_UPLOAD_BYTES + 1), "large.csv")
        raise AssertionError("oversized upload accepted")
    except ApiError as exc:
        assert exc.status == 413
    boundary = b"Date,Description,Amount\n2026-08-05,Boundary,1.00\n"
    boundary += b"\n" * (MAX_UPLOAD_BYTES - len(boundary))
    accepted = parse_upload(boundary, "boundary.csv", mapping={
        "date": "Date", "description": "Description", "amount": "Amount",
        "accountType": "card", "expenseSign": "positive",
    })
    assert accepted["transactions"][0]["amount"] == 1.0

    split_columns = (
        "When,Memo,Money out,Money in\n"
        "08/03/2026,Pharmacy,22.75,\n"
        "08/04/2026,Refund,,7.50\n"
    ).encode()
    split = parse_upload(split_columns, "split.csv", mapping={
        "date": "When", "description": "Memo", "debit": "Money out", "credit": "Money in",
        "dateFormat": "mdy", "accountType": "bank", "account": "Cash account",
    })
    assert len(split["transactions"]) == 1 and len(split["chequing"]) == 1
    assert split["transactions"][0]["date"] == "2026-08-03"

    overlapping = (
        "Date,Description,Amount\n"
        "2026-08-05,Same purchase,9.99\n"
        "2026-08-05,Same purchase,9.99\n"
    ).encode()
    overlap = parse_upload(overlapping, "overlap.csv", mapping={
        "date": "Date", "description": "Description", "amount": "Amount",
        "accountType": "card", "expenseSign": "positive",
    })
    assert len(overlap["transactions"]) == 2
    assert len({row["dedupe_key"] for row in overlap["transactions"]}) == 2

    for data, name in ((b"", "empty.csv"), (b"hello", "statement.txt")):
        try:
            parse_upload(data, name)
            raise AssertionError(f"invalid upload accepted: {name}")
        except ApiError:
            pass
    try:
        parse_upload(b"%PDF-1.4\n/image-only\n%%EOF", "scan.pdf")
        raise AssertionError("image-only PDF accepted")
    except ApiError as exc:
        assert "read" in str(exc).lower() or "transaction" in str(exc).lower()


if __name__ == "__main__":
    test_scotia_year_rollover()
    test_csv_detection_and_stable_dedupe()
    test_scotia_and_generic_csv_mapping()
    test_upload_limits_and_validation()
    print("PASS - hosted import parsing, rollover, and dedupe")
