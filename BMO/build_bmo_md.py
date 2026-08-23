#!/usr/bin/env python3
"""Build a normalized Markdown table from BMO Mastercard transaction exports.

BMO's statement PDFs are image-only (no text layer, and OCR on them is unreliable),
so rows are transcribed into the ROWS list below and normalized by this script.

The data here is a SYNTHETIC SAMPLE, committed so the repository is runnable and
testable without any real statement. Real statements and transcriptions stay local:
everything under BMO/ is git-ignored except this script.
"""

# (date, description, signed amount). '+' prefix = money in (credit/payment).
ROWS = [
    ("Apr 07, 2026", "INTEREST PURCHASES", "1.42"),
    ("Apr 05, 2026", "PAYMENT RECEIVED - THANK YOU", "+62.10"),
    ("Mar 28, 2026", "SAMPLE GROCER #101 ANYTOWN ON", "83.27"),
    ("Mar 22, 2026", "SAMPLE FITNESS CLUB ANYTOWN ON", "54.91"),
    ("Mar 14, 2026", "SAMPLE COFFEE CO ANYTOWN ON", "6.85"),
    ("Mar 05, 2026", "SAMPLE STREAMING SERVICE", "23.72"),
    ("Feb 27, 2026", "SAMPLE PHARMACY ANYTOWN ON", "19.44"),
    ("Feb 19, 2026", "PAYMENT RECEIVED - THANK YOU", "+57.67"),
    ("Feb 11, 2026", "SAMPLE HARDWARE STORE ANYTOWN ON", "112.03"),
    ("Feb 03, 2026", "SAMPLE TRANSIT AUTHORITY", "156.00"),
    ("Jan 25, 2026", "PAYMENT RECEIVED - THANK YOU", "+24.34"),
    ("Jan 22, 2026", "SAMPLE FITNESS CLUB ANYTOWN ON", "54.91"),
    ("Jan 16, 2026", "SAMPLE RESTAURANT ANYTOWN ON", "48.19"),
    ("Jan 09, 2026", "SAMPLE MOBILE CARRIER", "44.07"),
    ("Jan 07, 2026", "INTEREST PURCHASES", "0.64"),
    ("Jan 05, 2026", "SAMPLE STREAMING SERVICE", "23.72"),
    ("Jan 04, 2026", "PAYMENT RECEIVED - THANK YOU", "+50.00"),
    ("Dec 30, 2025", "SAMPLE BOOKSHOP ANYTOWN ON", "31.50"),
    ("Dec 22, 2025", "SAMPLE FITNESS CLUB ANYTOWN ON", "54.91"),
    ("Dec 18, 2025", "PAYMENT RECEIVED - THANK YOU", "+180.00"),
    ("Dec 12, 2025", "SAMPLE ELECTRONICS ANYTOWN ON", "249.99"),
    ("Dec 05, 2025", "SAMPLE STREAMING SERVICE", "23.72"),
    ("Nov 28, 2025", "AUTOMATIC PYMT RECEIVED", "+140.23"),
    ("Nov 20, 2025", "SAMPLE GROCER #101 ANYTOWN ON", "76.40"),
    ("Nov 08, 2025", "SAMPLE RESTAURANT ANYTOWN ON", "88.48"),
]

# Display-only masked card identifier. Never commit a real card number.
CARD = "XXXX-XXXX-XXXX-0890"

def main():
    lines = [
        f"# BMO CashBack Mastercard ({CARD}) — Transactions",
        "",
        "Range: Nov 08, 2025 – Apr 07, 2026 · SYNTHETIC SAMPLE DATA (not real account activity).",
        "",
        "| Transaction Date | Description | Amount | Type |",
        "| --- | --- | ---: | --- |",
    ]
    purchases = credits = 0.0
    for date, desc, amt in ROWS:
        credit = amt.startswith("+")
        val = float(amt.lstrip("+"))
        if credit:
            credits += val
            disp = f"+${val:,.2f}"
            typ = "Money in (payment/credit)"
        else:
            purchases += val
            disp = f"${val:,.2f}"
            typ = "Money out (purchase/fee)"
        lines.append(f"| {date} | {desc} | {disp} | {typ} |")
    lines += [
        "",
        f"**Transactions:** {len(ROWS)}  ",
        f"**Total money out (purchases/fees):** ${purchases:,.2f}  ",
        f"**Total money in (payments/credits):** ${credits:,.2f}  ",
        f"**Net (out − in):** ${purchases - credits:,.2f}",
    ]
    out = "\n".join(lines) + "\n"
    dst = "BMO CashBack Mastercard (normalized).md"
    with open(dst, "w") as f:
        f.write(out)
    print(f"{dst}")
    print(f"  rows={len(ROWS)}  out=${purchases:,.2f}  in=${credits:,.2f}")

if __name__ == "__main__":
    main()
