"""
Orchestrates: incoming message -> parser -> sheet writer.
Also handles the quota-exceeded reply and the "summary" command.

To run against your REAL sheet + REAL Gemini, on your own machine:
  1. pip install google-generativeai gspread google-auth
  2. export GEMINI_API_KEY=your_real_key
  3. export GOOGLE_SERVICE_ACCOUNT_JSON_PATH=/full/path/to/your/key.json
  4. export GOOGLE_SHEET_ID=the_id_from_your_sheet_url
  5. Change USE_MOCK = False below
  6. python main.py
"""
from dotenv import load_dotenv
load_dotenv()
from datetime import datetime
from config import MONTH_NAMES, MONTH_FULL_NAMES, QUOTA_RESET_MESSAGE_IST, normalize_person
from parser import MockParser, QuotaExceededError, ModelUnavailableError
from sheets_client import SheetsQuotaExceededError
from mock_sheet import MockSheetClient
from summary import compute_summary, is_last_day_of_month, previous_month_abbr

USE_MOCK = False  # flip to False + set env vars to run against real services


if USE_MOCK:
    parser = MockParser()
    sheet = MockSheetClient()
else:
    from parser import GeminiParser
    from sheets_client import SheetsClient
    parser = GeminiParser()
    sheet = SheetsClient()


def current_month_abbr() -> str:
    return MONTH_NAMES[datetime.now().month - 1]


def handle_message(message: str, person: str) -> str:
    """Returns the bot's WhatsApp reply text."""
    text = message.strip().lower()
    if text in ("summary", "how much did we spend", "monthly summary", "how much this month"):
        return handle_summary_request()

    try:
        entries = parser.parse(message)
    except QuotaExceededError:
        return QUOTA_RESET_MESSAGE_IST
    except ModelUnavailableError as e:
        print(f"\n⚠️  {e}\n")  # full details in the terminal for you to act on
        return "Bot's temporarily down for a config update — try again in a bit."

    if not entries:
        return "Couldn't find an amount in that. Try including a number, e.g. '250 auto'."

    month_abbr = current_month_abbr()
    today_str = datetime.now().strftime("%d-%b-%Y")
    logged = []
    for e in entries:
        row_number = sheet.append_row(
            month_abbr=month_abbr,
            date=today_str,
            description=e["description"],
            category=e["category"],
            amount=e["amount"],
            paid_by=person,
        )
        logged.append((row_number, e))

    if len(logged) == 1:
        row_number, e = logged[0]
        return f"Logged ₹{e['amount']:,.0f} under {e['category']} (row {row_number})."
    return f"Split into {len(logged)} entries, logged separately."


def handle_summary_request() -> str:
    month_abbr = current_month_abbr()
    month_label = MONTH_FULL_NAMES[month_abbr]
    try:
        rows = sheet.get_month_rows(month_abbr)
        prev_rows = sheet.get_month_rows(previous_month_abbr(month_abbr))
    except SheetsQuotaExceededError:
        return "Google Sheets is briefly rate-limited — try the summary again in a minute."
    return compute_summary(rows, prev_rows, month_label)


def check_and_send_month_end_summary():
    """Call this once a day (e.g. via cron); it only actually sends on the
    last calendar day of the month, regardless of whether that's the 28th,
    30th, or 31st."""
    now = datetime.now()
    if is_last_day_of_month(now):
        return handle_summary_request()
    return None


if __name__ == "__main__":
    mode_label = "MOCK mode (fake parser + fake sheet)" if USE_MOCK else "REAL mode (Gemini + your real Google Sheet)"
    print(f"Family expense bot — {mode_label}\n")
    print("Type a message as if it were WhatsApp. Type 'quit' to exit.\n")
    while True:
        person = normalize_person(input("Who's sending? (Tanmay/Mom/Dad/Akshat): ").strip() or "Tanmay")
        message = input(f"{person}> ").strip()
        if message.lower() == "quit":
            break
        reply = handle_message(message, person)
        print(f"Bot: {reply}\n")
