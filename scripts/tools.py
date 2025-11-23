#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Funções utilitárias compartilhadas pelos relatórios:

- title_counter: contador incremental salvo em JSON
- sent_guard: trava diária de envio (.sent)
- send_to_telegram: envio de mensagem (com proteção para limite de tamanho)
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

def _send_chunk(token: str, chat_id: str, text: str, use_html: bool) -> None:
    """Envia um único pedaço de texto para o Telegram."""
    base_url = f"https://api.telegram.org/bot{token}/sendMessage"

    payload = {
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": True,
    }
    if use_html:
        payload["parse_mode"] = "HTML"

    resp = requests.post(base_url, data=payload, timeout=30)
    try:
        resp.raise_for_status()
    except requests.HTTPError as e:
        # Loga o corpo da resposta pra facilitar debug
        print("[Telegram] Erro ao enviar mensagem:", resp.text)
        raise e


def send_to_telegram(text: str, preview: bool = False) -> None:
    """
    Envia 'text' para o Telegram, respeitando o limite de tamanho da API.

    Requer:
      - TELEGRAM_BOT_TOKEN
      - TELEGRAM_CHAT_ID

    Se 'preview' for True, prefixa a mensagem com [PREVIEW].
    Se o texto exceder ~4000 caracteres, ele é dividido em múltiplas mensagens.
    A primeira tentativa usa HTML; se precisar quebrar, envia em texto puro.
    """
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        raise RuntimeError("TELEGRAM_BOT_TOKEN ou TELEGRAM_CHAT_ID não configurados.")

    final_text = text
    if preview:
        final_text = "<b>[PREVIEW]</b>\n\n" + text

    MAX_LEN = 4000  # abaixo do limite oficial (4096) pra dar folga

    if len(final_text) <= MAX_LEN:
        # Mensagem curta: pode usar HTML normalmente
        _send_chunk(token, chat_id, final_text, use_html=True)
        return

    # Mensagem longa: quebra em pedaços de até MAX_LEN e envia sem HTML
    # (para evitar problema de tags quebradas).
    print(f"[Telegram] Mensagem com {len(final_text)} caracteres, será dividida em partes.")

    # Remove tags HTML no preview longo pra evitar bagunça
    if preview:
        # substitui o [PREVIEW] por texto simples no início
        sem_preview_tag = "[PREVIEW]\n\n" + text
        final_text = sem_preview_tag

    start = 0
    part = 1
    total_len = len(final_text)
    while start < total_len:
        chunk = final_text[start:start + MAX_LEN]
        prefix = f"(parte {part})\n" if total_len > MAX_LEN else ""
        _send_chunk(token, chat_id, prefix + chunk, use_html=False)
        start += MAX_LEN
        part += 1
