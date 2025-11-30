#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Plota spreads da curva (10y-2y, 30y-2y, 30y-10y) para os últimos 12 meses,
com áreas sombreadas quando houver inversão.
Funciona com colunas DGS2 / DGS10 / DGS30 ou qualquer nome contendo 2 / 10 / 30.
"""

import argparse
import os
from datetime import datetime, timedelta
import pandas as pd
import matplotlib.pyplot as plt

def read_df(path):
    df = pd.read_csv(path, parse_dates=["date"])
    df = df.sort_values("date").reset_index(drop=True)

    # detectar coluna yield_pct automaticamente
    col = None
    for c in df.columns:
        if c.lower() in ["yield", "yield_pct"]:
            col = c
            break
    if col is None:
        # fallback: segunda coluna
        col = df.columns[1]

    asset = os.path.basename(path).replace(".csv", "")
    df = df[["date", col]].rename(columns={col: asset})
    return df, asset

def detect_col(cols, patterns):
    """Retorna nome da coluna que contém qualquer padrão"""
    for p in patterns:
        for c in cols:
            if p.lower() in c.lower():
                return c
    return None

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--files", nargs=3, required=True)
    parser.add_argument("--window", type=int, default=20)
    parser.add_argument("--ema", action="store_true")
    parser.add_argument("--out", default="pipelines/bonds/spreads_12m.png")
    args = parser.parse_args()

    # ler arquivos
    dfs = []
    for f in args.files:
        df, name = read_df(f)
        dfs.append(df)

    # merge
    merged = dfs[0]
    for df in dfs[1:]:
        merged = pd.merge(merged, df, on="date", how="outer")

    merged = merged.sort_values("date").reset_index(drop=True)

    # --- detectar colunas reais automaticamente ---
    cols = [c for c in merged.columns if c != "date"]

    col_2y  = detect_col(cols, ["2", "2y", "02", "dgs2", "us2"])
    col_10y = detect_col(cols, ["10", "10y", "dgs10", "us10"])
    col_30y = detect_col(cols, ["30", "30y", "dgs30", "us30"])

    if not (col_2y and col_10y and col_30y):
        raise RuntimeError(f"Colunas não encontradas. Detectado: {cols}")

    print(f"Detectado 2Y  → {col_2y}")
    print(f"Detectado 10Y → {col_10y}")
    print(f"Detectado 30Y → {col_30y}")

    merged = merged[["date", col_2y, col_10y, col_30y]]
    merged.columns = ["date", "US2Y", "US10Y", "US30Y"]

    # --- FILTRO 12 MESES ---
    cutoff = datetime.utcnow().date() - timedelta(days=365)
    merged = merged[merged["date"] >= pd.to_datetime(cutoff)]

    # spreads
    merged["S_10_2"] = merged["US10Y"] - merged["US2Y"]
    merged["S_30_2"] = merged["US30Y"] - merged["US2Y"]
    merged["S_30_10"] = merged["US30Y"] - merged["US10Y"]

    # média móvel
    def smooth(x):
        return x.ewm(span=args.window, adjust=False).mean() if args.ema else x.rolling(args.window, min_periods=1).mean()

    for s in ["S_10_2", "S_30_2", "S_30_10"]:
        merged[f"{s}_MA"] = smooth(merged[s])

    # plot
    fig, axes = plt.subplots(3, 1, figsize=(12, 11), sharex=True)
    spreads = ["S_10_2", "S_30_2", "S_30_10"]

    for ax, s in zip(axes, spreads):
        ax.plot(merged["date"], merged[s], label=s, linewidth=1.2)
        ax.plot(merged["date"], merged[f"{s}_MA"], label=f"{s} MA{args.window}", linestyle="--")

        # inversão
        neg = merged[s] < 0
        if neg.any():
            merged["flag"] = neg.astype(int)
            merged["shift"] = merged["flag"].diff().fillna(0)

            starts = merged[merged["shift"] == 1].index.tolist()
            ends = merged[merged["shift"] == -1].index.tolist()

            if neg.iloc[0]:
                starts = [0] + starts
            if neg.iloc[-1]:
                ends = ends + [len(merged) - 1]

            for st, ed in zip(starts, ends):
                ax.axvspan(merged.loc[st, "date"], merged.loc[ed, "date"], color="gray", alpha=0.15)

        ax.axhline(0, linestyle=":", linewidth=0.7)
        ax.grid(True)
        ax.legend()

    axes[-1].set_xlabel("Data")
    plt.suptitle("Spreads — Últimos 12 Meses (inversões sombreadas)")
    plt.tight_layout(rect=[0,0,1,0.96])

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    plt.savefig(args.out, dpi=150)
    plt.close(fig)
    print(f"OK → {args.out}")

if __name__ == "__main__":
    main()
