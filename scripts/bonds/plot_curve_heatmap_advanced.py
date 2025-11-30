#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Heatmap avançado da curva 2Y-30Y com:
 - destaque de inversões (área vermelha onde 10y-2y < 0)
 - faixas de recessão (NBER) (tenta buscar USREC no FRED se FRED_API_KEY presente)
 - marcadores macro (FOMC, 2008, Covid) (lista embutida, extensível)

Saída padrão: pipelines/bonds/curve_heatmap_advanced.png
"""

from __future__ import annotations
import os
import argparse
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# Optional: fetch USREC series from FRED if API key available (no external web.run here)
import requests

def read_series(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["date"])
    df = df.sort_values("date").reset_index(drop=True)
    # detect yield column
    ycol = None
    for c in df.columns:
        if c.lower() in ("yield", "yield_pct"):
            ycol = c
            break
    if ycol is None:
        # fallback to second column
        ycol = df.columns[1]
    name = os.path.splitext(os.path.basename(path))[0]
    return df[["date", ycol]].rename(columns={ycol: name})

def detect_cols(cols):
    def find(patterns):
        for p in patterns:
            for c in cols:
                if p.lower() in c.lower():
                    return c
        return None
    return {
        "2": find(["2y", "dgs2", "2", "us2"]),
        "10": find(["10y", "dgs10", "10", "us10"]),
        "30": find(["30y", "dgs30", "30", "us30"]),
    }

def get_nber_recessions_from_fred(api_key: str):
    # fetch USREC series (0/1) from FRED to identify recession spans
    base = "https://api.stlouisfed.org/fred/series/observations"
    params = {"series_id": "USREC", "api_key": api_key, "file_type": "json"}
    try:
        r = requests.get(base, params=params, timeout=20)
        r.raise_for_status()
        obs = r.json().get("observations", [])
        rec_periods = []
        current_start = None
        for o in obs:
            date = pd.to_datetime(o["date"])
            val = o.get("value")
            if val in ("1","1.0",1,1.0):
                if current_start is None:
                    current_start = date
            else:
                if current_start is not None:
                    rec_periods.append((current_start.date(), (date - pd.Timedelta(days=1)).date()))
                    current_start = None
        if current_start is not None:
            rec_periods.append((current_start.date(), pd.to_datetime(obs[-1]["date"]).date()))
        return rec_periods
    except Exception:
        return None

def fallback_nber():
    # lista simples e histórica (até ~2023) — serve como fallback
    return [
        (datetime(2007,12,1).date(), datetime(2009,6,30).date()),   # GFC
        (datetime(2020,2,1).date(), datetime(2020,4,30).date()),    # COVID
    ]

def build_grid_interp(df_monthly, maturities):
    base_mats = np.array([2.0, 10.0, 30.0])
    values = df_monthly[["US2Y","US10Y","US30Y"]].to_numpy()
    grid = np.empty((values.shape[0], len(maturities)))
    for i, row in enumerate(values):
        row = np.nan_to_num(row, nan=np.nanmean(row))
        grid[i,:] = np.interp(maturities, base_mats, row)
    return grid

def compute_spread_10_2(df):
    # returns series indexed by date with 10y-2y
    return (df["US10Y"] - df["US2Y"])

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--files", nargs=3, required=True, help="CSV 2y 10y 30y")
    parser.add_argument("--out", default="pipelines/bonds/curve_heatmap_advanced.png")
    parser.add_argument("--cmap", default="cividis")
    parser.add_argument("--monthly", action="store_true", help="agrega mensal (default: True)")
    parser.add_argument("--fred-api-key", default=os.getenv("FRED_API_KEY"))
    args = parser.parse_args()

    dfs = [read_series(p) for p in args.files]
    merged = dfs[0]
    for df in dfs[1:]:
        merged = pd.merge(merged, df, on="date", how="outer")
    merged = merged.sort_values("date").reset_index(drop=True)

    cols = [c for c in merged.columns if c != "date"]
    mapping = detect_cols(cols)
    if not (mapping["2"] and mapping["10"] and mapping["30"]):
        raise RuntimeError(f"Não foi possível detectar colunas (encontradas: {cols})")
    merged = merged[["date", mapping["2"], mapping["10"], mapping["30"]]].rename(
        columns={mapping["2"]:"US2Y", mapping["10"]:"US10Y", mapping["30"]:"US30Y"}
    )

    # resample mensal por default
    dfm = merged.set_index("date").resample("MS").mean().interpolate()

    maturities = np.arange(2,31,1)
    grid = build_grid_interp(dfm, maturities)

    # spreads 10y-2y (monthly)
    spread = (dfm["US10Y"] - dfm["US2Y"]).reindex(dfm.index)

    # recessions
    recs = []
    if args.fred_api_key:
        recs = get_nber_recessions_from_fred(args.fred_api_key) or []
    if not recs:
        recs = fallback_nber()

    # macro events (list: (date, label))
    events = [
        (datetime(2008,9,15).date(), "Lehman"),
        (datetime(2020,3,11).date(), "WHO: COVID PN"),
        # Add FOMC meeting examples (replace with exact dates for your preference)
        (datetime(2020,3,15).date(), "FOMC emergency cut"),
        (datetime(2019,7,31).date(), "FOMC"),
    ]

    # plotting
    dates = dfm.index.to_pydatetime()
    fig_h = max(4, len(dates)*0.06)
    fig, ax = plt.subplots(figsize=(12, fig_h))
    im = ax.imshow(grid, origin="lower", aspect="auto", cmap=args.cmap,
                   extent=[maturities[0], maturities[-1], 0, len(dates)-1])

    # shade recession bands across entire maturity for rows that fall in recessions
    for start, end in recs:
        # find index positions in dates
        idx_start = 0
        idx_end = -1
        for i, d in enumerate(dates):
            if d.date() >= start:
                idx_start = i
                break
        for i, d in enumerate(dates):
            if d.date() > end:
                idx_end = i-1
                break
        if idx_end < 0:
            idx_end = len(dates)-1
        ax.axhspan(idx_start, idx_end, color='gray', alpha=0.10, zorder=1)

    # overlay inversion (10y-2y < 0) as translucent red overlay along rows where negative
    neg_mask = (spread < 0).to_numpy()
    for i, neg in enumerate(neg_mask):
        if neg:
            ax.axhspan(i, i+1, xmin=0, xmax=1, color='red', alpha=0.12)

    # macro event markers (vertical dashed line at approx time position)
    for ev_date, label in events:
        # find nearest index
        idx = min(range(len(dates)), key=lambda i: abs(dates[i].date() - ev_date))
        ax.plot([maturities[0], maturities[-1]], [idx+0.5, idx+0.5], linestyle='--', color='white', linewidth=0.8)
        ax.text(maturities[-1]+0.2, idx+0.5, label, va='center', fontsize=8, color='white', alpha=0.9)

    # Y ticks yearly
    year_idx = [i for i,d in enumerate(dates) if d.month==1]
    if len(year_idx) < 2:
        # fallback spread
        step = max(1, len(dates)//6)
        year_idx = list(range(0, len(dates), step))
    ax.set_yticks(year_idx)
    ax.set_yticklabels([dates[i].strftime("%Y") for i in year_idx])

    ax.set_xlabel("Maturidade (anos)")
    ax.set_ylabel("Ano")
    ax.set_title("Curva 2Y→30Y — Heatmap Avançado (inversões em vermelho; recessões cinza)")

    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label("Yield (%)")

    plt.tight_layout()
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    fig.savefig(args.out, dpi=150)
    plt.close(fig)
    print("[OK] heatmap avançado salvo em", args.out)

if __name__ == "__main__":
    main()
