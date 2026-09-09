"""
Shared configuration: category list, people list, and sheet column layout.
This mirrors the real "Final - Family Finance Tracker 2026" Google Sheet exactly,
so the bot writes into the same structure Tanmay already uses.
"""

# Exact categories from the real sheet's dropdown + Tanmay's master list.
# Order matters only for readability; matching is case-insensitive.
CATEGORIES = [
    "Medical & Healthcare",
    "Housing & Utilities",
    "Groceries",
    "Fruits & Vegetables",
    "Petrol + Fastag",
    "Loan EMI / Installment",
    "Non-Veg / Protein",
    "Clothing & Personal Care",
    "Entertainment / Dining Out",
    "Education & Courses",
    "Investments / SIP",
    "Gifts & Occasions",
    "Household Services",
    "Telecom & Internet",
    "Transportation",
    "Rental Income",
    "Additional Income",
    "Miscellaneous / Other",  # bot fallback bucket ("Others" in Tanmay's sheet)
]

# type mapping — decides how an entry affects totals (expense vs not)
CATEGORY_TYPE = {
    "Rental Income": "income",
    "Additional Income": "income",
    "Investments / SIP": "investment",
}
DEFAULT_TYPE = "expense"

def entry_type(category: str) -> str:
    return CATEGORY_TYPE.get(category, DEFAULT_TYPE)

# Family members — matches the "Paid By" dropdown in the real sheet
# Family members — matches the "Paid By" dropdown in the real sheet
PEOPLE = ["Tanmay", "Mom", "Dad", "Akshat"]

def normalize_person(name: str) -> str:
    """Maps any casing/whitespace variant (e.g. 'akshat', ' MOM ') to the
    exact capitalization the sheet's dropdown validation requires. Falls
    back to the original (title-cased) input if it's not a recognized
    family member, so an unexpected sender doesn't silently disappear."""
    cleaned = name.strip()
    for person in PEOPLE:
        if cleaned.lower() == person.lower():
            return person
    return cleaned.title() or "Unknown"

# Real sheet column layout (📋 <Month> Expenses tabs), 1-indexed to match Sheets API
# Column A is blank/unused, B is auto-numbering formula (never write here)
COL_DATE = "C"
COL_DESCRIPTION = "D"
COL_CATEGORY = "E"
COL_AMOUNT = "F"
COL_PAID_BY = "G"
COL_COMMENT = "H"

HEADER_ROW = 6
FIRST_DATA_ROW = 8

MONTH_TAB_PREFIX = "📋 "
MONTH_TAB_SUFFIX = " Expenses"

MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

MONTH_FULL_NAMES = {
    "Jan": "January", "Feb": "February", "Mar": "March", "Apr": "April",
    "May": "May", "Jun": "June", "Jul": "July", "Aug": "August",
    "Sep": "September", "Oct": "October", "Nov": "November", "Dec": "December",
}

def month_tab_name(month_abbr: str) -> str:
    return f"{MONTH_TAB_PREFIX}{month_abbr}{MONTH_TAB_SUFFIX}"

# Daily free-tier quota tracking (Gemini 2.5 Flash-Lite, per Google's published limits
# as of mid-2026). This is shared across the whole household's messages, not per-person.
GEMINI_MODEL = "gemini-2.5-flash-lite"
DAILY_QUOTA = 1000
QUOTA_RESET_MESSAGE_IST = (
    "Hit today's free message limit for the bot. "
    "It resets around 1:30 PM IST (midnight Pacific Time) — try again after that."
)
