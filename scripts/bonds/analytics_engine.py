"""Reusable Treasury curve analytics."""
import pandas as pd

def curve_metrics(data):
    frame=data.copy()
    for name, df in frame.items():
        if "yield_pct" not in df.columns: raise ValueError(f"{name}: yield_pct missing")
    merged=None
    for name, df in frame.items():
        x=df[["date","yield_pct"]].copy()
        x["date"]=pd.to_datetime(x["date"])
        x=x.rename(columns={"yield_pct":name})
        merged=x if merged is None else merged.merge(x,on="date",how="inner")
    required=["US2Y","US10Y","US30Y"]
    if not all(c in merged.columns for c in required): raise ValueError("Need US2Y, US10Y, US30Y")
    merged["10Y-2Y"]=merged["US10Y"]-merged["US2Y"]
    merged["30Y-10Y"]=merged["US30Y"]-merged["US10Y"]
    merged["30Y-2Y"]=merged["US30Y"]-merged["US2Y"]
    merged["butterfly"]=merged["US30Y"]-2*merged["US10Y"]+merged["US2Y"]
    for col in required:
        merged[f"{col}_daily_bps"]=merged[col].diff()*100
        merged[f"{col}_vol30_bps"]=merged[f"{col}_daily_bps"].rolling(30,min_periods=10).std()
        rolling=merged[col].rolling(252,min_periods=60)
        merged[f"{col}_z252"]=(merged[col]-rolling.mean())/rolling.std()
    return merged.sort_values("date").reset_index(drop=True)
