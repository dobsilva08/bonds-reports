"""Transparent Treasury-curve regime and observations; avoids causal claims."""
def _fmt(x, digits=3):
    try:
        return f"{float(x):.{digits}f}"
    except Exception:
        return "N/A"

def macro_context(metrics):
    latest=metrics.iloc[-1]
    prev=metrics.iloc[-2] if len(metrics)>1 else latest
    s=float(latest["10Y-2Y"]); s30=float(latest["30Y-10Y"])
    d2=float(latest["US2Y_daily_bps"]); d10=float(latest["US10Y_daily_bps"]); d30=float(latest["US30Y_daily_bps"])
    if s<0: curve="INVERTED (10Y–2Y)"
    elif s<0.25: curve="FLAT / LOW-SLOPE (10Y–2Y)"
    else: curve="NORMAL POSITIVE SLOPE (10Y–2Y)"
    if d10>d2: movement="BEAR STEEPENING tendency (10Y rose more than 2Y)"
    elif d10<d2: movement="BULL STEEPENING / flattening tendency (2Y moved more than 10Y)"
    else: movement="PARALLEL / similar daily movement at 2Y and 10Y"
    vol=float(latest.get("US10Y_vol30_bps",0) or 0)
    regime="HIGH" if vol>=20 else ("ELEVATED" if vol>=12 else "MODERATE/LOW")
    lines=[
      "US TREASURY & MACRO INTELLIGENCE | Daily Fixed Income Market Monitor",
      f"Observation: {latest['date']}",
      f"Curve regime: {curve}; 10Y–2Y={s:+.3f} pp; 30Y–10Y={s30:+.3f} pp.",
      f"Daily yield changes: 2Y {d2:+.1f} bps | 10Y {d10:+.1f} bps | 30Y {d30:+.1f} bps.",
      f"Curve movement: {movement}.",
      f"10Y realized volatility (30 observations, daily changes): {_fmt(vol)} bps; classification: {regime}.",
      f"Butterfly (30Y−2×10Y+2Y): {_fmt(latest['butterfly'])} pp.",
      "These classifications are mechanical descriptions of the supplied yield data, not predictions or proof of causal macro drivers.",
      "Yield data alone cannot establish inflation expectations, term premium, flows, positioning, central-bank intent, or news catalysts."
    ]
    return "\n".join(lines)
