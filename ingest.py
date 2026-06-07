#!/usr/bin/env python3
"""
ingest.py — shared ingestion + analytics library for the Expense Tracker.

Pure Python stdlib (zlib + cp037 + sqlite-free here). Used by BOTH the CLI
generator (build_dashboard.py) and the local backend (server.py), so the
EBCDIC PDF parsing, FX handling, merchant mapping, and the smart-feature
algorithms (recurring detection, anomalies, forecast) live in exactly one place.

Key parsing facts:
- Scotiabank PDFs store text in EBCDIC (cp037) fonts inside FlateDecode streams;
  there is no PDF lib installed, so streams are decoded directly.
- Use the permissive `stream[\\r\\n]+(.*?)endstream` capture — the strict form
  drops page-3 "continued" transactions.
- DETAILS is a fixed-width 25-char merchant field + city + province.
- Foreign-currency rows carry two amounts ("AMT 178.48 USD 248.09"); the posted
  CAD amount is the second one.
"""

import csv
import glob
import os
import re
import zlib
from collections import defaultdict
from datetime import date, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PDF_DIR = os.path.join(HERE, "Scotiabank 2026 e-statements")
STATEMENT_YEAR = 2026

MONTHS = {m: i for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}

MERCHANT_FIELD_WIDTH = 25

# keyword (in upper-cased 25-char field) -> (display name, category).
# Ordered most-specific first; first match wins. Seeds the DB rules table.
MERCHANTS = [
    ("ANNUAL FEE", "Annual Fee", "Fees & Interest"),
    ("INTEREST CHARGES", "Interest Charges", "Fees & Interest"),
    ("TICKETMASTER", "Ticketmaster", "Entertainment"),
    ("CINEPLEX", "Cineplex", "Entertainment"),
    ("BLIZZARD", "Blizzard", "Entertainment"),
    ("COCA-COLA COLISEUM", "Coca-Cola Coliseum", "Entertainment"),
    ("ACTIVATE TORONTO", "Activate Toronto", "Entertainment"),
    ("BRIMACOMBE", "Brimacombe Ski", "Entertainment"),
    ("LAN AIRLINE", "LATAM Airlines", "Travel"),
    ("FLIGHTHUB", "FlightHub", "Travel"),
    ("EXPEDIA", "Expedia", "Travel"),
    ("SPOTIFY", "Spotify", "Subscriptions"),
    ("FREEDOM MOBILE", "Freedom Mobile", "Subscriptions"),
    ("HELLO MOBILE", "Hello Mobile", "Subscriptions"),
    ("LA FITNESS", "LA Fitness", "Subscriptions"),
    ("SUPERCELL", "Supercell", "Subscriptions"),
    ("COSTCO", "Costco / Instacart", "Groceries"),
    ("FARM BOY", "Farm Boy", "Groceries"),
    ("MICHAEL'S NO FRILLS", "Michael's No Frills", "Groceries"),
    ("HEALTHY PLANET", "Healthy Planet", "Groceries"),
    ("DOLLARAMA", "Dollarama", "Groceries"),
    ("DOLLAR TREE", "Dollar Tree", "Groceries"),
    ("LCBO", "LCBO", "Groceries"),
    ("TORONTO PARKING", "Toronto Parking", "Transport"),
    ("CANADIAN TIRE", "Canadian Tire", "Shopping"),
    ("WINNERS", "Winners", "Shopping"),
    ("SHOPPERS DRUG MART", "Shoppers Drug Mart", "Health & Pharmacy"),
    ("OVERLEA PHARMACY", "Overlea Pharmacy", "Health & Pharmacy"),
    ("GOFNDME", "GoFundMe", "Giving"),
    ("GOFUNDME", "GoFundMe", "Giving"),
    ("AU PAIN DORE", "Au Pain Doré", "Food & Dining"),
    ("MR. SOUVLAKI", "Mr. Souvlaki", "Food & Dining"),
    ("TST-PAI", "Pai Northern Thai", "Food & Dining"),
    ("MIZZICA", "Mizzica Gelateria", "Food & Dining"),
    ("MR. PUFFS", "Mr. Puffs", "Food & Dining"),
    ("CHIPOTLE", "Chipotle", "Food & Dining"),
    ("KING SHAWARMA", "King Shawarma", "Food & Dining"),
    ("MESSINI", "Messini Gyro", "Food & Dining"),
    ("D SPOT", "D Spot Dessert Cafe", "Food & Dining"),
    ("COCO FRESH", "Coco Fresh Tea & Juice", "Food & Dining"),
    ("SHELBYS", "Shelbys", "Food & Dining"),
    ("EGGSTATIC", "Eggstatic", "Food & Dining"),
    ("NAAN AND KABOB", "Naan and Kabob", "Food & Dining"),
    ("MCDONALD", "McDonald's", "Food & Dining"),
    ("ANDREAS", "Andreas Cookies", "Food & Dining"),
    ("ISABELLA", "Isabella's Mochi Donut", "Food & Dining"),
    ("VIET THAI", "Viet Thai Kitchen", "Food & Dining"),
    ("BRAZEN HEAD", "Brazen Head Pub", "Food & Dining"),
    ("ROYWOODS", "Roywoods", "Food & Dining"),
    ("SAKU", "Saku", "Food & Dining"),
    ("SANKOFA", "Jack's Sankofa Square", "Food & Dining"),
    ("DOORDASH", "DoorDash", "Food & Dining"),
]

