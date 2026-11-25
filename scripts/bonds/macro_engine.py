"""Rule-based Treasury curve intelligence. Descriptive, not causal."""
def macro_context(metrics):
    latest=metrics.iloc[-1]
    def val(k, default=0):
        try: return float(latest.get(k,default))
        except (TypeError,ValueError): return default
    slope=val("10Y-2Y"); long_slope=val("30Y-10Y")
    d2=val("US2Y_daily_bps"); d10=val("US10Y_daily_bps"); d30=val("US30Y_daily_bps")
    vol=val("US10Y_vol30_bps"); fly=val("butterfly")
    z2=val("US2Y_z252",float("nan")); z10=val("US10Y_z252",float("nan")); z30=val("US30Y_z252",float("nan"))
    curve="invertida" if slope<0 else "quase plana" if slope<0.25 else "positivamente inclinada"
    if d2>0.5 and d10>0.5 and d30>0.5: move="alta generalizada dos yields"
    elif d2<-0.5 and d10<-0.5 and d30<-0.5: move="queda generalizada dos yields"
    elif d10>d2+0.5: move="steepening no trecho 2Y–10Y"
    elif d10<d2-0.5: move="flattening no trecho 2Y–10Y"
    else: move="movimento misto/contido entre 2Y e 10Y"
    vol_label="alta" if vol>=20 else "elevada" if vol>=12 else "moderada/baixa"
    fly_desc="curvatura positiva (10Y abaixo da interpolação linear entre 2Y e 30Y)" if fly>0 else "curvatura negativa (10Y acima dessa interpolação)" if fly<0 else "curvatura neutra"
    def zdesc(z):
        if z!=z: return "indisponível"
        if z>=2: return "bem acima da média recente"
        if z<=-2: return "bem abaixo da média recente"
        if z>=1: return "acima da média recente"
        if z<=-1: return "abaixo da média recente"
        return "próximo da média recente"
    lines=[
      f"• <b>Inclinação:</b> a curva está {curve}. O spread 10Y–2Y é {slope:+.3f} pp e o 30Y–10Y é {long_slope:+.3f} pp.",
      f"• <b>Dinâmica do dia:</b> {move}; variações de 2Y {d2:+.1f} bps, 10Y {d10:+.1f} bps e 30Y {d30:+.1f} bps.",
      f"• <b>Volatilidade:</b> a volatilidade realizada do 10Y em 30 observações está {vol_label} ({vol:.1f} bps).",
      f"• <b>Referência histórica:</b> 2Y {zdesc(z2)} (Z {z2:.2f}); 10Y {zdesc(z10)} (Z {z10:.2f}); 30Y {zdesc(z30)} (Z {z30:.2f}).",
      f"• <b>Curvatura:</b> butterfly {fly:+.3f} pp — {fly_desc}."
    ]
    return "\n".join(lines)
