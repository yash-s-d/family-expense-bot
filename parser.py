"""
Parses a free-text WhatsApp-style message into one or more structured
expense entries.

Two modes:
  - GeminiParser: calls the real Gemini API (2.5 Flash-Lite). Needs
    GEMINI_API_KEY set as an environment variable on your own machine —
    never pass this through chat.
  - MockParser: rule-based stand-in, used in this sandbox session so we can
    test the full pipeline without any real credentials.

Both return the same shape, so main.py can swap between them with one line.
"""
import os
import re
import json
from config import CATEGORIES, entry_type


PARSE_PROMPT_TEMPLATE = """You are parsing a short WhatsApp message from a family member logging an expense (or occasionally income/investment) into a household finance tracker.

Categories you MUST choose from (exact spelling):
{categories}

Rules:
- If the message mentions eggs together with vegetables/fruits (e.g. "eggs and tomato"), classify as "Fruits & Vegetables".
- If the message mentions eggs together with groceries/staples like bread, milk, kirana (e.g. "eggs and bread"), classify as "Groceries".
- If the message describes ONE shopping trip with multiple small items and ONE total amount (e.g. "700 vegetables paneer milk etc"), return ONE entry — keep the item list in "description", do not split it.
- If the message clearly describes MULTIPLE SEPARATE transactions with DIFFERENT amounts (e.g. "groceries 400 and auto 100"), return MULTIPLE entries, one per amount.
- If you cannot confidently match a category, use "Miscellaneous / Other".
- Amount formats to handle: "100/-", "Rs 100", "100rs", "₹100", plain "100".
- Return ONLY valid JSON, no markdown, no commentary, in this exact shape:

{{"entries": [{{"amount": <number>, "category": "<one of the categories above>", "description": "<short description>"}}]}}

If no valid amount can be found at all, return {{"entries": []}}.

Message: "{message}"
"""


class QuotaExceededError(Exception):
    pass


class ModelUnavailableError(Exception):
    """Raised when Gemini rejects the configured model name — usually means
    Google retired/renamed it. See the exception message for what to do."""
    pass


class GeminiParser:
    """Real parser — only usable on your own machine with GEMINI_API_KEY set.

    Uses the current `google-genai` SDK (the old `google-generativeai`
    package is deprecated / no longer receiving updates as of mid-2026).
    Model: gemini-3.1-flash-lite — the current cost-efficient, high-volume
    model, replacing the retired gemini-2.5-flash-lite for new API keys.
    """

    MODEL_NAME = "gemini-3.1-flash-lite"

    def __init__(self):
        from google import genai
        api_key = os.environ["GEMINI_API_KEY"]  # set this locally, never in chat
        self.client = genai.Client(api_key=api_key)

    def parse(self, message: str) -> list[dict]:
        prompt = PARSE_PROMPT_TEMPLATE.format(categories=", ".join(CATEGORIES), message=message)
        try:
            response = self.client.models.generate_content(
                model=self.MODEL_NAME,
                contents=prompt,
            )
        except Exception as e:
            error_text = str(e)
            if "429" in error_text or "RESOURCE_EXHAUSTED" in error_text or "quota" in error_text.lower():
                raise QuotaExceededError from e
            if "404" in error_text or "not found" in error_text.lower() or "no longer available" in error_text.lower():
                raise ModelUnavailableError(
                    f"The model '{self.MODEL_NAME}' seems to have been retired or renamed by Google. "
                    f"Check https://ai.google.dev/gemini-api/docs/deprecations for the current "
                    f"recommended model, then update MODEL_NAME in parser.py.\n\nOriginal error: {error_text}"
                ) from e
            raise
        text = re.sub(r"^```(json)?|```$", "", response.text.strip(), flags=re.MULTILINE).strip()
        try:
            return json.loads(text).get("entries", [])
        except json.JSONDecodeError:
            return []


class MockParser:
    """Rule-based stand-in mirroring the same rules given to Gemini above.
    Used only for local testing in this sandbox — no API key needed."""

    RULES = [
        (r"medical|hospital|doctor|pharmacy|clinic", "Medical & Healthcare"),
        (r"electricity|gas bill", "Housing & Utilities"),
        (r"haircut|clothes|dress|shopping", "Clothing & Personal Care"),
        (r"movie|zomato|swiggy|dining|lunch out|bhaji pav|pani puri", "Entertainment / Dining Out"),
        (r"book|pencil|pen|course|college fee|exam fee", "Education & Courses"),
        (r"\bgift", "Gifts & Occasions"),
        (r"chaitali|rinku|watchman", "Household Services"),
        (r"jio|airtel|wifi|spotify|phone bill", "Telecom & Internet"),
        (r"uber|train|auto|rapido|bus|airplane|ola", "Transportation"),
        (r"petrol|fastag|scooty", "Petrol + Fastag"),
        (r"\bemi\b", "Loan EMI / Installment"),
        (r"sip|silver|gold|\bfd\b|\brd\b|insurance|\blic\b|mutual fund", "Investments / SIP"),
        (r"chicken|fish|mutton", "Non-Veg / Protein"),
        (r"rent received|rental|satara rent|shop rent", "Rental Income"),
    ]

    def parse(self, message: str) -> list[dict]:
        segments = re.split(r"\band\b|,(?!\d)", message, flags=re.IGNORECASE)
        segments = [s.strip() for s in segments if s.strip()]
        if not (len(segments) > 1 and all(re.search(r"\d", s) for s in segments)):
            segments = [message]

        entries = []
        for seg in segments:
            amount_match = re.search(r"(\d+(?:\.\d{1,2})?)", seg)
            if not amount_match:
                continue
            amount = float(amount_match.group(1))
            desc = re.sub(r"(\d+(?:\.\d{1,2})?)\s*/?-?", "", seg)
            desc = re.sub(r"\b(paid|for|rs|rupees|received)\b", "", desc, flags=re.IGNORECASE).strip()
            desc = re.sub(r"\s+", " ", desc) or "Unspecified"
            entries.append({"amount": amount, "category": self._classify(seg), "description": desc})
        return entries

    def _classify(self, text: str) -> str:
        for pattern, cat in self.RULES:
            if re.search(pattern, text, re.IGNORECASE):
                return cat
        has_veg = re.search(r"vegetable|paneer|tomato|onion|potato|sabzi|fruit", text, re.IGNORECASE)
        has_grocery = re.search(r"groceries|grocery|milk|dmart|reliance mart|kirana|aata|flowers|bread|eggs", text, re.IGNORECASE)
        if has_veg:
            return "Fruits & Vegetables"
        if has_grocery:
            return "Groceries"
        return "Miscellaneous / Other"