"""Unified data/analytics pipeline entry point."""
import os
from scripts.bonds.data_engine import collect_all
from scripts.bonds.analytics_engine import curve_metrics
from scripts.bonds.macro_engine import macro_context

def main():
    data=collect_all(start=os.getenv("BONDS_START_DATE","2000-01-01"))
    metrics=curve_metrics(data)
    out="pipelines/bonds/analytics.csv"
    metrics.to_csv(out,index=False)
    latest=metrics.iloc[-1]
    text=("📊 <b>TREASURY CURVE — DAILY SNAPSHOT</b>\n"
          f"Data: {latest['date']}\n"
          f"US2Y: {latest['US2Y']:.3f}% | US10Y: {latest['US10Y']:.3f}% | US30Y: {latest['US30Y']:.3f}%\n"
          f"10Y-2Y: {latest['10Y-2Y']:.3f} pp | 30Y-10Y: {latest['30Y-10Y']:.3f} pp\n"
          f"Butterfly (30-2×10+2): {latest['butterfly']:.3f} pp\n"
          "Nota: snapshot quantitativo; dados de yields isoladamente não comprovam causas macroeconômicas.")
    os.makedirs("pipelines/bonds",exist_ok=True)
    with open("pipelines/bonds/executive.txt","w",encoding="utf-8") as f:
        f.write(text)
    with open("pipelines/bonds/macro_context.txt","w",encoding="utf-8") as f:
        f.write(macro_context(metrics))
    print(macro_context(metrics))
    print(f"[PIPELINE] Analytics saved: {out}")
if __name__=="__main__": main()
