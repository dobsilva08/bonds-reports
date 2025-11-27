# coding: utf-8
"""
Helpers reutilizáveis para os scripts de relatório:
- title_counter(counter_path, key)
- sent_guard(sent_path)  -> True se já foi enviado hoje
- mark_sent(sent_path)   -> cria a sentinel após envio
- send_to_telegram(text, preview=False)
"""

import os
import json
import time
from datetime import datetime


def _ensure_dir_for_file(path: str):
    d = os.path.dirname(path)
    if d and not os.path.exists(d):
        os.makedirs(d, exist_ok=True)


def title_counter(counter_path: str = "data/counters.json", key: str = "default"):
    """
    Lê um arquivo JSON com contadores, incrementa o contador 'key' e salva.
    Retorna o número novo (int).
    """
    _ensure_dir_for_file(counter_path)

    if os.path.exists(counter_path):
        try:
            with open(counter_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}
    else:
        data = {}

    current = int(data.get(key, 0))
    current += 1
    data[key] = current

    try:
        with open(counter_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[title_counter] erro ao salvar {counter_path}: {e}")

    return current


def sent_guard(sent_path: str):
    """
    Verifica a existencia de um arquivo sentinel (.sent) que indica que já foi enviado hoje.
    Retorna True se o arquivo existir (ou seja: já enviado).
    """
    return os.path.exists(sent_path)


def mark_sent(sent_path: str):
    """
    Marca o envio criando o arquivo sentinel com timestamp.
    """
    _ensure_dir_for_file(sent_path)
    payload = {
        "sent_at": datetime.utcnow().isoformat() + "Z",
        "ts": int(time.time()),
    }
    try:
        with open(sent_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[mark_sent] erro ao criar sentinel {sent_path}: {e}")


def send_to_telegram(text: str, preview: bool = False, html_mode: bool = True):
    """
    Envia mensagem para Telegram.
    - Prioridade de escolha do chat_id:
       1) TELEGRAM_CHAT_ID
       2) se preview=True -> TELEGRAM_CHAT_ID_TEST
       3) TELEGRAM_CHAT_ID_BONDS
       4) TELEGRAM_CHAT_ID_TEST
    - Se TELEGRAM_MESSAGE_THREAD_ID estiver definido, adiciona message_thread_id.
    - Usa parse_mode HTML por padrão.
    Retorna o JSON de resposta da API Telegram se sucesso.
    Lança RuntimeError em caso de configuração inválida ou erro HTTP.
    """
    import requests

    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN não configurado no ambiente.")

    # Preferência: TELEGRAM_CHAT_ID (único), depois as variações anteriores
    env_chat_primary = os.environ.get("TELEGRAM_CHAT_ID")
    env_chat_bonds = os.environ.get("TELEGRAM_CHAT_ID_BONDS")
    env_chat_test = os.environ.get("TELEGRAM_CHAT_ID_TEST")

    # Escolha do chat
    chat_id = None
    if env_chat_primary:
        chat_id = env_chat_primary
    else:
        # se preview foi pedido, dá prioridade ao CHAT_ID_TEST
        if preview and env_chat_test:
            chat_id = env_chat_test
        # senão tenta CHAT_ID_BONDS
        if not chat_id and env_chat_bonds:
            chat_id = env_chat_bonds
        # por fim tenta CHAT_ID_TEST (fallback)
        if not chat_id and env_chat_test:
            chat_id = env_chat_test

    if not chat_id:
        raise RuntimeError(
            "Nenhum TELEGRAM_CHAT_ID configurado. "
            "Defina TELEGRAM_CHAT_ID (recomendado) ou TELEGRAM_CHAT_ID_BONDS / TELEGRAM_CHAT_ID_TEST."
        )

    thread_id = os.environ.get("TELEGRAM_MESSAGE_THREAD_ID")

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": True,
    }
    if html_mode:
        payload["parse_mode"] = "HTML"
    if thread_id:
        try:
            payload["message_thread_id"] = int(thread_id)
        except Exception:
            # se não for inteiro, ignora (não quebra)
            pass

    resp = requests.post(url, json=payload, timeout=30)
    try:
        resp.raise_for_status()
    except Exception as e:
        # log detalhado e raise
        print("[send_to_telegram] ERRO ao enviar mensgem Telegram:", e)
        print("[send_to_telegram] status_code:", resp.status_code, "response:", resp.text)
        raise RuntimeError(f"Telegram API devolveu erro HTTP {resp.status_code}: {resp.text}")

    j = resp.json()
    if not j.get("ok"):
        raise RuntimeError(f"Telegram API devolveu erro: {j}")

    return j
