"""Shared validation helpers for Treasury yield CSV data."""
from pathlib import Path
import pandas as pd

REQUIRED = {"date", "yield_pct"}

def validate_frame(df: pd.DataFrame, series: str, min_rows: int = 2) -> pd.DataFrame:
    missing = REQUIRED - set(df.columns)
    if missing:
        raise ValueError(f"{series}: missing columns: {sorted(missing)}")
    out = df.copy()
    out["date"] = pd.to_datetime(out["date"], errors="coerce")
    out["yield_pct"] = pd.to_numeric(out["yield_pct"], errors="coerce")
    out = out.dropna(subset=["date", "yield_pct"]).sort_values("date")
    if out["date"].duplicated().any():
        raise ValueError(f"{series}: duplicate dates detected")
    if len(out) < min_rows:
        raise ValueError(f"{series}: insufficient valid observations ({len(out)})")
    if not out["yield_pct"].between(-1, 25).all():
        raise ValueError(f"{series}: yield values outside sanity range")
    if out["date"].max().date() > pd.Timestamp.utcnow().date():
        raise ValueError(f"{series}: future observation detected")
    age = (pd.Timestamp.utcnow().normalize() - out["date"].max().normalize()).days
    if age > 10:
        raise ValueError(f"{series}: stale observation ({age} calendar days)")
    return out.reset_index(drop=True)

def validate_csv(path, series):
    p = Path(path)
    if not p.exists() or p.stat().st_size == 0:
        raise FileNotFoundError(f"{series}: output missing or empty: {p}")
    return validate_frame(pd.read_csv(p), series)
