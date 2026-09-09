"""
Generates the monthly summary message, e.g.:

    📊 *July Summary*

    Total: ₹18,400

    Groceries: ₹6,200 (34%)
    Auto: ₹3,100 (17%)
    ...

    *By person:*
    Dad: ₹10,000
    Mom: ₹8,400

    Biggest change: Auto up 40% vs June

Works from whatever get_month_rows() returns (same shape from both
MockSheetClient and the real SheetsClient) — so this logic is identical
whether it's reading mock or real data.
"""
from datetime import datetime, timedelta
from config import entry_type, MONTH_NAMES


def compute_summary(rows: list[dict], previous_month_rows: list[dict] | None, month_label: str) -> str:
    """Only 'expense'-type rows count toward totals — income (Rental Income)
    and investments (Investments/SIP) are excluded per Tanmay's decision,
    so a disciplined SIP month doesn't look like an overspending month."""
    expense_rows = [r for r in rows if entry_type(r["category"]) == "expense"]
    total = sum(r["amount"] for r in expense_rows)

    by_category: dict[str, float] = {}
    by_person: dict[str, float] = {}
    for r in expense_rows:
        by_category[r["category"]] = by_category.get(r["category"], 0) + r["amount"]
        by_person[r["paid_by"]] = by_person.get(r["paid_by"], 0) + r["amount"]

    prev_by_category: dict[str, float] = {}
    if previous_month_rows:
        for r in previous_month_rows:
            if entry_type(r["category"]) == "expense":
                prev_by_category[r["category"]] = prev_by_category.get(r["category"], 0) + r["amount"]

    lines = [f"📊 *{month_label} Summary*", "", f"Total: ₹{total:,.0f}", ""]

    for cat, amt in sorted(by_category.items(), key=lambda x: -x[1]):
        pct = (amt / total * 100) if total else 0
        lines.append(f"{cat}: ₹{amt:,.0f} ({pct:.0f}%)")

    if by_person:
        lines.append("")
        lines.append("*By person:*")
        for person, amt in sorted(by_person.items(), key=lambda x: -x[1]):
            lines.append(f"{person}: ₹{amt:,.0f}")

    biggest_change_cat = None
    biggest_change_pct = 0.0
    for cat, amt in by_category.items():
        prev_amt = prev_by_category.get(cat, 0)
        if prev_amt > 0:
            change_pct = (amt - prev_amt) / prev_amt * 100
        elif amt > 0:
            change_pct = 100.0
        else:
            continue
        if abs(change_pct) > abs(biggest_change_pct):
            biggest_change_pct = change_pct
            biggest_change_cat = cat

    if biggest_change_cat:
        direction = "up" if biggest_change_pct > 0 else "down"
        lines.append("")
        lines.append(f"Biggest change: {biggest_change_cat} {direction} {abs(biggest_change_pct):.0f}% vs last month")

    return "\n".join(lines)


def is_last_day_of_month(date: datetime) -> bool:
    """Use this instead of hardcoding day==30 — handles Feb, 30-day, and
    31-day months correctly."""
    tomorrow = date + timedelta(days=1)
    return tomorrow.day == 1


def previous_month_abbr(current_month_abbr: str) -> str:
    idx = MONTH_NAMES.index(current_month_abbr)
    return MONTH_NAMES[idx - 1]  # -1 wraps Jan -> Dec correctly