"""Telegram report builder with On-Chain-inspired editorial layout."""
from scripts.bonds.macro_engine import macro_context

SEPARATOR = "━━━━━━━━━━━━━━━━━━━━"

def _num(v, digits=3):
    try:
        return f"{float(v):.{digits}f}"
    except (TypeError, ValueError):
        return "N/D"

def _change(v):
    try:
        n=float(v)
        arrow="🔺" if n>0.05 else "🔻" if n<-0.05 else "➡️"
        return f"{n:+.1f} bps {arrow}"
    except (TypeError, ValueError):
        return "N/D"

def _curve_status(v):
    try:
        n=float(v)
        return "🔴 Invertida" if n<0 else "🟡 Plana" if n<0.25 else "🟢 Positiva"
    except (TypeError, ValueError):
        return "N/D"

def build_daily_report(metrics):
    latest=metrics.iloc[-1]
    data_date=str(latest["date"])[:10]
    slope=latest.get("10Y-2Y")
    lines=[
      "🟡 <b>US TREASURY — DAILY INTELLIGENCE</b>",
      "<i>Fixed Income • U.S. Yield Curve</i>",
      f"📅 {data_date}",
      "",
      SEPARATOR,
      "📊 <b>MARKET SNAPSHOT</b>",
      "",
      f"• <b>2Y:</b> {_num(latest.get('US2Y'))}%  | {_change(latest.get('US2Y_daily_bps'))}",
      f"• <b>10Y:</b> {_num(latest.get('US10Y'))}% | {_change(latest.get('US10Y_daily_bps'))}",
      f"• <b>30Y:</b> {_num(latest.get('US30Y'))}% | {_change(latest.get('US30Y_daily_bps'))}",
      "",
      SEPARATOR,
      "📐 <b>YIELD CURVE</b>",
      "",
      f"• <b>10Y–2Y:</b> {_num(latest.get('10Y-2Y'))} pp  {_curve_status(slope)}",
      f"• <b>30Y–10Y:</b> {_num(latest.get('30Y-10Y'))} pp",
      f"• <b>30Y–2Y:</b> {_num(latest.get('30Y-2Y'))} pp",
      f"• <b>Butterfly:</b> {_num(latest.get('butterfly'))} pp",
      "",
      SEPARATOR,
      "🌡️ <b>VOLATILITY &amp; HISTORICAL POSITION</b>",
      "",
      f"• <b>10Y realized vol (30d):</b> {_num(latest.get('US10Y_vol30_bps'),1)} bps",
      f"• <b>Z-score:</b> 2Y {_num(latest.get('US2Y_z252'),2)} | 10Y {_num(latest.get('US10Y_z252'),2)} | 30Y {_num(latest.get('US30Y_z252'),2)}",
      "",
      SEPARATOR,
      "🧭 <b>MARKET INTERPRETATION</b>",
      "",
      macro_context(metrics),
      "",
      SEPARATOR,
      "⚠️ <b>ANALYTICAL LIMITS</b>",
      "• Indicadores quantitativos descrevem movimentos e posicionamento estatístico da curva; não identificam causas por si só.",
      "• Spreads e Z-scores não são sinais automáticos de compra ou venda.",
      "",
      "📚 <i>Fonte: Federal Reserve / FRED</i>",
      "<i>Automated quantitative analysis • Não constitui recomendação de investimento.</i>"
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