# Additional rules covering the Tangerine Mastercard's merchant tail.
# (Matched against the full free-form description, most-specific first.)
MERCHANTS += [
    # Transport — transit, gas, rideshare, parking, auto
    ("PRESTO", "Presto Transit", "Transport"),
    ("SHELL", "Shell Gas", "Transport"),
    ("ESSO", "Esso", "Transport"),
    ("PETRO-CANADA", "Petro-Canada", "Transport"),
    ("UBERTRIP", "Uber", "Transport"),
    ("UBER CANADA/UBERTRIP", "Uber", "Transport"),
    ("LYFT", "Lyft", "Transport"),
    ("BIKE SHARE", "Bike Share Toronto", "Transport"),
    ("SPOTHERO", "SpotHero Parking", "Transport"),
    ("TWINS AUTOWORKS", "Twins Autoworks", "Transport"),
    ("SHINE AUTO", "Shine Auto Sales", "Transport"),
    ("MTO TSD", "Ontario MTO", "Transport"),
    ("COIN WASH", "Car Wash", "Transport"),
    ("PARTSOUQ", "PartSouq (auto parts)", "Transport"),
    # Travel
    ("LAN AIR", "LATAM Airlines", "Travel"),
    ("INCA RAIL", "Inca Rail", "Travel"),
    ("VIATOR", "Viator", "Travel"),
    ("HOSTELWORLD", "Hostelworld", "Travel"),
    ("UNIDAD EJECUTORA", "Machu Picchu (Peru)", "Travel"),
    ("HARBOUR WA", "Toronto Harbour Tours", "Travel"),
    # Health & wellness
    ("WELLNESS SPA", "Wellness Spa", "Health & Pharmacy"),
    ("TSINGTAO WELLNESS", "Tsingtao Wellness Spa", "Health & Pharmacy"),
    ("TCM CLINIC", "TCM Clinic", "Health & Pharmacy"),
    ("REHABILITATION", "Rehab Clinic", "Health & Pharmacy"),
    ("RECREO REHAB", "Recreo Rehab", "Health & Pharmacy"),
    ("SUPPLEMENT KING", "Supplement King", "Health & Pharmacy"),
    ("GENERAL HOSPITAL", "Hospital", "Health & Pharmacy"),
    # Subscriptions / digital
    ("TELUS MOBILITY", "Telus Mobility", "Subscriptions"),
    ("COURSERA", "Coursera", "Subscriptions"),
    ("CLOUDFLARE", "Cloudflare", "Subscriptions"),
    ("APPLE.COM", "Apple", "Subscriptions"),
    ("PRIME MEMBER", "Amazon Prime", "Subscriptions"),
    ("AMAZON.CA PRIME", "Amazon Prime", "Subscriptions"),
    ("CANVAPTYLIM", "Canva", "Subscriptions"),
    ("CANVA", "Canva", "Subscriptions"),
    # Entertainment
    ("WONDERLAND", "Canada's Wonderland", "Entertainment"),
    ("CANADASWOND", "Canada's Wonderland", "Entertainment"),
    ("SCOTIABANK ARENA", "Scotiabank Arena", "Entertainment"),
    ("TMCANADA", "Ticketmaster Resale", "Entertainment"),
    ("GAMETIMETIX", "GameTime Tickets", "Entertainment"),
    ("AIR RIDERZ", "Air Riderz", "Entertainment"),
    ("FEVER", "Fever Events", "Entertainment"),
    ("ARTVENTURES", "ArtVentures", "Entertainment"),
    ("EB GAMES", "EB Games", "Entertainment"),
    ("JAYSSHOP", "Blue Jays Shop", "Entertainment"),
    # Shopping / retail
    ("MEC MOUNTAIN", "MEC", "Shopping"),
    ("ADIDAS", "Adidas", "Shopping"),
    ("GAP CANADA", "Gap", "Shopping"),
    ("SAXX", "Saxx", "Shopping"),
    ("TOYS R US", "Toys R Us", "Shopping"),
    ("HOME DEPOT", "Home Depot", "Shopping"),
    ("DECIEM", "Deciem", "Shopping"),
    ("SEPHORA", "Sephora", "Shopping"),
    ("DOWNTOWN CAMERA", "Downtown Camera", "Shopping"),
    ("WAL-MART", "Walmart", "Shopping"),
    ("WMT SUPRCTR", "Walmart", "Shopping"),
    ("WMT ", "Walmart", "Shopping"),
    ("JUST PRINT", "Just Print Canada", "Shopping"),
    ("GROUPON", "Groupon", "Shopping"),
    ("ROCKWOOD CANNABIS", "Rockwood Cannabis", "Shopping"),
    # Groceries / convenience
    ("LONGO", "Longo's", "Groceries"),
    ("FOOD BASICS", "Food Basics", "Groceries"),
    ("IQBAL FOODS", "Iqbal Foods", "Groceries"),
    ("FINCH JOY MART", "Finch Joy Mart", "Groceries"),
    ("LIVER CANADA", "Liver Canada", "Groceries"),
    ("COUNTRY STOR", "Country Store", "Groceries"),
    # PayPal sub-merchants (PayPal is just the processor)
    ("PAYPAL *SEPHORA", "Sephora", "Shopping"),
    ("PAYPAL *COURSERA", "Coursera", "Subscriptions"),
    # Generic food catch-alls (all safe — these words only appear on eateries)
    ("SUSHI", "Sushi", "Food & Dining"),
    ("SHAWARMA", "Shawarma", "Food & Dining"),
    (" THAI", "Thai", "Food & Dining"),
    ("NOODLE", "Noodles", "Food & Dining"),
    ("BURGER", "Burgers", "Food & Dining"),
    ("BURRITO", "Burrito", "Food & Dining"),
    (" PHO ", "Pho", "Food & Dining"),
    ("DONER", "Doner", "Food & Dining"),
    ("AND GRILL", "Grill", "Food & Dining"),
    ("GRILL HOUSE", "Grill House", "Food & Dining"),
    ("TIKKA", "Tikka", "Food & Dining"),
    ("HAKKA", "Hakka", "Food & Dining"),
    ("PERSIAN", "Persian", "Food & Dining"),
    ("KRISPY KREME", "Krispy Kreme", "Food & Dining"),
    ("CINNABON", "Cinnabon", "Food & Dining"),
    ("POPEYES", "Popeyes", "Food & Dining"),
    ("OSMOW", "Osmow's", "Food & Dining"),
    ("POTATO", "Potato Bar", "Food & Dining"),
    ("DESSERT", "Dessert", "Food & Dining"),
    ("DESERT", "Dessert", "Food & Dining"),
    ("CAFE", "Cafe", "Food & Dining"),
    ("JACK ASTOR", "Jack Astor's", "Food & Dining"),
    ("ST LOUIS BAR", "St. Louis Bar & Grill", "Food & Dining"),
    ("KING TAPS", "King Taps", "Food & Dining"),
    ("SASSAFRAZ", "Sassafraz", "Food & Dining"),
    ("LAHORE TIKKA", "Lahore Tikka House", "Food & Dining"),
    ("BON ITALIA", "Bon Italia", "Food & Dining"),
    ("EGG CLUB", "Egg Club", "Food & Dining"),
    ("DOUGHBOX", "Doughbox", "Food & Dining"),
    ("BAR BURRITO", "Bar Burrito", "Food & Dining"),
    ("CASSIUS", "Cassius", "Food & Dining"),
    ("KOREAN GRILL", "Korean Grill House", "Food & Dining"),
    ("BEST HAKKA", "Best Hakka", "Food & Dining"),
    ("MAPLE SHAWARMA", "Maple Shawarma", "Food & Dining"),
    ("ALADDIN SHAWARMA", "Aladdin Shawarma", "Food & Dining"),
    ("RAVINE CAFE", "Ravine Cafe", "Food & Dining"),
    ("SAHAN", "Sahan Restaurant", "Food & Dining"),
    ("GULGUL", "GulGul", "Food & Dining"),
    ("KING #557", "Krispy Kreme", "Food & Dining"),
    ("HEAVENLY DESSERT", "Heavenly Desserts", "Food & Dining"),
    ("BUBBLICIOUS", "Bubblicious", "Food & Dining"),
    ("FIKA SUPPLY", "Fika", "Food & Dining"),
    ("FINCH", "Finch Eatery", "Food & Dining"),
    ("UBEREATS", "Uber Eats", "Food & Dining"),
    ("PHO DAC", "Pho Dac Biet", "Food & Dining"),
    ("BUK CHANG", "Buk Chang Dong", "Food & Dining"),
    ("PIAZZA MANNA", "Piazza Manna", "Food & Dining"),
    ("ISABELLE", "Isabelle's", "Food & Dining"),
    ("B BOYZ", "B Boyz", "Food & Dining"),
    ("TBJ CONCESSION", "TBJ Concessions", "Food & Dining"),
    ("YONGE POTATO", "Yonge Potato", "Food & Dining"),
    ("TANGY MADE", "Tangy Made", "Food & Dining"),
    ("CASHEW AND CLIVE", "Cashew & Clive", "Food & Dining"),
    # Amex tail
    ("AMAZON", "Amazon", "Shopping"),
    ("AMZN", "Amazon", "Shopping"),
    ("RETURNED PAYMENT", "Returned Payment", "Fees & Interest"),
    ("CREDITOR INSURANCE", "Creditor Insurance", "Fees & Interest"),
    # BMO tail
    ("INTEREST PURCHASES", "Interest Charges", "Fees & Interest"),
    ("PAYMENT ADJUSTMENT", "Payment Adjustment", "Fees & Interest"),
    ("DISHONOURED PAYMENT", "Dishonoured Payment Fee", "Fees & Interest"),
    ("TIM HORTONS", "Tim Hortons", "Food & Dining"),
    ("DAIRY QUEEN", "Dairy Queen", "Food & Dining"),
    ("GELATO", "Gelato", "Food & Dining"),
    ("TST-BFF", "BFF", "Food & Dining"),
    ("MARSHALLS", "Marshalls", "Shopping"),
    ("ESCAPE GAMES", "Escape Games", "Entertainment"),
    ("ESCAPESIM", "Escape eSIM", "Travel"),
    ("BULK BARN", "Bulk Barn", "Groceries"),
]

