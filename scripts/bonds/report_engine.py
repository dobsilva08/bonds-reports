"""Executive Telegram report builder with editorial layout."""
from scripts.bonds.macro_engine import macro_context

def _change(v):
    try:
        n=float(v)
        arrow="↗️" if n>0.05 else "↘️" if n<-0.05 else "➡️"
        return f"{n:+.1f} bps {arrow}"
    except Exception:
        return "N/D"

def build_daily_report(metrics):
    latest=metrics.iloc[-1]
    data_date=str(latest["date"])[:10]
    lines=[
      "🟡 <b>US TREASURY — DAILY MARKET INTELLIGENCE</b>",
      "<i>Fixed Income | Curva de juros dos EUA</i>",
      f"📅 {data_date}",
      "",
      "━━━━━━━━━━━━━━",
      "📈 <b>Movimento dos Treasuries</b>",
      "",
      f"• <b>2 anos:</b> {latest['US2Y']:.3f}%  | {_change(latest.get('US2Y_daily_bps'))}",
      f"• <b>10 anos:</b> {latest['US10Y']:.3f}% | {_change(latest.get('US10Y_daily_bps'))}",
      f"• <b>30 anos:</b> {latest['US30Y']:.3f}% | {_change(latest.get('US30Y_daily_bps'))}",
      "",
      "━━━━━━━━━━━━━━",
      "📐 <b>Estrutura da Curva</b>",
      "",
      f"• 10Y–2Y: <b>{latest['10Y-2Y']:+.3f} pp</b>",
      f"• 30Y–10Y: <b>{latest['30Y-10Y']:+.3f} pp</b>",
      f"• 30Y–2Y: <b>{latest['30Y-2Y']:+.3f} pp</b>",
      f"• Curvatura (Butterfly): <b>{latest['butterfly']:+.3f} pp</b>",
      "",
      "━━━━━━━━━━━━━━",
      "🌡️ <b>Volatilidade &amp; Posição Estatística</b>",
      "",
      f"• Volatilidade do 10Y (30 sessões): <b>{_change(latest.get('US10Y_vol30_bps'))}</b>",
      f"• Z-score: 2Y <b>{latest.get('US2Y_z252',float('nan')):.2f}</b> | 10Y <b>{latest.get('US10Y_z252',float('nan')):.2f}</b> | 30Y <b>{latest.get('US30Y_z252',float('nan')):.2f}</b>",
      "",
      "━━━━━━━━━━━━━━",
      "🧭 <b>Leitura do Mercado</b>",
      "",
      macro_context(metrics),
      "",
      "━━━━━━━━━━━━━━",
      "⚠️ <b>Limites da análise</b>",
      "• Indicadores descrevem comportamento de preços e curva; não identificam isoladamente causas, expectativas do Fed, inflação ou fluxo institucional.",
      "• Z-scores e spreads não são sinais automáticos de compra ou venda.",
      "",
      "Fonte: Federal Reserve / FRED | Análise quantitativa automatizada."
    ]
    return "\n".join(lines)

def build_prompt(series_name, factual_context, macro_context_text=""):
    system=("You are a fixed-income analyst. Write in Brazilian Portuguese. Never fabricate news, "
            "macro data, positioning, consensus, or causality. Separate facts, interpretations and hypothetical scenarios.")
    user=f"""Daily executive report — {series_name}. Use only provided data.
Structure: factual snapshot, curve movement, supported interpretations, limitations and hypothetical scenarios.
DATA:
{factual_context}
CONTEXT:
{macro_context_text}"""
    return system,user

def validate_report(text):
    if not isinstance(text,str) or len(text.strip())<150:
        raise ValueError("LLM report is empty or suspiciously short")
    return text.strip()
