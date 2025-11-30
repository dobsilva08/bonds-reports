#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Heatmap compacto da curva 2Y–30Y (tempo x maturidade)
Feito para visualização no Telegram (altura reduzida).
"""

import argparse
import os
from datetime import datetime
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

def read_df(path):
    df = pd.read_csv(path, parse_dates=["date"])
    df = df.sort_values("date")
    # detect yield col
    ycol = None
    for c in df.columns:
        if c.lower() in ("yield", "yield_pct"):
            ycol = c
            break
    if ycol is None:
        ycol = df.columns[1]
    name = os.path.splitext(os.path.basename(path))[0]
    return df[["date", ycol]].rename(columns={ycol: name})

def detect(cols, patterns):
    for p in patterns:
        for c in cols:
            if p.lower() in c.lower():
                return c
    return None

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--files", nargs=3, required=True)
    parser.add_argument("--out", default="pipelines/bonds/curve_heatmap.png")
    parser.add_argument("--cmap", default="cividis")
    args = parser.parse_args()

    dfs = []
    for f in args.files:
        dfs.append(read_df(f))

    merged = dfs[0]
    for df in dfs[1:]:
        merged = pd.merge(merged, df, on="date", how="outer")

    merged = merged.sort_values("date").reset_index(drop=True)

    cols = [c for c in merged.columns if c != "date"]

    c2  = detect(cols, ["2", "2y", "dgs2"])
    c10 = detect(cols, ["10", "10y", "dgs10"])
    c30 = detect(cols, ["30", "30y", "dgs30"])

    if not(c2 and c10 and c30):
        raise RuntimeError("Não encontrou colunas 2y/10y/30y.")

    merged = merged[["date", c2, c10, c30]]
    merged.columns = ["date", "US2Y", "US10Y", "US30Y"]

    # RESAMPLE MENSAL → evita gráfico gigante
    df = merged.set_index("date").resample("MS").mean().interpolate()

    maturities = np.arange(2, 31, 1)
    base_mats = np.array([2, 10, 30])
    base_vals = df[["US2Y", "US10Y", "US30Y"]].to_numpy()

    grid = np.zeros((len(df), len(maturities)))

    for i in range(len(df)):
        row = base_vals[i]
        row = np.nan_to_num(row, nan=np.nanmean(row))
        grid[i] = np.interp(maturities, base_mats, row)

    dates = df.index

    # Figura mais curta e larga → ótimo no Telegram
    fig_h = max(4, len(df) * 0.08)  # altura proporcional mas menor
    fig_w = 12

    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    im = ax.imshow(
        grid,
        aspect="auto",
        origin="lower",
        cmap=args.cmap,
        extent=[maturities[0], maturities[-1], 0, len(df)]
    )

    # Ticks anuais
    years = sorted(set([d.year for d in dates]))
    year_idx = [i for i, d in enumerate(dates) if d.month == 1]
    ax.set_yticks(year_idx)
    ax.set_yticklabels([dates[i].strftime("%Y") for i in year_idx])

    ax.set_xlabel("Maturidade (anos)")
    ax.set_ylabel("Ano")
    ax.set_title("Heatmap da Curva 2Y–30Y (compacto)")

    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label("Yield (%)")

    plt.tight_layout()
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    fig.savefig(args.out, dpi=150)
    plt.close(fig)

    print(f"[OK] Heatmap compacto salvo em {args.out}")

if __name__ == "__main__":
    main()