EXCLUDE = ["PAYMENT - THANK YOU"]            # card payments are not spending

ROW_RE = re.compile(
    r"\b(\d{3})\s+([A-Z][a-z]{2} \d{1,2})\s+([A-Z][a-z]{2} \d{1,2})\s+"
    r"(.*?)\s+([\d,]+\.\d{2})"               # details + first amount
    r"(?:\s+[A-Z]{3}\s+([\d,]+\.\d{2}))?"    # optional FX: "USD 248.09" -> posted CAD
)


def resolve(details, rules=None, width=MERCHANT_FIELD_WIDTH):
    """Map a raw DETAILS string to (display_name, category) via the keyword rules.

    Scotiabank uses a fixed 25-char merchant field (width=25). Tangerine
    descriptions are free-form, so pass width=None to match the full string.
    """
    field = (details[:width] if width else details).rstrip()
    up = field.upper()
    for kw, name, cat in (rules or MERCHANTS):
        if kw in up:
            return name, cat
    # fallback "Other": trim a trailing "  CITY PROV" so the display stays tidy
    clean = re.sub(r"\s+[A-Z][A-Za-z]+\s+[A-Z]{2}\s*$", "", field).strip() or field
    return clean[:32], "Other"


def extract_text(path):
    data = open(path, "rb").read()
    streams = re.findall(rb"stream[\r\n]+(.*?)endstream", data, re.S)
    chunks = []
    for s in streams:
        d = None
        for cand in (s, s.rstrip(b"\r\n"), s.strip()):
            try:
                d = zlib.decompress(cand)
                break
            except zlib.error:
                d = None
        if not d:
            continue
        parts = re.findall(rb"\((?:[^()\\]|\\.)*\)", d)
        if not parts:
            continue
        decoded = [(p[1:-1].replace(b"\\(", b"(").replace(b"\\)", b")")
                    .replace(b"\\\\", b"\\")).decode("cp037", "replace") for p in parts]
        chunks.append(" ".join(decoded))
    return " ".join(chunks)


