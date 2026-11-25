"""Unified data/analytics pipeline entry point."""
import os
from scripts.bonds.data_engine import collect_all
from scripts.bonds.analytics_engine import curve_metrics
from scripts.bonds.macro_engine import macro_context
from scripts.bonds.report_engine import build_daily_report

def main():
    data=collect_all(start=os.getenv("BONDS_START_DATE","2000-01-01"))
    metrics=curve_metrics(data)
    out="pipelines/bonds/analytics.csv"
    os.makedirs("pipelines/bonds",exist_ok=True)
    metrics.to_csv(out,index=False)
    report=build_daily_report(metrics)
    with open("pipelines/bonds/executive.txt","w",encoding="utf-8") as f:
        f.write(report)
    with open("pipelines/bonds/macro_context.txt","w",encoding="utf-8") as f:
        f.write(macro_context(metrics))
    print(macro_context(metrics))
    print(f"[PIPELINE] Analytics saved: {out}")
if __name__=="__main__": main()
