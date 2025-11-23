#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Relatório Diário — US10Y (Treasury 10 anos)
- 10 tópicos fixos
- Usa providers.llm_client (PIAPI + fallback)
- Trava diária (.sent) e contador
- Envio opcional ao Telegram
"""

import os
import sys

# garante que o root do repo está no PYTHONPATH
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import argparse
import html
import time
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any

from providers.llm_client import LLMClient
from scripts.tools import title_counter, sent_guard, send_to_telegram
from scripts.bonds.us10y_daily import fetch_us10y_from_fred

BRT = timezone(timedelta(hours=-3))


def today_brt_str() -> str:
    meses = [
        "janeiro", "fevereiro", "março", "abril", "maio", "junho",
        "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"
    ]
    now = datetime.now(BRT)
    return f"{now.day} de {meses[now.month-1]} de {now.year}"


def build_context_block(series_id: str = "DGS10", start: str = "2000-01-01") -> str:
    """
    Busca US10Y via FRED e monta um bloco de contexto factual
    (nível atual, variação, histórico) para o LLM.
    """
    api_key = os.getenv("FRED_API_KEY")
    if not api_key:
        raise RuntimeError("FRED_API_KEY não configurado no ambiente.")

    df = fetch_us10y_from_fred(
        api_key=api_key,
        series_id=series_id,
        observation_start=start,
    )

    df = df.sort_values("date").reset_index(drop=True)
    last = df.iloc[-1]
    last_date = last["date"]
    last_yield = float(last["yield_pct"])

    if len(df) > 1:
        prev = df.iloc[-2]
        prev_date = prev["date"]
        prev_yield = float(prev["yield_pct"])
        delta = last_yield - prev_yield
        delta_bp = delta * 100.0
    else:
        prev_date = None
        prev_yield = None
        delta = 0.0
        delta_bp = 0.0

    min_y = float(df["yield_pct"].min())
    max_y = float(df["yield_pct"].max())
    start_date = df["date"].min()
    end_date = df["date"].max()

    lines = [
        f"- US10Y (DGS10 FRED): {last_yield:.2f}% em {last_date}.",
    ]

    if prev_date is not None:
        lines.append(
            f"- Leitura anterior: {prev_yield:.2f}% em {prev_date}. "
            f"Variação diária: {delta:+.2f} pp ({delta_bp:+.1f} bps)."
        )

    lines.extend(
        [
            f"- Período observado na série: {start_date} → {end_date}.",
            f"- Faixa histórica de yield: mínimo {min_y:.2f}%, máximo {max_y:.2f}%.",
            "- US10Y é a referência global de taxa livre de risco de longo prazo em USD.",
            "- Interpretação ligada a expectativas de inflação, prêmio de prazo e política monetária do Fed.",
            "- A inclinação 2Y–10Y e 10Y–30Y é relevante para entender sinal de ciclo (steepening vs flattening).",
        ]
    )

    return "\n".join(lines)


def gerar_analise_us10y(contexto_textual: str, provider_hint: Optional[str] = None) -> Dict[str, Any]:
    system_msg = (
        "Você é um gestor sênior de renda fixa global, com foco em Treasuries dos EUA. "
        "Escreva em PT-BR, claro, objetivo, com foco em curva de juros, inflação implícita, "
        "política monetária e apetite por risco em bonds."
    )

    user_msg = f"""
Gere um **Relatório Diário — US10Y (Treasury 10 anos)** estruturado nos **10 tópicos abaixo**.
Numere exatamente de 1 a 10, texto contínuo (sem markdown de lista do tipo '- ').

1) Nível atual do US10Y e variação diária
2) Curva de juros EUA (2Y, 10Y, 30Y) — inclinação e movimento do dia
3) Inflação implícita e expectativas de política monetária (Fed, dot plot, próximos meetings)
4) Reprecificação de duration (apetite por juros longos vs curtos)
5) Spreads de crédito e impacto em IG/HY (em linhas gerais)
6) Risco global e fluxo para ativos de risco vs ativos de refúgio (equities vs bonds)
7) Contexto macro recente (dados de inflação, emprego, atividade)
8) Visão institucional (bancos, research, casas de análise) sobre a trajetória da curva
9) Interpretação Executiva (bullet points objetivos, até 5 linhas, em PT-BR)
10) Conclusão (1 parágrafo: curto e médio prazo para US10Y e curva de Treasuries)

Baseie-se no contexto factual levantado:
{contexto_textual}
""".strip()

    llm = LLMClient(provider=provider_hint or None)
    texto = llm.generate(
        system_prompt=system_msg,
        user_prompt=user_msg,
        temperature=0.35,
        max_tokens=1600,
    )
    return {"texto": texto, "provider": llm.active_provider}


def main():
    parser = argparse.ArgumentParser(description="Relatório Diário — US10Y (Treasury 10 anos)")
    parser.add_argument("--send-telegram", action="store_true")
    parser.add_argument("--preview", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--counter-path", default="data/counters.json")
    parser.add_argument("--sent-path", default=None)
    parser.add_argument("--provider", default=None)
    parser.add_argument(
        "--series-id",
        default=os.environ.get("US10Y_FRED_SERIES_ID", "DGS10"),
    )
    parser.add_argument("--start", default="2000-01-01")
    args = parser.parse_args()

    sent_path = args.sent_path or "data/sentinels/us10y_daily.sent"

    # trava diária (evita envio duplicado)
    if not args.force and sent_guard(sent_path):
        print("Já foi enviado hoje (trava .sent). Use --force para ignorar.")
        return

    numero = title_counter(args.counter_path, key="diario_us10y")
    titulo = f"💵 US10Y — Relatório Diário — {today_brt_str()} — Nº {numero}"

    contexto = build_context_block(series_id=args.series_id, start=args.start)

    t0 = time.time()
    llm_out = gerar_analise_us10y(contexto_textual=contexto, provider_hint=args.provider)
    dt = time.time() - t0

    corpo = llm_out["texto"].strip()
    provider_usado = llm_out.get("provider", "?")

    texto_final = (
        f"<b>{html.escape(titulo)}</b>\n\n"
        f"{corpo}\n\n"
        f"<i>Provedor LLM: {html.escape(str(provider_usado))} • {dt:.1f}s</i>"
    )

    print(texto_final)

    if args.send_telegram:
        # send_to_telegram deve ler TELEGRAM_CHAT_ID do ambiente
        send_to_telegram(texto_final, preview=args.preview)


if __name__ == "__main__":
    main()