def _money(text, pattern):
    m = re.search(pattern, text)
    return float(m.group(1).replace(",", "")) if m else 0.0


def parse_pdf(path, rules=None, year=STATEMENT_YEAR):
    """Parse one statement PDF -> (transactions, statement_summary).

    transactions: list of {date, merchant, raw, amount, category, ref, source}
    statement: {date, label, purchases, payments, interest, balance} or None
    """
    fname = os.path.basename(path)
    text = extract_text(path)
    txns, seen = [], set()
    for ref, tdate, _post, details, amount, cad in ROW_RE.findall(text):
        if any(x in details.upper() for x in EXCLUDE):
            continue
        if ref in seen:
            continue
        seen.add(ref)
        mon, day = tdate.split()
        d = date(year, MONTHS[mon], int(day)).isoformat()
        amt = float((cad or amount).replace(",", ""))    # FX: posted CAD is 2nd figure
        field = details[:MERCHANT_FIELD_WIDTH].rstrip()  # exact field for rule re-apply
        merchant, category = resolve(details, rules)
        txns.append({
            "date": d, "merchant": merchant,
            "raw": re.sub(r"\s{2,}", " ", details.strip()),
            "amount": round(amt, 2), "category": category,
            "ref": ref, "source": fname, "field": field,
        })
    stmt = None
    m = re.search(r"Statement Date\s+([A-Z][a-z]{2}) (\d{1,2}), (\d{4})", text)
    if m:
        mon, day, yr = m.group(1), int(m.group(2)), int(m.group(3))
        purchases = _money(text, r"Purchases/charges\s*\+?\s*\$?([\d,]+\.\d{2})")
        payments = _money(text, r"Payments/credits\s*-?\s*\$?([\d,]+\.\d{2})")
        interest = _money(text, r"Interest\s*\+?\s*\$?([\d,]+\.\d{2})")
        previous = _money(text, r"Previous balance,[^$]*\$([\d,]+\.\d{2})")
        stmt = {
            "date": date(yr, MONTHS[mon], day).isoformat(),
            "label": f"{mon} {yr}", "source": fname,
            "purchases": round(purchases, 2), "payments": round(payments, 2),
            "interest": round(interest, 2),
            "balance": round(previous + purchases - payments + interest, 2),
        }
    return txns, stmt


