"""Compact, rule-based Treasury curve intelligence. Descriptive, not causal."""
def macro_context(metrics):
    latest=metrics.iloc[-1]
    def val(k, default=float("nan")):
        try: return float(latest.get(k,default))
        except (TypeError,ValueError): return default
    slope=val("10Y-2Y"); long_slope=val("30Y-10Y")
    d2=val("US2Y_daily_bps",0); d10=val("US10Y_daily_bps",0); d30=val("US30Y_daily_bps",0)
    vol=val("US10Y_vol30_bps"); fly=val("butterfly")
    z2=val("US2Y_z252"); z10=val("US10Y_z252"); z30=val("US30Y_z252")
    curve="invertida" if slope<0 else "quase plana" if slope<0.25 else "positivamente inclinada"
    if d2>0.5 and d10>0.5 and d30>0.5: move="alta generalizada dos yields"
    elif d2<-0.5 and d10<-0.5 and d30<-0.5: move="queda generalizada dos yields"
    elif d10>d2+0.5: move="steepening no trecho 2Y–10Y"
    elif d10<d2-0.5: move="flattening no trecho 2Y–10Y"
    else: move="movimento misto/contido entre 2Y e 10Y"
    vol_label="alta" if vol>=20 else "elevada" if vol>=12 else "moderada/baixa"
    fly_desc="10Y abaixo da interpolação linear entre 2Y e 30Y" if fly>0 else "10Y acima dessa interpolação" if fly<0 else "curvatura neutra"
    def zdesc(z):
        if z!=z: return "indisponível"
        if z>=2: return "extremo superior"
        if z<=-2: return "extremo inferior"
        if z>=1: return "acima da média"
        if z<=-1: return "abaixo da média"
        return "próximo da média"
    lines=[
      f"• 🧩 <b>Inclinação:</b> {curve} (10Y–2Y: {slope:+.3f} pp; 30Y–10Y: {long_slope:+.3f} pp).",
      f"• 🔄 <b>Movimento:</b> {move}. 2Y {d2:+.1f} bps | 10Y {d10:+.1f} bps | 30Y {d30:+.1f} bps.",
      f"• 🌡️ <b>Volatilidade:</b> {vol_label} — 10Y, 30 observações ({vol:.1f} bps).",
      f"• 📍 <b>Contexto histórico:</b> 2Y {zdesc(z2)} (Z {_fmt(z2)}); 10Y {zdesc(z10)} (Z {_fmt(z10)}); 30Y {zdesc(z30)} (Z {_fmt(z30)}).",
      f"• 🌀 <b>Curvatura:</b> butterfly {fly:+.3f} pp — {fly_desc}."
    ]
    return "\n".join(lines)

def _fmt(z):
    return "N/D" if z!=z else f"{z:.2f}"
