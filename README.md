# Family Expense Bot

A WhatsApp bot that lets family members log expenses (and income) by just
texting a message like `"250 auto"` or `"eggs and bread 180"` — no app, no
manual spreadsheet entry. An AI model reads the message, figures out the
amount and category, and writes a row into a shared Google Sheet.

## How it works (the flow)

```
Family member sends WhatsApp message
        ↓
Meta's WhatsApp Cloud API forwards it to our webhook
        ↓
Flask server (webhook_server.py) receives it
        ↓
Gemini API (parser.py) reads the free-text message and returns
structured JSON: {amount, category, description}
        ↓
gspread (sheets_client.py) writes that as a new row into the
correct month's tab in the Google Sheet
        ↓
Bot replies on WhatsApp confirming what was logged
```

Special case: if you text `"summary"`, it skips the parser and instead
reads the current month's rows back from the Sheet and replies with
totals (`summary.py`).

## Tech stack

| Piece | Tool |
|---|---|
| Message parsing / categorization | Google Gemini API |
| Data storage | Google Sheets (via a service account, not OAuth login) |
| Messaging | WhatsApp Cloud API (Meta) |
| Server | Flask + Gunicorn + Nginx |
| Hosting | AWS EC2 (t3.micro is enough) |

## Repo structure

- `main.py` — orchestrates parser → sheet write, also has a local CLI test mode
- `webhook_server.py` — the Flask endpoint Meta actually calls
- `parser.py` — talks to Gemini, defines the categorization prompt
- `sheets_client.py` — talks to Google Sheets
- `whatsapp_client.py` — sends replies back via WhatsApp
- `config.py` — categories list, sheet column layout, people list (edit this to customize categories)
- `summary.py` — builds the "how much did we spend" reply

## Setup (for a friend forking this)

You'll need your **own** accounts and keys for all of these — nothing here
is shared with the original author.

1. **Google Gemini API key** — free tier available at [aistudio.google.com/apikey](https://aistudio.google.com/apikey)
2. **Google Sheet + service account** — create a sheet, then a service
   account in Google Cloud Console, download its JSON key, and share your
   Sheet with the service account's email (found inside the JSON)
3. **WhatsApp Cloud API access** — via a Meta Developer app (free tier
   allows a test number to start)
4. **A server** — any always-on machine works; this was built and tested
   on an AWS EC2 free-tier instance

Then:
```bash
git clone https://github.com/yash-s-d/family-expense-bot.git
cd family-expense-bot
cp .env.example .env
# edit .env and fill in YOUR real keys — never commit this file
pip install -r requirements.txt
python main.py   # local CLI test mode first, then deploy webhook_server.py for real
```

Customize `config.py` — the `CATEGORIES` list and `PEOPLE` list — to match
your own family/household setup before going live.

## Security note

`.env` and any `*.json` service-account key are git-ignored on purpose.
Never commit real API keys or tokens — generate your own and keep them
only in your local `.env`.
