"""
Real Google Sheets client. Not used in this sandbox session (no live credentials
were ever passed through chat) — this is the file Tanmay runs on his own machine
once he has:
  1. GOOGLE_SERVICE_ACCOUNT_JSON_PATH env var pointing at his own downloaded key file
  2. GOOGLE_SHEET_ID env var with his real spreadsheet's ID (from its URL)

Usage mirrors MockSheetClient exactly (same method names/signatures), so
main.py can swap between them with a single line change.
"""
import os
import gspread
from google.oauth2.service_account import Credentials
from config import month_tab_name, FIRST_DATA_ROW, COL_DATE, COL_DESCRIPTION, COL_CATEGORY, COL_AMOUNT, COL_PAID_BY, COL_COMMENT

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


class SheetsQuotaExceededError(Exception):
    """Raised when Google Sheets API rejects a request for exceeding its
    per-minute quota. Distinct from Gemini's QuotaExceededError."""
    pass


class SheetsClient:
    def __init__(self):
        key_path = os.environ["GOOGLE_SERVICE_ACCOUNT_JSON_PATH"]  # set this locally, never in chat
        sheet_id = os.environ["GOOGLE_SHEET_ID"]
        creds = Credentials.from_service_account_file(key_path, scopes=SCOPES)
        gc = gspread.authorize(creds)
        self.spreadsheet = gc.open_by_key(sheet_id)

    def _first_blank_row(self, worksheet):
        # Column D (Description) is a reliable "is this row used" signal
        col_values = worksheet.col_values(ord(COL_DESCRIPTION) - ord("A") + 1)
        return max(FIRST_DATA_ROW, len(col_values) + 1)

    def append_row(self, month_abbr: str, date: str, description: str,
                   category: str, amount: float, paid_by: str, comment: str = ""):
        tab_name = month_tab_name(month_abbr)
        worksheet = self.spreadsheet.worksheet(tab_name)
        row_number = self._first_blank_row(worksheet)
        # Single batched write instead of 6 separate update_acell calls —
        # writes C{row}:H{row} (Date through Comment) in one API request.
        row_values = [date, description, category, amount, paid_by, comment]
        try:
            worksheet.update(
                f"{COL_DATE}{row_number}:{COL_COMMENT}{row_number}",
                [row_values],
            )
        except gspread.exceptions.APIError as e:
            if "429" in str(e) or "Quota exceeded" in str(e):
                raise SheetsQuotaExceededError from e
            raise
        return row_number

    def get_month_rows(self, month_abbr: str):
        tab_name = month_tab_name(month_abbr)
        worksheet = self.spreadsheet.worksheet(tab_name)
        # Single batched read of the whole data range instead of up to 6
        # separate acell() calls per row — this is what was blowing through
        # the Sheets API's per-minute read quota on large sheets.
        try:
            all_rows = worksheet.get(
                f"{COL_DATE}{FIRST_DATA_ROW}:{COL_COMMENT}1000",
                value_render_option="UNFORMATTED_VALUE",
            )
        except gspread.exceptions.APIError as e:
            if "429" in str(e) or "Quota exceeded" in str(e):
                raise SheetsQuotaExceededError from e
            raise

        records = []
        for row in all_rows:
            # Pad short rows so index access below never raises IndexError
            row = row + [""] * (6 - len(row))
            date, description, category, amount, paid_by, comment = row[:6]
            if not description:
                continue
            records.append({
                "date": date,
                "description": description,
                "category": category,
                "amount": float(amount or 0),
                "paid_by": paid_by,
                "comment": comment,
            })
        return records