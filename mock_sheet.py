"""
A local, in-memory stand-in for the real Google Sheet.
Mimics the exact tab/column structure of Tanmay's real workbook so that
switching to the real `sheets_client.py` later requires no logic changes
elsewhere in the codebase — only swapping which "client" object gets used.
"""
from collections import defaultdict
from config import month_tab_name, FIRST_DATA_ROW


class MockSheetClient:
    """
    Structure: self.tabs["📋 Jul Expenses"] = list of row dicts, e.g.
        {"date": "10-Jul-2026", "description": "haircut", "category": "...",
         "amount": 100.0, "paid_by": "Tanmay", "comment": ""}
    """

    def __init__(self):
        self.tabs = defaultdict(list)

    def append_row(self, month_abbr: str, date: str, description: str,
                   category: str, amount: float, paid_by: str, comment: str = ""):
        tab = month_tab_name(month_abbr)
        row_number = FIRST_DATA_ROW + len(self.tabs[tab])
        self.tabs[tab].append({
            "date": date,
            "description": description,
            "category": category,
            "amount": amount,
            "paid_by": paid_by,
            "comment": comment,
        })
        return row_number

    def get_month_rows(self, month_abbr: str):
        return list(self.tabs[month_tab_name(month_abbr)])  # each row already has 'category', 'amount' keys

    def pretty_print(self, month_abbr: str):
        tab = month_tab_name(month_abbr)
        rows = self.tabs[tab]
        if not rows:
            print(f"[{tab}] — no entries yet")
            return
        print(f"\n[{tab}]")
        print(f"{'#':<3} {'Date':<12} {'Description':<28} {'Category':<26} {'Amount':>10} {'Paid By':<8}")
        for i, r in enumerate(rows, 1):
            print(f"{i:<3} {r['date']:<12} {r['description'][:27]:<28} {r['category']:<26} "
                  f"₹{r['amount']:>8,.0f} {r['paid_by']:<8}")
