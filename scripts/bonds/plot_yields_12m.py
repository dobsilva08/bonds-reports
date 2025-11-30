#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Convenience: plota últimos 12 meses para US2Y, US10Y, US30Y.
Internamente usa os mesmos parâmetros do plot_yields_separate.
"""
import argparse
import os
from datetime import datetime, timedelta
import pandas as pd
import matplotlib.pyplot as plt

# reuse logic similar to plot_yields_separate but simplified:
def read_series(path: str):
    df = pd.read_csv(path, parse_dates=["date"])
    if "yield_pct" not in df.columns:
        raise RuntimeError(f"Arquivo {path} não contém coluna 'yield_pct'.")
    name = None
    if "source" in df.columns and df["source"].notnull().any():
        src = df.loc[df["source"].first_valid_index(), "source"]
        name = src.split(":")[-1] if isinstance(src, str) and ":" in src else str(src)
    if not name:
        name = os.path.splitext(os.path.basename(path))[0]
    df = df[["date", "yield_pct"]].copy().sort_values("date").reset_index(drop=True)
    df.rename(columns={"yield_pct": name}, inplace=True)
    return df, name

def main():
    parser = argparse.ArgumentParser(description="Plota últimos 12 meses (convenience wrapper).")
    parser.add_argument("--files", nargs="+", required=True, help="CSV(s) de entrada")
    parser.add_argument("--window", type=int, default=20)
    parser.add_argument("--ema", action="store_true")
    parser.add_argument("--out", default="pipelines/bonds/yields_12m.png")
    args = parser.parse_args()

    # build merged
    dfs, names = [], []
    for f in args.files:
        if not os.path.exists(f):
            print(f"Warning: {f} not found; skipping")
            continue
        df, name = read_series(f)
        dfs.append(df); names.append(name)
    if not dfs:
        raise RuntimeError("Nenhum arquivo válido")

    merged = dfs[0]
    for df in dfs[1:]:
        merged = pd.merge(merged, df, on="date", how="outer")
    merged = merged.sort_values("date").reset_index(drop=True)

    cutoff = datetime.utcnow().date() - timedelta(days=365)
    merged = merged[merged["date"] >= pd.to_datetime(cutoff)]
    if merged.empty:
        raise RuntimeError("Nenhum dado nos últimos 12 meses.")

    # plotting using same style as plot_yields_separate
    cols = [c for c in merged.columns if c != "date"]
    n = len(cols)
    fig, axes = plt.subplots(nrows=n, ncols=1, figsize=(12, 4*n), sharex=True)
    if n == 1: axes = [axes]

    for i, col in enumerate(cols):
        ax = axes[i]
        s = merged[["date", col]].dropna()
        if s.empty:
            continue
        ax.plot(s["date"], s[col], label=f"{col} (yield)")
        ma = s[col].ewm(span=args.window, adjust=False, min_periods=1).mean() if args.ema else s[col].rolling(window=args.window, min_periods=1).mean()
        ax.plot(s["date"], ma, linestyle="--", label=f"MA{args.window}")
        ax.set_title(f"{col} — Últimos 12 meses (MA{args.window})")
        ax.set_ylabel("Yield (%)")
        ax.grid(True)
        ax.legend(loc="upper left")

    axes[-1].set_xlabel("Data")
    out_path = os.path.abspath(args.out)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()
    print(f"Gráfico 12M salvo em: {out_path}")
    print("Período:", merged["date"].min().date(), "→", merged["date"].max().date())

if __name__ == "__main__":
    main()
