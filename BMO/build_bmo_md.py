#!/usr/bin/env python3
"""Build a normalized Markdown table from the BMO Mastercard transaction screenshots.
Transcribed by hand from the image-only PDFs (no text layer / OCR available).
"""

# (date, description, signed amount). '+' prefix = money in (credit/payment).
ROWS = [
    ("Apr 07, 2026", "INTEREST PURCHASES", "1.39"),
    ("Apr 05, 2026", "PAYMENT RECEIVED - THANK YOU", "+54.91"),
    ("Feb 22, 2026", "LA FITNESS BRAMPTON ON", "54.91"),
    ("Feb 19, 2026", "PAYMENT RECEIVED - THANK YOU", "+57.67"),
    ("Feb 05, 2026", "PAYPAL *SPOTIFY*P3F0C9 3531****001 GBR", "23.72"),
    ("Jan 25, 2026", "PAYMENT RECEIVED - THANK YOU", "+24.34"),
    ("Jan 22, 2026", "LA FITNESS BRAMPTON ON", "54.91"),
    ("Jan 08, 2026", "FREEDOM MOBILE TORONTO ON", "+21.96"),
    ("Jan 07, 2026", "INTEREST PURCHASES", "0.64"),
    ("Jan 05, 2026", "PAYPAL *SPOTIFY*P3E1B4 3531****001 GBR", "23.72"),
    ("Jan 04, 2026", "PAYMENT RECEIVED - THANK YOU", "+50.00"),
    ("Dec 22, 2025", "LA FITNESS BRAMPTON ON", "54.91"),
    ("Dec 19, 2025", "FREEDOM MOBILE TORONTO ON", "44.07"),
    ("Dec 18, 2025", "PAYMENT RECEIVED - THANK YOU", "+360.32"),
    ("Dec 05, 2025", "INTEREST PURCHASES", "4.56"),
    ("Dec 05, 2025", "PAYPAL *SPOTIFY*P3D1A0 3531****001 GBR", "23.72"),
    ("Dec 02, 2025", "DISHONOURED PAYMENT FEE", "48.00"),
    ("Dec 02, 2025", "DISHONOURED PYMT FEE ADJ", "+48.00"),
    ("Nov 28, 2025", "AUTOMATIC PYMT RECEIVED", "+140.23"),
    ("Nov 28, 2025", "PAYMENT ADJUSTMENT", "140.23"),
    ("Nov 22, 2025", "LA FITNESS BRAMPTON ON", "54.91"),
    ("Nov 19, 2025", "FREEDOM MOBILE TORONTO ON", "38.42"),
    ("Nov 16, 2025", "PAYMENT RECEIVED - THANK YOU", "+100.00"),
    ("Nov 09, 2025", "Cashback/Remises CR", "+38.00"),
    ("Nov 09, 2025", "PAYMENT RECEIVED - THANK YOU", "+10.00"),
    ("Nov 08, 2025", "KOH LIPE THAI KITCHEN TORONTO ON", "88.48"),
    ("Nov 05, 2025", "PAYPAL *SPOTIFY*P3C1FD 3531****001 GBR", "23.72"),
    ("Nov 01, 2025", "DOLLARAMA # 359 SCARBOROUGH ON", "3.39"),
    ("Nov 01, 2025", "LCBO/RAO #660 TORONTO ON", "7.90"),
    ("Nov 01, 2025", "MICHAEL'S NO FRILLS 69 SCARBOROUGH ON", "10.49"),
    ("Oct 23, 2025", "LA FITNESS TORONTO ON", "166.31"),
    ("Oct 19, 2025", "FREEDOM MOBILE TORONTO ON", "38.42"),
    ("Oct 08, 2025", "PAYMENT RECEIVED - THANK YOU", "+48.27"),
    ("Oct 05, 2025", "PAYPAL *SPOTIFY*P3B330 3531****001 GBR", "23.72"),
    ("Sep 19, 2025", "FREEDOM MOBILE 877-946-3184 ON", "38.42"),
    ("Sep 05, 2025", "PAYPAL *SPOTIFY*P3A3AF 3531****001 GBR", "23.72"),
    ("Aug 28, 2025", "MAPLE SHAWARMA WHITBY ON", "13.56"),
    ("Aug 23, 2025", "TIM HORTONS #1910 SCARBOROUGH ON", "14.51"),
    ("Aug 19, 2025", "FREEDOM MOBILE 877-946-3184 ON", "38.42"),
    ("Aug 18, 2025", "MAPLE SHAWARMA WHITBY ON", "15.81"),
    ("Aug 18, 2025", "MICHAEL'S NO FRILLS 69 SCARBOROUGH ON", "20.75"),
    ("Aug 16, 2025", "TIM HORTONS #8486 BROOKLIN ON", "8.79"),
    ("Aug 15, 2025", "ESCAPE GAMES CANADA NORTH YORK ON", "42.00"),
    ("Aug 05, 2025", "PAYPAL *SPOTIFY*P393D7 3531****001 GBR", "23.72"),
    ("Jul 30, 2025", "SQ *PIAZZA MANNA NORTH YORK ON", "6.77"),
    ("Jul 27, 2025", "SQ *MIZZICA GELATERIA Toronto ON", "7.74"),
    ("Jul 26, 2025", "DAIRY QUEEN #11949 TORONTO ON", "8.80"),
    ("Jul 25, 2025", "TST-BFF Toronto Toronto ON", "10.17"),
    ("Jul 23, 2025", "BULK BARN 767 TORONTO TORONTO ON", "4.34"),
    ("Jul 22, 2025", "GELATO NORTH TORONTO ON", "8.00"),
    ("Jul 19, 2025", "FREEDOM MOBILE 877-946-3184 ON", "38.42"),
    ("Jul 19, 2025", "MARSHALLS 702 TORONTO ON", "28.24"),
    ("Jul 19, 2025", "WINNERS 222 TORONTO ON", "100.52"),
    ("Jul 19, 2025", "TIM HORTONS #8141 TORONTO ON", "2.72"),
    ("Jul 18, 2025", "SQ *PIAZZA MANNA NORTH YORK ON", "15.20"),
    ("Jul 12, 2025", "LA FITNESS BRAMPTON ON", "+45.19"),
    ("Jul 12, 2025", "LA FITNESS BRAMPTON ON", "+45.19"),
    ("Jul 12, 2025", "LA FITNESS BRAMPTON ON", "+77.97"),
    ("Jul 12, 2025", "LA FITNESS BRAMPTON ON", "+45.19"),
    ("Jul 12, 2025", "LA FITNESS BRAMPTON ON", "+45.19"),
    ("Jul 12, 2025", "LA FITNESS BRAMPTON ON", "+45.19"),
    ("Jul 12, 2025", "LA FITNESS BRAMPTON ON", "+45.19"),
    ("Jul 12, 2025", "LA FITNESS BRAMPTON ON", "+45.19"),
    ("Jul 12, 2025", "LA FITNESS BRAMPTON ON", "+45.19"),
    ("Jul 01, 2025", "PAYMENT RECEIVED - THANK YOU", "+45.00"),
    ("Jun 30, 2025", "AUTOMATIC PYMT RECEIVED", "+7.22"),
    ("Jun 19, 2025", "FREEDOM MOBILE 877-946-3184 ON", "38.42"),
    ("May 22, 2025", "PAYMENT RECEIVED - THANK YOU", "+160.00"),
    ("May 19, 2025", "FREEDOM MOBILE 877-946-3184 ON", "38.42"),
    ("May 16, 2025", "LA FITNESS BRAMPTON ON", "45.19"),
    ("Apr 28, 2025", "AUTOMATIC PYMT RECEIVED", "+0.15"),
    ("Apr 19, 2025", "FREEDOM MOBILE 877-946-3184 ON", "38.42"),
    ("Apr 16, 2025", "LA FITNESS BRAMPTON ON", "45.19"),
    ("Apr 14, 2025", "PAYMENT RECEIVED - THANK YOU", "+160.00"),
    ("Mar 28, 2025", "AUTOMATIC PYMT RECEIVED", "+94.91"),
    ("Mar 22, 2025", "LA FITNESS TORONTO ON", "42.21"),
    ("Mar 21, 2025", "LA FITNESS BRAMPTON ON", "11.30"),
    ("Mar 19, 2025", "FREEDOM MOBILE 877-946-3184 ON", "61.45"),
    ("Mar 16, 2025", "LA FITNESS BRAMPTON ON", "45.19"),
    ("Feb 21, 2025", "LA FITNESS BRAMPTON ON", "11.30"),
    ("Feb 19, 2025", "FREEDOM MOBILE 877-946-3184 ON", "38.42"),
    ("Feb 16, 2025", "LA FITNESS BRAMPTON ON", "45.19"),
    ("Jan 26, 2025", "PAYMENT RECEIVED - THANK YOU", "+138.52"),
    ("Jan 21, 2025", "LA FITNESS BRAMPTON ON", "54.91"),
    ("Jan 19, 2025", "FREEDOM MOBILE 877-946-3184 ON", "38.42"),
    ("Jan 16, 2025", "LA FITNESS BRAMPTON ON", "45.19"),
    ("Dec 30, 2024", "PAYMENT RECEIVED - THANK YOU", "+138.52"),
    ("Dec 21, 2024", "LA FITNESS BRAMPTON ON", "54.91"),
    ("Dec 19, 2024", "FREEDOM MOBILE 877-946-3184 ON", "38.42"),
    ("Dec 16, 2024", "LA FITNESS BRAMPTON ON", "45.19"),
    ("Dec 15, 2024", "PAYMENT RECEIVED - THANK YOU", "+67.93"),
    ("Dec 04, 2024", "TRSF FROM/DE ACCT/CPT 0450-XXXX-998", "+3.99"),
    ("Nov 29, 2024", "TRSF FROM/DE ACCT/CPT 0450-XXXX-998", "+1.63"),
    ("Nov 21, 2024", "LA FITNESS BRAMPTON ON", "54.91"),
    ("Nov 19, 2024", "FREEDOM MOBILE 877-946-3184 ON", "38.42"),
    ("Nov 16, 2024", "LA FITNESS BRAMPTON ON", "45.19"),
    ("Nov 13, 2024", "TRSF FROM/DE ACCT/CPT 0450-XXXX-998", "+91.49"),
    ("Oct 29, 2024", "PAYMENT RECEIVED - THANK YOU", "+112.00"),
    ("Oct 28, 2024", "AUTOMATIC PYMT RECEIVED", "+29.49"),
    ("Oct 21, 2024", "LA FITNESS BRAMPTON ON", "54.91"),
    # ----- page 2 of the list (items 101-126) -----
    ("Oct 19, 2024", "FREEDOM MOBILE 877-946-3184 ON", "38.42"),
    ("Oct 16, 2024", "LA FITNESS BRAMPTON ON", "45.19"),
    ("Oct 16, 2024", "PAYMENT RECEIVED - THANK YOU", "+112.53"),
    ("Oct 16, 2024", "TRSF FROM/DE ACCT/CPT 0450-XXXX-998", "+95.95"),
    ("Oct 05, 2024", "LA FITNESS ANNUAL FEE BRAMPTON ON", "66.67"),
    ("Sep 30, 2024", "LA FITNESS ANNUAL FEE BRAMPTON ON", "77.97"),
    ("Sep 21, 2024", "LA FITNESS BRAMPTON ON", "54.91"),
    ("Sep 19, 2024", "FREEDOM MOBILE 877-946-3184 ON", "38.42"),
    ("Sep 10, 2024", "PAYMENT RECEIVED - THANK YOU", "+112.53"),
    ("Sep 05, 2024", "Spotify P2F2B208D9 Stockholm SWE", "19.20"),
    ("Aug 21, 2024", "LA FITNESS BRAMPTON ON", "54.91"),
    ("Aug 19, 2024", "FREEDOM MOBILE 877-946-3184 ON", "38.42"),
    ("Aug 14, 2024", "PAYMENT RECEIVED - THANK YOU", "+112.53"),
    ("Aug 05, 2024", "Spotify P2E47DA017 Stockholm SWE", "19.20"),
    ("Jul 21, 2024", "LA FITNESS BRAMPTON ON", "54.91"),
    ("Jul 19, 2024", "FREEDOM MOBILE 877-946-3184 ON", "38.42"),
    ("Jul 16, 2024", "PAYMENT RECEIVED - THANK YOU", "+164.18"),
    ("Jul 05, 2024", "Spotify P2D7DB7F2D Stockholm SWE", "19.20"),
    ("Jul 01, 2024", "SHELL EASYPAY C02155 SCARBOROUGH ON", "71.65"),
    ("Jun 21, 2024", "LA FITNESS BRAMPTON ON", "54.91"),
    ("Jun 19, 2024", "FREEDOM MOBILE 877-946-3184 ON", "38.42"),
    ("Jun 19, 2024", "SHELL EASYPAY C02254 SCARBOROUGH ON", "20.00"),
    ("Jun 19, 2024", "PAYMENT RECEIVED - THANK YOU", "+102.09"),
    ("Jun 07, 2024", "SHELL EASYPAY C02155 SCARBOROUGH ON", "42.89"),
    ("Jun 05, 2024", "Spotify P2CBEE304F Stockholm SWE", "19.20"),
    ("Jun 03, 2024", "PAYMENT RECEIVED - THANK YOU", "+93.33"),
]

CARD = "5191-2301-9871-0890"

def main():
    lines = [
        "# BMO CashBack Mastercard (5191-2301-9871-0890) — Transactions",
        "",
        "Range: Jan 01, 2021 – Jun 04, 2026 (as shown) · transcribed from image-only PDF exports.",
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
