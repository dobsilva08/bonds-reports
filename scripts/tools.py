import os
import json
import requests
from datetime import date

def title_counter(path: str, key: str) -> int:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not os.path.exists(path):
        data = {key: 1}
    else:
        with open(path, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except Exception:
                data = {}

    n = data.get(key, 0) + 1
    data[key] = n

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    return n


def sent_guard(path: str) -> bool:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    today = str(date.today())

    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            last = f.read().strip()
        if last == today:
            return True

    with open(path, "w", encoding="utf-8") as f:
        f.write(today)
    return False


def send_to_telegram(text: str, preview: bool = False):
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN não configurado.")

    if not chat_id:
        raise RuntimeError("TELEGRAM_CHAT_ID não configurado (único permitido).")

    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": not preview
    }

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    r = requests.post(url, json=payload, timeout=30)

    if r.status_code >= 300:
        raise RuntimeError(f"Telegram erro {r.status_code}: {r.text}")

    return True
