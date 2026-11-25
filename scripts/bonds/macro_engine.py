"""Rule-based Treasury curve intelligence. Descriptive, not causal."""
def macro_context(metrics):
    latest=metrics.iloc[-1]
    def val(k, default=0):
        try: return float(latest.get(k,default))
        except (TypeError,ValueError): return default
    slope=val("10Y-2Y"); long_slope=val("30Y-10Y"); spread30_2=val("30Y-2Y")
    d2=val("US2Y_daily_bps"); d10=val("US10Y_daily_bps"); d30=val("US30Y_daily_bps")
    vol=val("US10Y_vol30_bps"); fly=val("butterfly")
    z2=val("US2Y_z252",float("nan")); z10=val("US10Y_z252",float("nan")); z30=val("US30Y_z252",float("nan"))
    if slope<0: curve="invertida (10Y abaixo do 2Y)"
    elif slope<0.25: curve="praticamente flat / pouco inclinada"
    else: curve="positivamente inclinada"
    if d2>0.5 and d10>0.5 and d30>0.5: move="alta generalizada dos yields"
    elif d2<-0.5 and d10<-0.5 and d30<-0.5: move="queda generalizada dos yields"
    elif d10>d2+0.5: move="movimento de steepening na parte 2Y–10Y (10Y subiu mais que 2Y)"
    elif d10<d2-0.5: move="movimento de flattening na parte 2Y–10Y (o yield de 10Y teve variação inferior à do 2Y; se ambos caíram, o 10Y caiu mais; se ambos subiram, o 10Y subiu menos)"
    else: move="movimento relativamente misto/contido nos vértices 2Y e 10Y"
    vol_label="alta" if vol>=20 else "elevada" if vol>=12 else "moderada/baixa"
    butterfly_desc="curvatura positiva: 10Y está relativamente abaixo da interpolação simples entre 2Y e 30Y" if fly>0 else "curvatura negativa: 10Y está relativamente acima da interpolação simples entre 2Y e 30Y" if fly<0 else "curvatura neutra"
    def zdesc(z):
        if z!=z: return "indisponível"
        if z>=2: return "bem acima da média histórica recente"
        if z<=-2: return "bem abaixo da média histórica recente"
        if z>=1: return "acima da média recente"
        if z<=-1: return "abaixo da média recente"
        return "próximo da média recente"
    lines=[
      "<b>LEITURA DO MERCADO</b>",
      f"• A curva está {curve}, com spread 10Y–2Y de {slope:+.3f} pp. O spread 30Y–10Y é {long_slope:+.3f} pp, indicando prêmio de inclinação também no trecho longo.",
      f"• No dia, observou-se {move}: 2Y {d2:+.1f} bps, 10Y {d10:+.1f} bps e 30Y {d30:+.1f} bps.",
      f"• A volatilidade realizada do 10Y (janela de 30 observações) está {vol_label} ({vol:.1f} bps).",
      f"• Posicionamento estatístico: 2Y {zdesc(z2)} (Z={z2:.2f}); 10Y {zdesc(z10)} (Z={z10:.2f}); 30Y {zdesc(z30)} (Z={z30:.2f}).",
      f"• Curvatura: butterfly {fly:+.3f} pp — {butterfly_desc}.",
      "",
      "<b>O QUE OS DADOS NÃO DIZEM</b>",
      "• A curva, isoladamente, não confirma expectativas de inflação, trajetória do Fed, prêmio de prazo, fluxo ou causa específica para o movimento.",
      "• Z-scores descrevem posição relativa na janela histórica usada; não são sinais automáticos de compra/venda."
    ]
    return "\n".join(lines)
