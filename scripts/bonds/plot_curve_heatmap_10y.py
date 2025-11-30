#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Heatmap compacto — Últimos 10 anos (alto contraste) — otimizado para Telegram/mobile.

Salve como: scripts/bonds/plot_curve_heatmap_10y.py

Uso:
  python scripts/bonds/plot_curve_heatmap_10y.py \
    --files pipelines/bonds/us2y_daily.csv pipelines/bonds/us10y_daily.csv pipelines/bonds/us30y_daily.csv \
    --out pipelines/bonds/curve_heatmap_10y.png
"""
from __future__ import annotations
import argparse
import os
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import requests
import warnings

warnings.filterwarnings("ignore", category=UserWarning)

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
        # fallback: first non-date column
        for c in df.columns:
            if c.lower() != "date":
                ycol = c
                break
    if ycol is None:
        raise RuntimeError(f"Não encontrou coluna de yield em {path}")
    name = os.path.splitext(os.path.basename(path))[0]
    return df[["date", ycol]].rename(columns={ycol: name})

def detect_col_name(cols):
    def find(patterns):
        for p in patterns:
            for c in cols:
                if p.lower() in c.lower():
                    return c
        return None
    return {
        "2": find(["2y","dgs2","2","us2"]),
        "10": find(["10y","dgs10","10","us10"]),
        "30": find(["30y","dgs30","30","us30"]),
    }

def fetch_nber_from_fred(api_key: str):
    """Retorna lista de (start_date, end_date) de recessões a partir da série USREC no FRED (opcional)."""
    if not api_key:
        return []
    try:
        url = "https://api.stlouisfed.org/fred/series/observations"
        params = {"series_id": "USREC", "api_key": api_key, "file_type": "json"}
        r = requests.get(url, params=params, timeout=15)
        r.raise_for_status()
        obs = r.json().get("observations", [])
        recs = []
        cur_start = None
        for o in obs:
            dt = pd.to_datetime(o["date"]).date()
            val = o.get("value")
            if val in ("1","1.0",1,1.0):
                if cur_start is None:
                    cur_start = dt
            else:
                if cur_start is not None:
                    recs.append((cur_start, (dt - pd.Timedelta(days=1)).date()))
                    cur_start = None
        if cur_start is not None:
            recs.append((cur_start, pd.to_datetime(obs[-1]["date"]).date()))
        return recs
    except Exception:
        return []

def fallback_recessions():
    # fallback útil para últimos 10 anos (apenas COVID em 2020)
    return [(datetime(2020,2,1).date(), datetime(2020,4,30).date())]

def build_grid(df_monthly: pd.DataFrame, maturities: np.ndarray) -> np.ndarray:
    known_mats = np.array([2.0, 10.0, 30.0])
    vals = df_monthly[["US2Y","US10Y","US30Y"]].to_numpy()
    grid = np.empty((vals.shape[0], len(maturities)))
    for i, row in enumerate(vals):
        row = np.nan_to_num(row, nan=np.nanmean(row))
        grid[i,:] = np.interp(maturities, known_mats, row)
    return grid

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--files", nargs=3, required=True, help="CSV 2Y 10Y 30Y (qualquer ordem)")
    parser.add_argument("--out", default="pipelines/bonds/curve_heatmap_10y.png")
    parser.add_argument("--cmap", default="plasma", help="Colormap (default: plasma)")
    parser.add_argument("--mmin", type=int, default=2)
    parser.add_argument("--mmax", type=int, default=30)
    parser.add_argument("--mstep", type=float, default=1.0)
    parser.add_argument("--fred-api-key", default=os.getenv("FRED_API_KEY"))
    args = parser.parse_args()

    # read
    dfs = [read_series(p) for p in args.files]
    merged = dfs[0]
    for d in dfs[1:]:
        merged = pd.merge(merged, d, on="date", how="outer")
    merged = merged.sort_values("date").reset_index(drop=True)

    # detect and rename to US2Y, US10Y, US30Y
    cols = [c for c in merged.columns if c != "date"]
    mapping = detect_col_name(cols)
    if not (mapping["2"] and mapping["10"] and mapping["30"]):
        raise RuntimeError(f"Não foi possível mapear colunas automaticamente (detectadas: {cols})")
    merged = merged[["date", mapping["2"], mapping["10"], mapping["30"]]].rename(
        columns={mapping["2"]: "US2Y", mapping["10"]: "US10Y", mapping["30"]: "US30Y"}
    )

    # --- FILTRO últimos 10 anos ---
    end_date = pd.to_datetime(datetime.utcnow().date())
    start_date = end_date - pd.DateOffset(years=10)
    merged = merged[(merged["date"] >= start_date) & (merged["date"] <= end_date)].copy()
    if merged.empty:
        raise RuntimeError("Nenhum dado nos últimos 10 anos após filtro.")

    # RESAMPLE MENSAL (MS) e interpolação
    dfm = merged.set_index("date").resample("MS").mean().interpolate()

    # maturities e grid
    maturities = np.arange(args.mmin, args.mmax + 1e-9, args.mstep)
    grid = build_grid(dfm, maturities)

    # spread 10y-2y para sinal de inversão
    spread = (dfm["US10Y"] - dfm["US2Y"]).to_numpy()

    # recessões: tentar FRED, senão fallback
    recs = fetch_nber_from_fred(args.fred_api_key)
    if not recs:
        recs = fallback_recessions()

    # --- PLOT otimizado para Telegram ---
    dates = dfm.index.to_pydatetime()
    T = len(dates)
    W = len(maturities)

    # figura fixa: largura 10, altura 8 (solicitado)
    fig_w, fig_h = 10, 8
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))

    # imshow com interpolation='nearest' para manter linhas nítidas
    im = ax.imshow(grid, aspect="auto", origin="lower", cmap=args.cmap,
                   interpolation="nearest", extent=[maturities[0], maturities[-1], 0, T])

    # ticks: anos grandes e legíveis
    years = sorted(set([d.year for d in dates]))
    # pick positions where month==1 (jan) within the period
    year_positions = [i for i, d in enumerate(dates) if d.month == 1]
    # ensure we have tick labels; if too many, sample
    if len(year_positions) > 8:
        step = max(1, len(year_positions)//8)
        year_positions = year_positions[::step]
    year_labels = [dates[i].strftime("%Y") for i in year_positions]
    ax.set_yticks(year_positions)
    ax.set_yticklabels(year_labels, fontsize=12)

    # Maturities x ticks
    ax.set_xticks(maturities[::2])  # every 2 years for readability
    ax.set_xticklabels([str(int(x)) for x in maturities[::2]], fontsize=12)
    ax.set_xlabel("Maturidade (anos)", fontsize=13)
    ax.set_ylabel("Ano", fontsize=13)
    ax.set_title("Curva 2Y→30Y — Últimos 10 anos (Heatmap) — legível para celular", fontsize=14)

    # colorbar slim
    cbar = fig.colorbar(im, ax=ax, fraction=0.035, pad=0.02)
    cbar.ax.tick_params(labelsize=11)
    cbar.set_label("Yield (%)", fontsize=12)

    # recessions: shade thin horizontal bands (transparent)
    for start, end in recs:
        # limit to our displayed date window
        s = max(start, dates[0].date())
        e = min(end, dates[-1].date())
        if s > e:
            continue
        # find indices
        idx_s = next((i for i, d in enumerate(dates) if d.date() >= s), 0)
        idx_e = next((i for i, d in enumerate(dates) if d.date() > e), len(dates)-1)
        ax.axhspan(idx_s, idx_e, color='grey', alpha=0.12, zorder=2)

    # inversions: draw thin red horizontal lines for months where spread<0
    for i, val in enumerate(spread):
        if np.isnan(val):
            continue
        if val < 0:
            ax.hlines(i + 0.5, xmin=maturities[0], xmax=maturities[-1], colors='red', linewidth=0.9, alpha=0.9, zorder=3)

    # aesthetic tweaks
    ax.invert_yaxis()  # optional: put most recent at top — comment if prefer oldest on top
    ax.set_ylim(T, 0)  # ensure invert_yaxis mapping
    plt.tight_layout()

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    fig.savefig(args.out, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"[OK] Heatmap 10y salvo em {args.out}")

if __name__ == "__main__":
    main()
