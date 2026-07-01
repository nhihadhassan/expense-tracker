#!/usr/bin/env python3
"""Focused regression tests for hosted statement parsing and deduplication."""

import os
import tempfile
import zlib

import ingest
from api.shared import _tangerine_kind, parse_upload


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


if __name__ == "__main__":
    test_scotia_year_rollover()
    test_csv_detection_and_stable_dedupe()
    print("PASS - hosted import parsing, rollover, and dedupe")
