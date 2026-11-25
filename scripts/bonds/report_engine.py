"""Executive Telegram report builder."""
from scripts.bonds.macro_engine import macro_context

def _change(v):
    try: return f"{float(v):+.1f} bps"
    except Exception: return "N/A"

def build_daily_report(metrics):
    latest=metrics.iloc[-1]
    data_date=str(latest["date"])[:10]
    lines=[
      "<b>🇺🇸 US TREASURY &amp; MACRO INTELLIGENCE</b>",
      "<i>Daily Fixed Income Market Monitor</i>",
      f"<b>Data de referência:</b> {data_date}",
      "",
      "<b>1 | MARKET SNAPSHOT</b>",
      f"• 2Y: <b>{latest['US2Y']:.3f}%</b> ({_change(latest.get('US2Y_daily_bps'))})",
      f"• 10Y: <b>{latest['US10Y']:.3f}%</b> ({_change(latest.get('US10Y_daily_bps'))})",
      f"• 30Y: <b>{latest['US30Y']:.3f}%</b> ({_change(latest.get('US30Y_daily_bps'))})",
      "",
      "<b>2 | CURVE &amp; SPREADS</b>",
      f"• 10Y–2Y: <b>{latest['10Y-2Y']:+.3f} pp</b>",
      f"• 30Y–10Y: <b>{latest['30Y-10Y']:+.3f} pp</b>",
      f"• 30Y–2Y: <b>{latest['30Y-2Y']:+.3f} pp</b>",
      f"• Butterfly: <b>{latest['butterfly']:+.3f} pp</b>",
      "",
      "<b>3 | VOLATILITY &amp; STATISTICAL POSITION</b>",
      f"• 10Y volatility (30 observations): {_change(latest.get('US10Y_vol30_bps'))}",
      f"• Z-score 2Y: <b>{latest.get('US2Y_z252',float('nan')):.2f}</b> | 10Y: <b>{latest.get('US10Y_z252',float('nan')):.2f}</b> | 30Y: <b>{latest.get('US30Y_z252',float('nan')):.2f}</b>",
      "",
      "<b>4 | MACRO INTELLIGENCE</b>",
      macro_context(metrics),
      "",
      "<i>Fonte: Federal Reserve / FRED. Análise quantitativa descritiva; não constitui recomendação de investimento.</i>"
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
