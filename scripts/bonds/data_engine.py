"""Unified FRED collection and validation for Treasury yield series."""
import os
import requests
import pandas as pd
from scripts.bonds.validation import validate_frame

FRED_URL = "https://api.stlouisfed.org/fred/series/observations"
SERIES = {"US2Y":"DGS2", "US10Y":"DGS10", "US30Y":"DGS30"}

def fetch_series(series_id, start="2000-01-01", api_key=None):
    key = api_key or os.getenv("FRED_API_KEY")
    if not key:
        raise RuntimeError("FRED_API_KEY missing")
    response = requests.get(FRED_URL, params={
        "series_id":series_id, "api_key":key, "file_type":"json",
        "observation_start":start
    }, timeout=30)
    response.raise_for_status()
    observations = response.json().get("observations", [])
    rows=[]
    for item in observations:
        value=item.get("value")
        if value in (None, "", "."): continue
        rows.append({"date":item.get("date"),"yield_pct":float(value),"source":f"FRED:{series_id}"})
    return validate_frame(pd.DataFrame(rows), series_id)

def collect_all(start="2000-01-01", out_dir="pipelines/bonds"):
    os.makedirs(out_dir, exist_ok=True)
    result={}
    for name, sid in SERIES.items():
        df=fetch_series(sid,start)
        path=os.path.join(out_dir, f"{name.lower()}_daily.csv")
        df.to_csv(path,index=False)
        result[name]=df
        print(f"[DATA] {name}: {len(df)} rows; latest={df.date.max()}")
    return result
