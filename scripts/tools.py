#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Funções utilitárias compartilhadas pelos relatórios:

- title_counter: contador incremental salvo em JSON
- sent_guard: trava diária de envio (.sent)
- send_to_telegram: envio de mensagem HTML para o Telegram
"""

import os
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any

import requests

BRT = timezone(timedelta(hours=-3))


# ------------------------------------------------------------------ #
# Contador de relatórios
# ------------------------------------------------------------------ #
def title_counter(path: str, key: str) -> int:
    """
    Incrementa e retorna o contador associado a 'key' em um JSON.

    Exemplo:
      numero = title_counter("data/counters.json", key="diario_us10y")
    """
    data: Dict[str, Any] = {}

    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}

    value = int(data.get(key, 0)) + 1
    data[key] = value

    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return value


# ------------------------------------------------------------------ #
# Trava diária (.sent)
# ------------------------------------------------------------------ #
def sent_guard(sent_path: str) -> bool:
    """
    Garante que só um envio seja feito por dia.
    Retorna True se JÁ FOI enviado hoje (ou seja, deve abortar).
    Retorna False se AINDA NÃO foi enviado hoje (segue o fluxo).

    Implementação: salva a data de hoje (BRT) em um arquivo .sent.
    """
    today_str = datetime.now(BRT).date().isoformat()

    if os.path.exists(sent_path):
        try:
            with open(sent_path, "r", encoding="utf-8") as f:
                last = f.read().strip()
            if last == today_str:
                return True
        except Exception:
            pass

    os.makedirs(os.path.dirname(sent_path), exist_ok=True)
    with open(sent_path, "w", encoding="utf-8") as f:
        f.write(today_str)

    return False


# ------------------------------------------------------------------ #
# Envio para Telegram
# ------------------------------------------------------------------ #
def send_to_telegram(text: str, preview: bool = False) -> None:
    """
    Envia 'text' (HTML) para o Telegram.

    Requer:
      - TELEGRAM_BOT_TOKEN
      - TELEGRAM_CHAT_ID

    Se 'preview' for True, apenas marca a mensagem com prefixo "[PREVIEW]"
    (mas pode usar a mesma sala).
    """
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        raise RuntimeError("TELEGRAM_BOT_TOKEN ou TELEGRAM_CHAT_ID não configurados.")

    base_url = f"https://api.telegram.org/bot{token}/sendMessage"

    final_text = text
    if preview:
        final_text = "<b>[PREVIEW]</b>\n\n" + text

    payload = {
        "chat_id": chat_id,
        "text": final_text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }

    resp = requests.post(base_url, data=payload, timeout=30)
    resp.raise_for_status()
    # não precisa retornar nada
