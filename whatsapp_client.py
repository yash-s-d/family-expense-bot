"""
Thin wrapper around Meta's WhatsApp Cloud API for sending replies.

Reads credentials from environment variables (set via .env):
  WHATSAPP_ACCESS_TOKEN   - the token you generated in Meta's dashboard
  WHATSAPP_PHONE_NUMBER_ID - your test (or later, real) number's Phone Number ID

Docs: https://developers.facebook.com/docs/whatsapp/cloud-api/reference/messages
"""
import os
import requests

GRAPH_API_VERSION = "v25.0"  # matches what Meta's dashboard showed in your test cURL command


def send_whatsapp_message(to: str, text: str) -> dict:
    """Sends a plain text WhatsApp message. `to` is the recipient's number
    in international format, no leading '+' (e.g. '919876543210')."""
    access_token = os.environ["WHATSAPP_ACCESS_TOKEN"]
    phone_number_id = os.environ["WHATSAPP_PHONE_NUMBER_ID"]

    url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text},
    }
    response = requests.post(url, headers=headers, json=payload, timeout=10)
    if response.status_code != 200:
        print(f"WhatsApp send failed ({response.status_code}): {response.text}")
    return response.json()