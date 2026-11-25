"""Macro context builder based only on supplied market data; no fabricated news."""
def macro_context(metrics):
    latest=metrics.iloc[-1]
    lines=["MACRO/market context derived strictly from Treasury series:"]
    lines.append(f"Observation date: {latest['date']}")
    lines.append(f"2Y: {latest['US2Y']:.3f}%; 10Y: {latest['US10Y']:.3f}%; 30Y: {latest['US30Y']:.3f}%")
    lines.append(f"10Y-2Y spread: {latest['10Y-2Y']:.3f} pp; 30Y-10Y: {latest['30Y-10Y']:.3f} pp")
    lines.append("Interpretation caveat: yields alone do not establish causal macro drivers, inflation expectations, term premium, flows, or institutional positioning.")
    return "\n".join(lines)
