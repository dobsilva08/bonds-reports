#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Plota spreads (10y-2y, 30y-2y, 30y-10y) limitados aos últimos 12 meses,
incluindo áreas sombreadas quando há inversão.

Uso:
  python scripts/bonds/plot_spreads_12m.py \
    --files pipelines/bonds/us2y_daily.csv pipelines/bonds/us10y_daily.csv pipelines/bonds/us30y_daily.csv \
    --window 20 \
    --ema \
    --out pipelines/bonds/spreads_12m.png
"""

import argparse
import os
from datetime import datetime, timedelta
import pandas as pd
import matplotlib.pyplot as plt

def read_series(path):
    df = pd.read_csv(path, parse_dates=["date"])
    if "yield_pct" not in df.columns:
        raise RuntimeError(f"{path} missing yield_pct")
    name = None
    if "source" in df.columns and df["source"].notnull().any():
        s = df.loc[df["source"].first_valid_index(), "source"]
        name = s.split(":")[-1] if isinstance(s, str) and ":" in s else str(s)
    if not name:
        name = os.path.splitext(os.path.basename(path))[0]
    df = df[["date", "yield_pct"]].rename(columns={"yield_pct": name})
    return df.sort_values("date").reset_index(drop=True), name

def moving(series, window, ema=False):
    if ema:
        return series.ewm(span=window, adjust=False, min_periods=1).mean()
    return series.rolling(window=window, min_periods=1).mean()

def main():
    parser = argparse.ArgumentParser(description="Plot spreads últimos 12 meses")
    parser.add_argument("--files", nargs=3, required=True, help="CSV 2Y, 10Y, 30Y")
    parser.add_argument("--window", type=int, default=20)
    parser.add_argument("--ema", action="store_true")
    parser.add_argument("--out", default="pipelines/bonds/spreads_12m.png")
    args = parser.parse_args()

    dfs = []
    for f in args.files:
        df, _ = read_series(f)
        dfs.append(df)

    # merge
    merged = dfs[0]
    for df in dfs[1:]:
        merged = pd.merge(merged, df, on="date", how="outer")

    merged = merged.sort_values("date").reset_index(drop=True)

    # Identificar colunas por nome
    cols = [c for c in merged.columns if c != "date"]
    mapping = {}

    def map_key(keys):
        for k in keys:
            for c in cols:
                if k.lower() in c.lower():
                    return c
        return None

    mapping["US2Y"] = map_key(["2", "2y", "dgs2"])
    mapping["US10Y"] = map_key(["10", "10y", "dgs10"])
    mapping["US30Y"] = map_key(["30", "30y", "dgs30"])

    if None in mapping.values():
        raise RuntimeError(f"Não foi possível mapear colunas automaticamente: {mapping}")

    merged = merged.rename(columns=mapping)[["date", "US2Y", "US10Y", "US30Y"]]

    # --- FILTRAR ÚLTIMOS 12 MESES ---
    cutoff = datetime.utcnow().date() - timedelta(days=365)
    merged = merged[merged["date"] >= pd.to_datetime(cutoff)]

    if merged.empty:
        raise RuntimeError("Nenhum dado disponível nos últimos 12 meses.")

    # spreads
    merged["S_10_2"] = merged["US10Y"] - merged["US2Y"]
    merged["S_30_2"] = merged["US30Y"] - merged["US2Y"]
    merged["S_30_10"] = merged["US30Y"] - merged["US10Y"]

    # suavização
    for s in ["S_10_2", "S_30_2", "S_30_10"]:
        merged[f"{s}_MA"] = moving(merged[s], args.window, ema=args.ema)

    # plot
    spreads = ["S_10_2", "S_30_2", "S_30_10"]
    fig, axes = plt.subplots(3, 1, figsize=(12, 11), sharex=True)

    for ax, s in zip(axes, spreads):
        ax.plot(merged["date"], merged[s], label=s, linewidth=1.2)
        ax.plot(merged["date"], merged[f"{s}_MA"], label=f"{s} MA{args.window}", linestyle="--")

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

            merged.drop(columns=["flag", "shift"], inplace=True, errors=True)

        ax.axhline(0, linestyle=":", linewidth=0.8)
        ax.grid(True)
        ax.legend(loc="upper left")
        ax.set_ylabel("Spread (pp)")

    axes[-1].set_xlabel("Data")
    plt.suptitle("Spreads da Curva — Últimos 12 Meses (inversões sombreadas)")
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    plt.savefig(args.out, dpi=150)
    plt.close(fig)

    print(f"[OK] spreads_12m salvo em {args.out}")

if __name__ == "__main__":
    main()
