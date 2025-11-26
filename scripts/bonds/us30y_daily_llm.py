#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Relatório Diário — US30Y (Treasury 30 anos)
- 10 tópicos fixos
- Usa providers.llm_client (PIAPI + fallback)
- Trava diária (.sent) e contador
- Envio opcional ao Telegram
"""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import argparse
import html
import time
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any

from providers.llm_client import LLMClient
from scripts.gas.tools import title_counter, sent_guard, send_to_telegram
from scripts.bonds.us30y_daily import fetch_us30y_from_fred

BRT = timezone(timedelta(hours=-3))

def today_brt_str() -> str:
    meses = ["janeiro","fevereiro","março","abril","maio","junho",
             "julho","agosto","setembro","outubro","novembro","dezembro"]
    now = datetime.now(BRT)
    return f"{now.day} de {meses[now.month-1]} de {now.year}"

def build_context_block(series_id: str = "DGS30", start: str = "2000-01-01") -> str:
    api_key = os.getenv("FRED_API_KEY")
    if not api_key:
        raise RuntimeError("FRED_API_KEY não configurado no ambiente.")
    df = fetch_us30y_from_fred(api_key=api_key, series_id=series_id, observation_start=start)
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
        f"- US30Y (DGS30 FRED): {last_yield:.2f}% em {last_date}.",
    ]
    if prev_date is not None:
        lines.append(f"- Leitura anterior: {prev_yield:.2f}% em {prev_date}. Variação diária: {delta:+.2f} pp ({delta_bp:+.1f} bps).")
    lines.extend([
        f"- Período observado: {start_date} → {end_date}.",
        f"- Faixa histórica: mínimo {min_y:.2f}%, máximo {max_y:.2f}%.",
        "- US30Y reflete a parte longa da curva e é sensível a expectativas de inflação estrutural, term premium e longevidade de política monetária.",
        "- Movimentos no US30Y impactam duration de portfólios longos e pricing de ativos sensíveis a yields de longo prazo.",
    ])
    return "\n".join(lines)

def gerar_analise_us30y(contexto_textual: str, provider_hint: Optional[str] = None) -> Dict[str, Any]:
    system_msg = "Você é um gestor sênior de renda fixa, escreva em PT-BR, objetivo, focado em juros longos e risco de prazo."
    user_msg = f"""
Gere um **Relatório Diário — US30Y (Treasury 30 anos)** estruturado nos 10 tópicos abaixo.
Numere exatamente de 1 a 10.

1) Nível atual do US30Y e variação diária
2) Term premium e interpretação estrutural
3) Curva 2Y–10Y e 10Y–30Y: inclinação e movimento do dia
4) Impacto em duration e portfólios longos
5) Spreads de crédito longos (corporate, IG vs HY)
6) Fluxos institucionais (pension funds, insurers)
7) Dados macro relevantes (inflação, wages, atividade)
8) Perspectiva de bancos centrais e impacto em yield longo
9) Interpretação Executiva (bullet points)
10) Conclusão (curto e médio prazo)
Baseie-se no contexto factual:
{contexto_textual}
""".strip()
    llm = LLMClient(provider=provider_hint or None)
    texto = llm.generate(system_prompt=system_msg, user_prompt=user_msg, temperature=0.25, max_tokens=1200)
    return {"texto": texto, "provider": llm.active_provider}

def main():
    parser = argparse.ArgumentParser(description="Relatório Diário — US30Y (DGS30)")
    parser.add_argument("--send-telegram", action="store_true")
    parser.add_argument("--preview", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--counter-path", default="data/counters.json")
    parser.add_argument("--sent-path", default=None)
    parser.add_argument("--provider", default=None)
    parser.add_argument("--series-id", default=os.environ.get("US30Y_FRED_SERIES_ID", "DGS30"))
    parser.add_argument("--start", default="2000-01-01")
    args = parser.parse_args()

    sent_path = args.sent_path or "data/sentinels/us30y_daily.sent"
    if not args.force and sent_guard(sent_path):
        print("Já foi enviado hoje (trava .sent). Use --force para ignorar.")
        return

    numero = title_counter(args.counter_path, key="diario_us30y")
    titulo = f"💵 US30Y — Relatório Diário — {today_brt_str()} — Nº {numero}"

    contexto = build_context_block(series_id=args.series_id, start=args.start)
    t0 = time.time()
    llm_out = gerar_analise_us30y(contexto_textual=contexto, provider_hint=args.provider)
    dt = time.time() - t0

    corpo = llm_out["texto"].strip()
    provider_usado = llm_out.get("provider", "?")
    texto_final = f"<b>{html.escape(titulo)}</b>\n\n{corpo}\n\n<i>Provedor LLM: {html.escape(str(provider_usado))} • {dt:.1f}s</i>"
    print(texto_final)
    if args.send_telegram:
        send_to_telegram(texto_final, preview=args.preview)

if __name__ == "__main__":
    main()