def parse_dir(pdf_dir=DEFAULT_PDF_DIR, rules=None):
    """Parse every PDF in a directory -> (transactions, statements), deduped."""
    txns, stmts, seen = [], [], set()
    pdfs = sorted(glob.glob(os.path.join(pdf_dir, "*.pdf")))
    if not pdfs:
        raise SystemExit(f"No PDFs found in {pdf_dir}")
    for path in pdfs:
        t, s = parse_pdf(path, rules)
        for r in t:
            key = (r["source"], r["ref"])
            if key in seen:
                continue
            seen.add(key)
            txns.append(r)
        if s:
            stmts.append(s)
    txns.sort(key=lambda r: (r["date"], r["merchant"]))
    stmts.sort(key=lambda s: s["date"])
    return txns, stmts


# Back-compat thin wrappers used by build_dashboard.py
def parse_transactions(pdf_dir=DEFAULT_PDF_DIR):
    return parse_dir(pdf_dir)[0]


def parse_statements(pdf_dir=DEFAULT_PDF_DIR):
    return parse_dir(pdf_dir)[1]


# --- Tangerine adapter (normalized markdown tables) -------------------------
TANGERINE_DIR = os.path.join(HERE, "Tangerine")
_MD_DATE = re.compile(r"^([A-Z][a-z]{2}) (\d{1,2}), (\d{4})$")
# Internal transfers / borrowing — NOT real income/spending for cash-flow purposes
INTERNAL_RE = re.compile(
    r"tangerine savings|line of credit|to tangerine|from tangerine|"
    r"to ws investments|to wealthsimple|own account|to savings|from savings",
    re.I)
# Own name (transfers between the user's own accounts look like e-transfers)
OWN_NAME = "NHIHAD"
# Bank names — "EFT/Internet Deposit from <BANK>" is an inter-account transfer, not income
_BANK_RE = re.compile(
    r"from:?\s+(the toronto|toronto-domin|bank of montr|\bbmo\b|\btd\b|cibc|"
    r"\brbc\b|scotiabank|simplii|wealthsimple|questrade)", re.I)

# How each deposit is classified for income purposes.
PRIMARY_INCOME = {"income", "government", "cheque"}     # counts as real income


def classify_deposit(desc):
    """Bucket a chequing deposit so income excludes transfers/reimbursements."""
    d = desc.lower()
    if INTERNAL_RE.search(desc) or OWN_NAME.lower() in d:
        return "internal"          # savings/LOC/investments/own-account moves
    if "interest paid" in d:
        return "interest"
    if _BANK_RE.search(desc):
        return "transfer"          # money shuffled from another bank account
    if "from: canada" in d or "from canada" in d or "canada fed" in d:
        return "government"        # CRA / federal benefits
    if "cheque-in" in d or "cheque deposit" in d:
        return "cheque"            # deposited cheques (often pay)
    if "e-transfer from" in d or "e-transfer received" in d:
        return "etransfer"         # peer e-transfer — reimbursement/gift, not income
    if "deposit from" in d:        # EFT/Internet deposit from a company = payroll/business
        return "income"
    return "other"


def _md_rows(path):
    rows = []
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if not cells or cells[0] in ("Date", "") or set(cells[0]) <= set("-"):
            continue
        rows.append(cells)
    return rows


def _md_date(s):
    m = _MD_DATE.match(s)
    if not m:
        return None
    return date(int(m.group(3)), MONTHS[m.group(1)], int(m.group(2))).isoformat()


def _md_money(s):
    neg = s.strip().startswith("-")
    return float(re.sub(r"[+\-$,\s]", "", s)), neg


def _seq_ref(seen, date, desc, amount):
    """Stable, collision-free ref for sources without a native transaction id.
    Uses the full description + a per-(date,desc,amount) occurrence index, so two
    genuinely-identical rows get distinct refs while re-imports stay idempotent."""
    base = f"{date}|{desc}|{amount}"
    i = seen.get(base, 0)
    seen[base] = i + 1
    return f"{base}#{i}"


