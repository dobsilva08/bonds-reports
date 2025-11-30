#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Plota Z-Score de cada vértice (rolling mean/std).
- Entrada: CSVs com yield_pct.
- Saída: pipelines/bonds/zscore_{window}d.png
"""
import argparse
import os
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
    df = df[["date","yield_pct"]].rename(columns={"yield_pct": name}).sort_values("date").reset_index(drop=True)
    return df, name

def main():
    p = argparse.ArgumentParser(description="Z-score (rolling) das yields")
    p.add_argument("--files", nargs="+", required=True)
    p.add_argument("--window", type=int, default=252, help="janela para média e std (default 252)")
    p.add_argument("--out", default=None)
    p.add_argument("--start", default=None)
    p.add_argument("--end", default=None)
    args = p.parse_args()

    dfs, names = [], []
    for f in args.files:
        if not os.path.exists(f):
            print("Warning:", f, "not found; skipping")
            continue
        df, name = read_series(f); dfs.append(df); names.append(name)
    if not dfs:
        raise RuntimeError("Nenhum arquivo válido")

    merged = dfs[0]
    for df in dfs[1:]:
        merged = pd.merge(merged, df, on="date", how="outer")
    merged = merged.sort_values("date").reset_index(drop=True)

    if args.start:
        merged = merged[merged["date"] >= pd.to_datetime(args.start)]
    if args.end:
        merged = merged[merged["date"] <= pd.to_datetime(args.end)]

    cols = [c for c in merged.columns if c != "date"]
    for c in cols:
        rolling_mean = merged[c].rolling(window=args.window, min_periods=1).mean()
        rolling_std = merged[c].rolling(window=args.window, min_periods=1).std()
        merged[f"{c}_z"] = (merged[c] - rolling_mean) / rolling_std

    zcols = [c for c in merged.columns if c.endswith("_z")]

    # plot subplots
    n = len(zcols)
    fig, axes = plt.subplots(nrows=n, ncols=1, figsize=(12, 3.5*n), sharex=True)
    if n == 1: axes = [axes]
    for i, zc in enumerate(zcols):
        ax = axes[i]
        name = zc.replace("_z","")
        ax.plot(merged["date"], merged[zc], label=f"Z-score {name}")
        ax.axhline(0, linestyle=":", linewidth=0.8)
        ax.axhline(2, linestyle="--", linewidth=0.6)
        ax.axhline(-2, linestyle="--", linewidth=0.6)
        ax.set_ylabel("Z")
        ax.grid(True)
        ax.legend(loc="upper left")
    axes[-1].set_xlabel("Data")

    out = args.out or f"pipelines/bonds/zscore_{args.window}d.png"
    os.makedirs(os.path.dirname(out), exist_ok=True)
    plt.tight_layout()
    plt.savefig(out, dpi=150)
    plt.close()
    print("Saved:", out)
    print("Period:", merged['date'].min().date(), "→", merged['date'].max().date())

if __name__ == "__main__":
    main()
