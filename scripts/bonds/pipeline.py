"""Unified data/analytics pipeline entry point. Does not send LLM reports."""
import os
from scripts.bonds.data_engine import collect_all
from scripts.bonds.analytics_engine import curve_metrics
from scripts.bonds.macro_engine import macro_context

def main():
    data=collect_all(start=os.getenv("BONDS_START_DATE","2000-01-01"))
    metrics=curve_metrics(data)
    out="pipelines/bonds/analytics.csv"
    metrics.to_csv(out,index=False)
    print(macro_context(metrics))
    print(f"[PIPELINE] Analytics saved: {out}")
if __name__=="__main__": main()