def parse_tangerine_cc(path, rules=None, account="Tangerine Mastercard"):
    """Credit-card purchases → spending records (payments/credits excluded)."""
    out = []
    seen = {}
    for cells in _md_rows(path):
        # Date | Description | Card | Amount | Type | Cash-Back
        if len(cells) < 5:
            continue
        d = _md_date(cells[0])
        if not d or cells[4] != "Purchase":
            continue
        amt, _ = _md_money(cells[3])
        merchant, category = resolve(cells[1], rules, width=None)
        out.append({
            "date": d, "merchant": merchant, "raw": cells[1],
            "amount": round(amt, 2), "category": category,
            "ref": _seq_ref(seen, d, cells[1], cells[3]), "source": account,
            "field": cells[1], "account": account, "account_type": "card",
        })
    out.sort(key=lambda r: (r["date"], r["merchant"]))
    return out


def parse_tangerine_chq(path, account="Tangerine Chequing"):
    """Chequing → cash-flow records with deposit/withdrawal kind + running balance."""
    out = []
    for cells in _md_rows(path):
        # Date | Description | Amount | Type | Balance
        if len(cells) < 4:
            continue
        d = _md_date(cells[0])
        if not d:
            continue
        amt, neg = _md_money(cells[2])
        kind = "deposit" if cells[3] == "Deposit" else "withdrawal"
        bal = _md_money(cells[4])[0] if len(cells) > 4 and cells[4] else None
        dep_type = classify_deposit(cells[1]) if kind == "deposit" else None
        internal = bool(INTERNAL_RE.search(cells[1])) or dep_type == "internal"
        out.append({
            "date": d, "desc": cells[1], "amount": round(amt, 2), "kind": kind,
            "balance": bal, "internal": internal, "dep_type": dep_type,
            "is_income": dep_type in PRIMARY_INCOME, "account": account,
        })
    out.sort(key=lambda r: r["date"])
    return out


# --- Amex adapter (year-end summary CSVs) -----------------------------------
AMEX_DIR = os.path.join(HERE, "amex")
# Fallback when the merchant keyword doesn't match: map Amex's own sub-category.
AMEX_SUBCAT = {
    "Fee Services": "Fees & Interest", "Communications": "Subscriptions",
    "Entertainment": "Entertainment", "Travel Other": "Travel",
    "Mail Order/Telephone": "Shopping", "Merchandise Other": "Shopping",
    "Retail": "Shopping",
}


