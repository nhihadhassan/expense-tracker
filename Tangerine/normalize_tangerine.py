#!/usr/bin/env python3
"""Normalize MarkItDown-converted Tangerine statements into clean transaction tables.

Handles the two fragmented layouts MarkItDown produces:
  - Credit card: Date | Description | Card(***8125) | Amount, with a trailing cash-back line.
  - Chequing:    Date | Description | Amount | Balance (deposits prefixed with '+').
"""
import re
import sys

DATE_RE = re.compile(r'^([A-Z][a-z]{2} \d{1,2}, \d{4})\b')
# optional '+' (credit) prefix, then a dollar value; sign captured separately
MONEY_RE = re.compile(r'(\+\s*)?(-?)\$([\d,]+\.\d{2})')
CARD_RE = re.compile(r'\*{2,}(\d{4})')
ONLY_MONEY_RE = re.compile(r'^(\+\s*)?(-?)\$[\d,]+\.\d{2}$')
ONLY_CARD_RE = re.compile(r'^\*{2,}\d{4}$')


def strip_pipes(line):
    """Turn a markdown table row into plain spaced text; drop separator rows."""
    s = line.strip()
    if s.startswith('|'):
        cells = [c.strip() for c in s.strip('|').split('|')]
        if all(set(c) <= set('-') and c for c in cells if c):  # separator row
            return None
        return ' '.join(c for c in cells if c)
    return s


def money(sign_plus, neg, num):
    val = float(num.replace(',', ''))
    return -val if neg else val


def parse(lines, kind):
    records = []
    cur = None
    for raw in lines:
        line = strip_pipes(raw)
        if not line:
            continue
        m = DATE_RE.match(line)
        if m:
            date = m.group(1)
            rest = line[m.end():]
            card = ''
            cm = CARD_RE.search(rest)
            if cm:
                card = '***' + cm.group(1)
                rest = rest[:cm.start()] + rest[cm.end():]
            monies = list(MONEY_RE.finditer(rest))
            if not monies:
                continue
            first = monies[0]
            desc = rest[:first.start()].strip().rstrip('.').strip()
            desc = re.sub(r'\s+', ' ', desc).rstrip('…').strip()
            amount = money(*monies[0].groups())
            credit = bool(monies[0].group(1))  # had a '+' prefix
            balance = money(*monies[1].groups()) if len(monies) > 1 else None
            cur = {'date': date, 'desc': desc, 'card': card,
                   'amount': amount, 'credit': credit,
                   'balance': balance, 'cashback': None}
            records.append(cur)
        elif cur is not None and ONLY_CARD_RE.match(line):
            if not cur['card']:
                cur['card'] = '***' + line[-4:]
        elif cur is not None and ONLY_MONEY_RE.match(line):
            # standalone money line = cash-back (credit card only)
            if kind == 'cc' and cur['cashback'] is None:
                g = MONEY_RE.search(line)
                cur['cashback'] = money(*g.groups())
    return records


def fmt(v, signed=False):
    if v is None:
        return ''
    s = f"${abs(v):,.2f}"
    if v < 0:
        return f"-{s}"
    return f"+{s}" if signed and v > 0 else s


def render_cc(records):
    out = ["| Date | Description | Card | Amount | Type | Cash-Back |",
           "| --- | --- | --- | ---: | --- | ---: |"]
    debit = credit_t = cashback = 0.0
    for r in records:
        typ = "Payment/Credit" if r['credit'] else "Purchase"
        if r['credit']:
            credit_t += r['amount']
        else:
            debit += r['amount']
        if r['cashback']:
            cashback += r['cashback']
        amt = ("+" if r['credit'] else "") + f"${r['amount']:,.2f}"
        cb = fmt(r['cashback'])
        out.append(f"| {r['date']} | {r['desc']} | {r['card']} | {amt} | {typ} | {cb} |")
    out += ["",
            f"**Transactions:** {len(records)}  ",
            f"**Total purchases:** ${debit:,.2f}  ",
            f"**Total payments/credits:** ${credit_t:,.2f}  ",
            f"**Total cash-back earned:** ${cashback:,.2f}"]
    return "\n".join(out)


def render_chq(records):
    out = ["| Date | Description | Amount | Type | Balance |",
           "| --- | --- | ---: | --- | ---: |"]
    deb = cred = 0.0
    for r in records:
        typ = "Deposit" if r['credit'] else "Withdrawal"
        if r['credit']:
            cred += r['amount']
        else:
            deb += r['amount']
        amt = ("+" if r['credit'] else "-") + f"${r['amount']:,.2f}"
        out.append(f"| {r['date']} | {r['desc']} | {amt} | {typ} | {fmt(r['balance'])} |")
    out += ["",
            f"**Transactions:** {len(records)}  ",
            f"**Total deposits:** ${cred:,.2f}  ",
            f"**Total withdrawals:** ${deb:,.2f}"]
    return "\n".join(out)


def main():
    src, kind, title = sys.argv[1], sys.argv[2], sys.argv[3]
    with open(src) as f:
        lines = f.read().splitlines()
    recs = parse(lines, kind)
    body = render_cc(recs) if kind == 'cc' else render_chq(recs)
    out = f"# {title}\n\n{body}\n"
    dst = src.rsplit('.md', 1)[0] + ' (normalized).md'
    with open(dst, 'w') as f:
        f.write(out)
    print(f"{dst}\n  parsed {len(recs)} transactions")


if __name__ == '__main__':
    main()
