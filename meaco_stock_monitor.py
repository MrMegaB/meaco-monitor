#!/usr/bin/env python3
"""
Meaco air-conditioner stock monitor.

Polls each product's Shopify .js endpoint, and emails you the moment a
product flips from out-of-stock to in-stock. Only alerts on the *transition*
so you don't get spammed every run.

Run it on a schedule (cron / GitHub Actions / AWS Lambda). See notes at bottom.

Email config is read from environment variables:
    SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, ALERT_TO
(For Gmail: SMTP_HOST=smtp.gmail.com, SMTP_PORT=587, SMTP_USER=you@gmail.com,
 SMTP_PASS=<a Google "App Password", not your normal password>.)
"""

import json
import os
import smtplib
import ssl
import sys
from email.message import EmailMessage
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

# --- products to watch (Shopify "handles") -------------------------------
HANDLES = [
    "meaco-cirro-12000-btu-super-quiet-smart-portable-air-conditioner",
    "meaco-cirro-12000-btu-super-quiet-smart-portable-air-conditioner-heater",
    "meaco-cirro-14000-btu-super-quiet-inverter-smart-portable-air-conditioner",
    "meaco-cirro-14000-btu-super-quiet-inverter-smart-portable-air-conditioner-heater",
    "meaco-cirro-16000-btu-super-quiet-inverter-smart-portable-air-conditioner",
    "meaco-cirro-16000-btu-super-quiet-inverter-smart-portable-air-conditioner-heater",
]

BASE_PRODUCT_URL = "https://www.meaco.com/products/{}"
STATE_FILE = os.environ.get("STATE_FILE", "meaco_stock_state.json")
USER_AGENT = "Mozilla/5.0 (stock-monitor; personal use)"
TIMEOUT = 20


def fetch_status(handle):
    """Return (available: bool, title: str) for a product handle."""
    url = BASE_PRODUCT_URL.format(handle) + ".js"
    req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urlopen(req, timeout=TIMEOUT) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    # Top-level "available" is true if ANY variant can be bought.
    available = bool(data.get("available"))
    title = data.get("title", handle)
    return available, title


def load_state():
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def send_email(newly_available):
    host = os.environ["SMTP_HOST"]
    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ["SMTP_USER"]
    password = os.environ["SMTP_PASS"]
    to_addr = os.environ.get("ALERT_TO", user)

    lines = ["These Meaco air conditioners just came back IN STOCK:\n"]
    for handle, title in newly_available:
        lines.append(f"- {title}\n  {BASE_PRODUCT_URL.format(handle)}\n")
    lines.append("\nGo buy quickly. (Sent by your stock monitor.)")
    body = "\n".join(lines)

    msg = EmailMessage()
    msg["Subject"] = f"IN STOCK: {len(newly_available)} Meaco air conditioner(s)"
    msg["From"] = user
    msg["To"] = to_addr
    msg.set_content(body)

    ctx = ssl.create_default_context()
    with smtplib.SMTP(host, port, timeout=TIMEOUT) as server:
        server.starttls(context=ctx)
        server.login(user, password)
        server.send_message(msg)


def main():
    state = load_state()
    newly_available = []

    for handle in HANDLES:
        try:
            available, title = fetch_status(handle)
        except (URLError, HTTPError, ValueError, KeyError) as e:
            print(f"[warn] {handle}: {e}", file=sys.stderr)
            continue

        was_available = state.get(handle, False)
        if available and not was_available:
            newly_available.append((handle, title))
        state[handle] = available
        print(f"{'IN STOCK ' if available else 'sold out '} {handle}")

    if newly_available:
        try:
            send_email(newly_available)
            print(f"[ok] emailed about {len(newly_available)} product(s)")
        except Exception as e:
            # Don't save 'available' as seen if the email failed, so we retry next run.
            for handle, _ in newly_available:
                state[handle] = False
            print(f"[error] email failed: {e}", file=sys.stderr)

    save_state(state)


if __name__ == "__main__":
    main()