def parse_amex_csv(path, rules=None, account="Amex"):
    """Amex year-end CSV → spending records (Charges only; Credits are payments)."""
    out = []
    seen = {}
    with open(path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            try:
                charge = float(row.get("Charges $") or 0)
            except ValueError:
                charge = 0
            if charge <= 0:
                continue
            d, m, y = row["Date"].split("/")
            iso = f"{y}-{int(m):02d}-{int(d):02d}"
            desc = re.sub(r"\s{2,}", " ", row["Transaction"].strip())
            name, cat = resolve(desc, rules, width=None)
            if cat == "Other":
                cat = AMEX_SUBCAT.get(row.get("Sub-Category", ""), "Other")
            out.append({
                "date": iso, "merchant": name, "raw": desc,
                "amount": round(charge, 2), "category": cat,
                "ref": _seq_ref(seen, iso, desc, f"{charge:.2f}"),
                "source": account, "field": desc,
                "account": account, "account_type": "card",
            })
    return out


# --- BMO adapter (CSV: Date,Description,Amount,Direction,AbsAmount,Account,CardLast4) ----
BMO_DIR = os.path.join(HERE, "BMO")


def parse_bmo_csv(path, rules=None, account="BMO Mastercard"):
    """BMO CSV → spending records (Direction 'out' only; 'in' = payments/credits)."""
    out = []
    seen = {}
    with open(path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            if (row.get("Direction") or "").strip().lower() != "out":
                continue                      # skip payments/credits
            desc = re.sub(r"\s{2,}", " ", row["Description"].strip())
            if "PAYMENT RECEIVED" in desc.upper():
                continue
            try:
                amt = abs(float(row.get("AbsAmount") or row.get("Amount") or 0))
            except ValueError:
                continue
            if amt <= 0:
                continue
            iso = row["Date"].strip()         # already YYYY-MM-DD
            name, cat = resolve(desc, rules, width=None)
            out.append({
                "date": iso, "merchant": name, "raw": desc,
                "amount": round(amt, 2), "category": cat,
                "ref": _seq_ref(seen, iso, desc, f"{amt:.2f}"),
                "source": account, "field": desc,
                "account": account, "account_type": "card",
            })
    out.sort(key=lambda r: r["date"])
    return out


# --- Payments / credits (the inverse of purchases) — for Spend-vs-Payments ----
def _scotia_payments(pdf_dir=DEFAULT_PDF_DIR, year=STATEMENT_YEAR):
    out, seen = [], set()
    for path in sorted(glob.glob(os.path.join(pdf_dir, "*.pdf"))):
        for ref, tdate, _post, details, amount, cad in ROW_RE.findall(extract_text(path)):
            if not any(x in details.upper() for x in EXCLUDE):
                continue
            mon, day = tdate.split()
            d = date(year, MONTHS[mon], int(day)).isoformat()
            amt = round(float((cad or amount).replace(",", "")), 2)
            if (d, amt) in seen:                 # dedupe overlapping statement periods
                continue
            seen.add((d, amt))
            out.append({"date": d, "amount": amt, "account": "Scotiabank Visa"})
    return out


def _tangerine_cc_payments(path, account="Tangerine Mastercard"):
    out = []
    for cells in _md_rows(path):
        if len(cells) >= 5 and _md_date(cells[0]) and cells[4] == "Payment/Credit":
            out.append({"date": _md_date(cells[0]),
                        "amount": round(abs(_md_money(cells[3])[0]), 2), "account": account})
    return out


def _amex_payments(path, account="Amex"):
    out = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            try:
                cr = float(row.get("Credits $") or 0)
            except ValueError:
                cr = 0
            if cr > 0:
                d, m, y = row["Date"].split("/")
                out.append({"date": f"{y}-{int(m):02d}-{int(d):02d}",
                            "amount": round(cr, 2), "account": account})
    return out


def _bmo_payments(path, account="BMO Mastercard"):
    out = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            if (row.get("Direction") or "").strip().lower() != "in":
                continue
            try:
                amt = abs(float(row.get("AbsAmount") or row.get("Amount") or 0))
            except ValueError:
                continue
            if amt > 0:
                out.append({"date": row["Date"].strip(), "amount": round(amt, 2),
                            "account": account})
    return out


def load_all(scotia_dir=DEFAULT_PDF_DIR, tangerine_dir=TANGERINE_DIR,
             amex_dir=AMEX_DIR, bmo_dir=BMO_DIR, rules=None):
    """Unified multi-account load → {cards, chequing, statements, accounts, payments}."""
    cards, statements = parse_dir(scotia_dir, rules)
    for r in cards:
        r.setdefault("account", "Scotiabank Visa")
        r["account_type"] = "card"
    cc = os.path.join(tangerine_dir, "Credit Card Account Details _ Tangerine (normalized).md")
    chq = os.path.join(tangerine_dir, "Chequing Account Details _ Tangerine (normalized).md")
    if os.path.exists(cc):
        cards += parse_tangerine_cc(cc, rules)
    chequing = parse_tangerine_chq(chq) if os.path.exists(chq) else []
    # CSV-based cards (Amex, BMO) — dedupe on (account, ref)
    seen = {(r["account"], r["ref"]) for r in cards}
    csv_sources = [(amex_dir, parse_amex_csv), (bmo_dir, parse_bmo_csv)]
    for d, parser in csv_sources:
        for f in sorted(glob.glob(os.path.join(d, "*.csv"))):
            for r in parser(f, rules):
                key = (r["account"], r["ref"])
                if key in seen:
                    continue
                seen.add(key)
                cards.append(r)
    cards.sort(key=lambda r: (r["date"], r["merchant"]))
    accounts = sorted({r["account"] for r in cards})
    # Payments/credits across all cards (the money paid toward the cards)
    payments = _scotia_payments(scotia_dir)
    if os.path.exists(cc):
        payments += _tangerine_cc_payments(cc)
    for f in sorted(glob.glob(os.path.join(amex_dir, "*.csv"))):
        payments += _amex_payments(f)
    for f in sorted(glob.glob(os.path.join(bmo_dir, "*.csv"))):
        payments += _bmo_payments(f)
    payments.sort(key=lambda p: p["date"])
    return {"cards": cards, "chequing": chequing, "statements": statements,
            "accounts": accounts, "payments": payments}


# --- Analytics (mirror of the dashboard JS, served by the API) --------------
def _median(a):
    if not a:
        return 0.0
    s = sorted(a)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


CADENCES = [("Weekly", 7, 2.5, 52), ("Biweekly", 14, 3, 26),
            ("Monthly", 30.44, 6, 12), ("Quarterly", 91, 12, 4), ("Yearly", 365, 30, 1)]
NON_RECURRING_CATS = {"Fees & Interest", "Food & Dining", "Groceries"}
# Auto-detection only trusts the "Subscriptions" category and monthly+ cadences — repeated
# transit/parking/shopping at weekly/biweekly intervals are coincidence, not subscriptions.
SUBSCRIPTION_CATS = {"Subscriptions"}
SUBSCRIPTION_CADENCES = {"Monthly", "Quarterly", "Yearly"}


def detect_recurring(txns):
    """Detect subscriptions by merchant + cadence + amount stability (Subscriptions category,
    monthly-or-longer only — keeps precision high; everything else is added manually)."""
    by_m = defaultdict(list)
    for r in txns:
        by_m[r["merchant"]].append(r)
    out = []
    for merchant, group in by_m.items():
        if len(group) < 2 or group[0]["category"] not in SUBSCRIPTION_CATS:
            continue
        ds = sorted(date.fromisoformat(r["date"]).toordinal() for r in group)
        gaps = [ds[i] - ds[i - 1] for i in range(1, len(ds))]
        med_gap = _median(gaps)
        amts = [r["amount"] for r in group]
        avg = sum(amts) / len(amts)
        cv = (sum((a - avg) ** 2 for a in amts) / len(amts)) ** 0.5 / avg if avg else 1
        cad = next((c for c in CADENCES if abs(med_gap - c[1]) <= c[2]), None)
        if not cad or cad[0] not in SUBSCRIPTION_CADENCES:
            continue
        if not (cv < 0.20 or (len(group) >= 3 and cv < 0.30)):
            continue
        gap_cv = ((sum((g - med_gap) ** 2 for g in gaps) / len(gaps)) ** 0.5 / med_gap
                  if med_gap else 1)
        score = min(3, len(group)) + (2 if cv < 0.05 else 1 if cv < 0.15 else 0) + \
                (2 if gap_cv < 0.15 else 1 if gap_cv < 0.35 else 0)
        conf = "high" if score >= 6 else "med" if score >= 4 else "low"
        last = date.fromordinal(ds[-1])
        out.append({
            "merchant": merchant, "category": group[0]["category"],
            "cadence": cad[0], "count": len(group), "avg": round(avg, 2),
            "last_seen": last.isoformat(),
            "next_date": (last + timedelta(days=round(med_gap))).isoformat(),
            "annual": round(avg * cad[3], 2), "monthly": round(avg * cad[3] / 12, 2),
            "confidence": conf,
        })
    out.sort(key=lambda r: -r["annual"])
    return out


def detect_anomalies(txns, limit=5):
    """Flag transactions far above their category's normal (robust MAD z-score)."""
    by_cat = defaultdict(list)
    for r in txns:
        by_cat[r["category"]].append(r)
    anoms = []
    for group in by_cat.values():
        if len(group) < 3:
            continue
        amts = [r["amount"] for r in group]
        med = _median(amts)
        mad = _median([abs(a - med) for a in amts]) or 0
        for r in group:
            z = (r["amount"] - med) / (1.4826 * mad) if mad else 0
            if r["amount"] >= 40 and (r["amount"] > med * 3 or z > 3.5):
                anoms.append({**r, "typical": round(med, 2),
                              "times": round(r["amount"] / med, 1) if med else None})
    anoms.sort(key=lambda r: -r["amount"])
    # one per merchant
    seen, uniq = set(), []
    for a in anoms:
        if a["merchant"] in seen:
            continue
        seen.add(a["merchant"])
        uniq.append(a)
    return uniq[:limit]


def forecast(txns, months_ahead=3):
    """Project future monthly spend: recurring scheduled forward + variable run-rate."""
    months = sorted({r["date"][:7] for r in txns})
    if not months:
        return {"history": [], "projection": [], "monthly_projection": 0.0}
    actual = {m: round(sum(r["amount"] for r in txns if r["date"][:7] == m), 2) for m in months}
    rec = detect_recurring(txns)
    recur_monthly = sum(r["monthly"] for r in rec)
    recur_merchants = {r["merchant"] for r in rec}
    var_by_month = [sum(r["amount"] for r in txns
                        if r["date"][:7] == m and r["merchant"] not in recur_merchants)
                    for m in months]
    var_avg = sum(var_by_month) / len(var_by_month) if var_by_month else 0
    projected = round(recur_monthly + var_avg, 2)
    ly, lm = map(int, months[-1].split("-"))
    proj = []
    for i in range(1, months_ahead + 1):
        y, m = ly + (lm - 1 + i) // 12, (lm - 1 + i) % 12 + 1
        proj.append({"month": f"{y}-{m:02d}", "projected": projected})
    return {
        "history": [{"month": m, "actual": actual[m]} for m in months],
        "projection": proj, "monthly_projection": projected,
    }


def summary(txns):
    total = round(sum(r["amount"] for r in txns), 2)
    by_cat = defaultdict(float)
    for r in txns:
        by_cat[r["category"]] += r["amount"]
    dates = [r["date"] for r in txns]
    return {
        "total": total, "count": len(txns),
        "date_range": [min(dates), max(dates)] if dates else [None, None],
        "by_category": {k: round(v, 2) for k, v in
                        sorted(by_cat.items(), key=lambda kv: -kv[1])},
    }
