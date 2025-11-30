#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Plot heatmap da curva 2Y-30Y ao longo do tempo (anos x maturidade).

Entrada:
  --files : CSVs (us2y, us10y, us30y) - ordem livre
Opções:
  --start / --end : filtrar período (YYYY-MM-DD)
  --monthly : agregação por mês (média) para reduzir resolução
  --mmin / --mmax / --mstep : maturidade mínima, máxima e step (em anos). Default 2..30 step 1
  --out : PNG de saída (default pipelines/bonds/curve_heatmap.png)
  --cmap : colormap matplotlib (default 'viridis')
  --dpi : DPI do PNG (default 150)

Exemplo:
  python scripts/bonds/plot_curve_heatmap.py \
    --files pipelines/bonds/us2y_daily.csv pipelines/bonds/us10y_daily.csv pipelines/bonds/us30y_daily.csv \
    --monthly --start 2015-01-01 --out pipelines/bonds/curve_heatmap.png
"""
from __future__ import annotations
import argparse
import os
from datetime import datetime
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

def read_series(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["date"])
    df = df.sort_values("date").reset_index(drop=True)

    # pick yield column (common names) or fallback to second column
    yield_col = None
    for c in df.columns:
        if c.lower() in ("yield", "yield_pct", "yield_pct"):
            yield_col = c
            break
    if yield_col is None:
        # fallback: any numeric column besides date
        for c in df.columns:
            if c.lower() != "date":
                yield_col = c
                break
    if yield_col is None:
        raise RuntimeError(f"Cannot find yield column in {path}")

    # asset name (try from source column or filename)
    name = None
    if "source" in df.columns and df["source"].notnull().any():
        s = df.loc[df["source"].first_valid_index(), "source"]
        if isinstance(s, str) and ":" in s:
            name = s.split(":")[-1]
        else:
            name = str(s)
    if not name:
        name = os.path.splitext(os.path.basename(path))[0]

    out = df[["date", yield_col]].rename(columns={yield_col: name})
    return out

def detect_cols(cols: list[str]) -> dict:
    # heuristics to map columns that include 2,10,30
    def find(patterns):
        for p in patterns:
            for c in cols:
                if p.lower() in c.lower():
                    return c
        return None
    return {
        "2": find(["2y","dgs2","2","02","us2"]),
        "10": find(["10y","dgs10","10","us10"]),
        "30": find(["30y","dgs30","30","us30"]),
    }

def build_grid(merged_df: pd.DataFrame, maturities: np.ndarray, monthly: bool=False) -> (np.ndarray, np.ndarray, np.ndarray):
    """
    Returns:
      dates (as pd.DatetimeIndex), maturities (np.array), grid (2D np.array shape (len(dates), len(maturities)))
    """
    df = merged_df.copy().set_index("date").sort_index()

    if monthly:
        # resample to month start frequency
        df = df.resample("MS").mean()

    dates = df.index.to_pydatetime()
    # if any NaNs, we can forward/backfill small gaps
    df = df.interpolate(method="time", limit_direction="both")
    # we have only columns for 2y/10y/30y; build interpolation function per date
    known_mats = np.array([2.0, 10.0, 30.0])
    values = df.to_numpy()  # shape (T, 3)

    grid = np.empty((values.shape[0], len(maturities)), dtype=float)
    for i, row in enumerate(values):
        # if row has NaN, use interpolation across time was done; final fallback: nan_to_num
        row = np.array(row, dtype=float)
        row = np.nan_to_num(row, nan=np.nanmean(row))
        # linear interpolation across the maturities
        grid[i, :] = np.interp(maturities, known_mats, row)
    return dates, maturities, grid

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--files", nargs=3, required=True, help="CSV us2y/us10y/us30y (any order)")
    parser.add_argument("--start", default=None)
    parser.add_argument("--end", default=None)
    parser.add_argument("--monthly", action="store_true", help="agrega por mês (média)")
    parser.add_argument("--mmin", type=float, default=2.0)
    parser.add_argument("--mmax", type=float, default=30.0)
    parser.add_argument("--mstep", type=float, default=1.0)
    parser.add_argument("--out", default="pipelines/bonds/curve_heatmap.png")
    parser.add_argument("--cmap", default="viridis")
    parser.add_argument("--dpi", type=int, default=150)
    args = parser.parse_args()

    # read and merge
    dfs = []
    for p in args.files:
        if not os.path.exists(p):
            raise RuntimeError(f"File not found: {p}")
        dfs.append(read_series(p))

    merged = dfs[0]
    for df in dfs[1:]:
        merged = pd.merge(merged, df, on="date", how="outer")

    merged = merged.sort_values("date").reset_index(drop=True)

    # detect which columns correspond to 2/10/30
    cols = [c for c in merged.columns if c != "date"]
    mapping = detect_cols(cols)
    if not (mapping["2"] and mapping["10"] and mapping["30"]):
        raise RuntimeError(f"Não foi possível mapear colunas automaticamente. Detectadas: {cols}")

    # keep only date and the three cols, rename for convenience
    merged = merged[["date", mapping["2"], mapping["10"], mapping["30"]]].rename(
        columns={mapping["2"]: "DGS2", mapping["10"]: "DGS10", mapping["30"]: "DGS30"}
    )

    if args.start:
        merged = merged[merged["date"] >= pd.to_datetime(args.start)]
    if args.end:
        merged = merged[merged["date"] <= pd.to_datetime(args.end)]

    if merged.empty:
        raise RuntimeError("Nenhum dado após filtro de datas.")

    # define maturities grid and build interpolation grid
    maturities = np.arange(args.mmin, args.mmax + 1e-9, args.mstep)
    dates, mats, grid = build_grid(merged, maturities, monthly=args.monthly)

    # plot heatmap
    fig, ax = plt.subplots(figsize=(12, max(6, len(dates) * 0.12)))
    # imshow expects (rows=time, cols=maturities)
    im = ax.imshow(grid, aspect="auto", origin="lower", cmap=args.cmap,
                   extent=[maturities[0], maturities[-1], 0, len(dates)-1])

    # y ticks: choose reasonable number of date ticks
    nticks = 8
    yt_idxs = np.linspace(0, len(dates)-1, min(len(dates), nticks)).astype(int)
    ytick_labels = [dates[i].strftime("%Y-%m-%d") for i in yt_idxs]
    ax.set_yticks(yt_idxs)
    ax.set_yticklabels(ytick_labels)
    ax.set_xlabel("Maturidade (anos)")
    ax.set_ylabel("Data")
    ax.set_title("Curva de Yields (2Y→30Y) — Heatmap (tempo x maturidade)")

    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label("Yield (%)")

    plt.tight_layout()
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    fig.savefig(args.out, dpi=args.dpi)
    plt.close(fig)
    print(f"[OK] Heatmap salvo em {args.out}")
    print("Período:", dates[0].strftime("%Y-%m-%d"), "→", dates[-1].strftime("%Y-%m-%d"))
    print("Maturidades:", maturities[0], "→", maturities[-1], "step", args.mstep)

if __name__ == "__main__":
    main()
