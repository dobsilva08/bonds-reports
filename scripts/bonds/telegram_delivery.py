"""Telegram delivery with response verification and post-success marker."""
import os, json, time
from pathlib import Path
import requests

def send_message(text, preview=False, marker=None, html_mode=True):
    token=os.getenv("TELEGRAM_BOT_TOKEN")
    chat=os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat: raise RuntimeError("Telegram credentials missing")
    payload={"chat_id":chat,"text":text,"disable_web_page_preview":not preview}
    if html_mode: payload["parse_mode"]="HTML"
    response=requests.post(f"https://api.telegram.org/bot{token}/sendMessage",json=payload,timeout=30)
    if not response.ok:
        raise RuntimeError(f\"Telegram sendMessage HTTP {response.status_code}: {response.text}\")
    body=response.json()
    if not body.get("ok") or not body.get("result"):
        raise RuntimeError(f"Telegram API did not confirm delivery: {body}")
    if marker:
        p=Path(marker); p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text(json.dumps({"sent_at":time.time(),"message_id":body["result"].get("message_id")}),encoding="utf-8")
    return body

def send_photo(path, caption="", marker=None):
    token=os.getenv("TELEGRAM_BOT_TOKEN"); chat=os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat: raise RuntimeError("Telegram credentials missing")
    with open(path,"rb") as photo:
        response=requests.post(f"https://api.telegram.org/bot{token}/sendPhoto",
            data={"chat_id":chat,"caption":caption},files={"photo":photo},timeout=60)
    if not response.ok:
        raise RuntimeError(f\"Telegram sendPhoto HTTP {response.status_code}: {response.text}\")
    body=response.json()
    if not body.get("ok") or not body.get("result"): raise RuntimeError(f"Telegram API delivery not confirmed: {body}")
    if marker:
        p=Path(marker); p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text(json.dumps({"sent_at":time.time(),"message_id":body["result"].get("message_id")}),encoding="utf-8")
    return body
