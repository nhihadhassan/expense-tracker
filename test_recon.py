#!/usr/bin/env python3
"""
test_recon.py — guards the EBCDIC + FX parsing and the smart-feature outputs.
Run: python3 test_recon.py   (stdlib only; no pytest needed)
"""

import ingest


def approx(a, b, tol=0.01):
    return abs(a - b) <= tol


def main():
    txns, stmts = ingest.parse_dir()
    s = ingest.summary(txns)
    fails = []

    # 1) Reconciliation: total spend == sum(statement purchases) + interest
    stmt_purch = sum(x["purchases"] for x in stmts)
    stmt_int = sum(x["interest"] for x in stmts)
    if not approx(s["total"], stmt_purch + stmt_int):
        fails.append(f"total {s['total']} != purchases {stmt_purch} + interest {stmt_int}")
    if not approx(s["total"], 5236.00):
        fails.append(f"expected total 5236.00, got {s['total']}")
    if s["count"] != 84:
        fails.append(f"expected 84 transactions, got {s['count']}")

    # 2) Balance chain: each statement's balance feeds the next as 'previous'
    if [x["balance"] for x in stmts] != [1600.22, 1623.55, 2002.23]:
        fails.append(f"balance chain wrong: {[x['balance'] for x in stmts]}")

    # 3) FX: LATAM Airlines uses posted CAD (248.09 etc.), not USD (178.48)
    latam = [t for t in txns if t["merchant"] == "LATAM Airlines"]
    if round(sum(t["amount"] for t in latam), 2) != 735.34:
        fails.append(f"LATAM CAD total wrong: {sum(t['amount'] for t in latam)}")

    # 4) No card payments leaked in
    if any("PAYMENT - THANK YOU" in t["raw"].upper() for t in txns):
        fails.append("card payment leaked into spending")

    # 5) No uncategorized merchants
    other = sorted({t["merchant"] for t in txns if t["category"] == "Other"})
    if other:
        fails.append(f"uncategorized merchants: {other}")

    # 6) Recurring detection: real subs flagged, food not
    rec = {r["merchant"] for r in ingest.detect_recurring(txns)}
    for m in ["Spotify", "Freedom Mobile"]:
        if m not in rec:
            fails.append(f"recurring missed {m}")
    for m in ["Au Pain Doré", "Shelbys", "Chipotle"]:
        if m in rec:
            fails.append(f"recurring false-positive {m}")

    # 7) Anomalies surface the big ones
    an = {a["merchant"] for a in ingest.detect_anomalies(txns)}
    for m in ["FlightHub", "Ticketmaster"]:
        if m not in an:
            fails.append(f"anomaly missed {m}")

    # 8) Multi-account: Tangerine adapter loads + reconciles, chequing balance present
    alld = ingest.load_all()
    cards = alld["cards"]
    by_acct = {a: round(sum(r["amount"] for r in cards if r["account"] == a), 2)
               for a in alld["accounts"]}
    if by_acct.get("Tangerine Mastercard") != 18389.62:
        fails.append(f"Tangerine CC total wrong: {by_acct.get('Tangerine Mastercard')}")
    if by_acct.get("Scotiabank Visa") != 5236.00:
        fails.append(f"Scotiabank total wrong: {by_acct.get('Scotiabank Visa')}")
    if by_acct.get("Amex") != 11536.11:
        fails.append(f"Amex total wrong: {by_acct.get('Amex')}")
    if by_acct.get("BMO Mastercard") != 3145.24:
        fails.append(f"BMO total wrong: {by_acct.get('BMO Mastercard')}")
    combined = round(sum(by_acct.values()), 2)
    if combined != 38306.97:
        fails.append(f"combined card total wrong: {combined}")
    # income classification: primary income < all non-internal deposits (transfers excluded)
    chq_all = alld["chequing"]
    income = sum(r["amount"] for r in chq_all if r.get("is_income"))
    noninternal = sum(r["amount"] for r in chq_all
                      if r["kind"] == "deposit" and not r["internal"])
    if not (0 < income < noninternal):
        fails.append(f"income classification off: income {income} vs non-internal {noninternal}")
    # auto-detection precision: across ALL accounts, only real subscriptions (no parking/shopping)
    rec_all = {r["merchant"] for r in ingest.detect_recurring(cards)}
    for m in ["Toronto Parking", "SpotHero Parking", "Canadian Tire", "Escape eSIM"]:
        if m in rec_all:
            fails.append(f"recurring false-positive across accounts: {m}")
    if not {"Spotify", "Freedom Mobile"} <= rec_all:
        fails.append(f"recurring missed core subs across accounts: {rec_all}")

    # categorization coverage ≥ 90% by value
    other = sum(r["amount"] for r in cards if r["category"] == "Other")
    if other / combined > 0.10:
        fails.append(f"low categorization coverage: {other/combined*100:.1f}% Other")
    chq = alld["chequing"]
    if not chq or chq[-1]["balance"] != 998.61:
        fails.append(f"chequing balance wrong: {chq[-1]['balance'] if chq else None}")

    # 9) Backend DB sync stores every account + chequing and reconciles to the static load
    import os as _os
    import db
    tmp = _os.path.join(_os.path.dirname(__file__), "_test.db")
    if _os.path.exists(tmp):
        _os.remove(tmp)
    conn = db.connect(tmp)
    db.seed_rules(conn)
    db.sync_all(conn)
    db_txns = db.all_transactions(conn)
    db_total = round(sum(r["amount"] for r in db_txns), 2)
    if db_total != combined:
        fails.append(f"DB total {db_total} != static {combined} (ref collisions?)")
    if len(db_txns) != len(cards):
        fails.append(f"DB stored {len(db_txns)} txns vs static {len(cards)}")
    if len(db.all_chequing(conn)) != len(chq):
        fails.append("DB chequing count mismatch")
    conn.close()
    _os.remove(tmp)

    if fails:
        print("FAILED:")
        for f in fails:
            print("  -", f)
        raise SystemExit(1)
    print(f"PASS — Scotiabank {s['count']} txns ${s['total']:,.2f}; "
          f"all cards ${combined:,.2f} ({100-other/combined*100:.0f}% categorized); "
          f"chequing balance ${chq[-1]['balance']:,.2f}; recurring/anomalies/chain OK")


if __name__ == "__main__":
    main()
