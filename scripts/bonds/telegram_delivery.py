"""Telegram delivery with response verification and migration-aware retries."""
import os, json, time
from pathlib import Path
import requests

def _post_with_migration_retry(endpoint, *, json_payload=None, data_payload=None, files=None, timeout=30):
    token=os.getenv("TELEGRAM_BOT_TOKEN")
    if not token: raise RuntimeError("Telegram credentials missing")
    url=f"https://api.telegram.org/bot{token}/{endpoint}"
    response=requests.post(url,json=json_payload,data=data_payload,files=files,timeout=timeout)
    try:
        body=response.json()
    except Exception:
        body={}
    migrated=(body.get("parameters") or {}).get("migrate_to_chat_id") if isinstance(body,dict) else None
    if migrated:
        if json_payload is not None: json_payload["chat_id"]=migrated
        if data_payload is not None: data_payload["chat_id"]=migrated
        # Keep the new ID for subsequent sends during this workflow execution.
        os.environ["TELEGRAM_CHAT_ID"]=str(migrated)
        gh_env=os.getenv("GITHUB_ENV")
        if gh_env:
            with open(gh_env,"a",encoding="utf-8") as f: f.write(f"TELEGRAM_CHAT_ID={migrated}\n")
        if files:
            for fp in files.values():
                try: fp.seek(0)
                except Exception: pass
        response=requests.post(url,json=json_payload,data=data_payload,files=files,timeout=timeout)
        try: body=response.json()
        except Exception: body={}
    if not response.ok or not isinstance(body,dict) or not body.get("ok"):
        detail=body.get("description",response.text) if isinstance(body,dict) else response.text
        raise RuntimeError(f"Telegram {endpoint} HTTP {response.status_code}: {detail}")
    return body

def send_message(text, preview=False, marker=None, html_mode=True):
    chat=os.getenv("TELEGRAM_CHAT_ID")
    if not chat: raise RuntimeError("Telegram credentials missing")
    payload={"chat_id":chat,"text":text,"disable_web_page_preview":not preview}
    if html_mode: payload["parse_mode"]="HTML"
    body=_post_with_migration_retry("sendMessage",json_payload=payload,timeout=30)
    if marker:
        p=Path(marker); p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text(json.dumps({"sent_at":time.time(),"message_id":body["result"].get("message_id")}),encoding="utf-8")
    return body

def send_photo(path, caption="", marker=None):
    chat=os.getenv("TELEGRAM_CHAT_ID")
    if not chat: raise RuntimeError("Telegram credentials missing")
    payload={"chat_id":chat,"caption":caption}
    with open(path,"rb") as photo:
        body=_post_with_migration_retry("sendPhoto",data_payload=payload,files={"photo":photo},timeout=60)
    if marker:
        p=Path(marker); p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text(json.dumps({"sent_at":time.time(),"message_id":body["result"].get("message_id")}),encoding="utf-8")
    return body
