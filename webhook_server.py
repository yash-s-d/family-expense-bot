"""
Webhook server for the WhatsApp Cloud API.

This is what turns your bot from "type into a terminal" into "actually
receives real WhatsApp messages." Meta calls this server's /webhook endpoint
whenever a message arrives; this server calls handle_message() (same logic
already tested via the terminal) and sends the reply back via the Cloud API.

Run locally + expose via ngrok for testing:
  1. python webhook_server.py          (starts listening on port 5000)
  2. ngrok http 5000                   (in a separate terminal — gives you a
                                         public URL like https://xxxx.ngrok-free.app)
  3. In Meta's dashboard (WhatsApp > Configuration > Webhook), set:
       Callback URL:  https://xxxx.ngrok-free.app/webhook
       Verify token:  whatever you set as WHATSAPP_VERIFY_TOKEN below
     Subscribe to the "messages" field.

Needs these env vars (add to your .env):
  WHATSAPP_ACCESS_TOKEN     - from Meta's dashboard, Step 1
  WHATSAPP_PHONE_NUMBER_ID  - from Meta's dashboard, Step 1
  WHATSAPP_VERIFY_TOKEN     - any string YOU make up, used only to prove to
                              Meta that webhook calls are hitting your server
                              correctly during setup. Not a secret from Meta's
                              side, but keep it out of chat/commits anyway.
"""
import os
from flask import Flask, request, jsonify
from dotenv import load_dotenv

load_dotenv()

from main import handle_message
from config import normalize_person
from whatsapp_client import send_whatsapp_message

app = Flask(__name__)

VERIFY_TOKEN = os.environ.get("WHATSAPP_VERIFY_TOKEN", "")

# Maps the sender's WhatsApp phone number to a family member name.
# Fill this in with your real family numbers (international format, no '+').
# Example: "919876543210": "Tanmay"
PHONE_TO_PERSON = {
    "919082500861": "Tanmay",
    "919930009096": "Mom",
    "919082342073": "Dad",
    "918828523417": "Akshat",
}


@app.route("/webhook", methods=["GET"])
def verify_webhook():
    """Meta calls this once, during setup, to confirm you control this URL."""
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    print(f"DEBUG: received token = '{token}'")
    print(f"DEBUG: expected VERIFY_TOKEN = '{VERIFY_TOKEN}'")
    print(f"DEBUG: match = {token == VERIFY_TOKEN}")
    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200
    return "Verification failed", 403


@app.route("/webhook", methods=["POST"])
def receive_message():
    """Meta calls this every time a message arrives."""
    data = request.get_json(silent=True) or {}
    try:
        entry = data["entry"][0]
        change = entry["changes"][0]
        value = change["value"]
        messages = value.get("messages")
        if not messages:
            return jsonify(status="ignored"), 200

        msg = messages[0]
        sender_number = msg["from"]
        text = msg.get("text", {}).get("body", "")

        if not text:
            return jsonify(status="ignored - non-text message"), 200

        person = PHONE_TO_PERSON.get(sender_number)
        if not person:
            send_whatsapp_message(
                sender_number,
                "This number isn't registered as a family member yet. "
                "Ask Tanmay to add it to PHONE_TO_PERSON in webhook_server.py.",
            )
            return jsonify(status="unregistered sender"), 200

        reply = handle_message(text, normalize_person(person))
        send_whatsapp_message(sender_number, reply)
        return jsonify(status="ok"), 200

    except (KeyError, IndexError) as e:
        print(f"Webhook payload didn't match expected shape: {e}\nFull payload: {data}")
        return jsonify(status="ignored - unexpected payload"), 200


if __name__ == "__main__":
    print("Webhook server starting on http://localhost:5000/webhook")
    print("Run 'ngrok http 5000' in another terminal to get a public URL.\n")
    app.run(port=5000, debug=True)
