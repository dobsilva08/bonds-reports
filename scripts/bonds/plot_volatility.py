#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Plota volatilidade realizada (rolling std) das yields.
- Calcula std dos delta diários (em bps) e opcionalmente anualiza (sqrt(252)).
- Entrada: 3 CSVs (us2y, us10y, us30y) ou qualquer conjunto contendo col 'yield_pct'.
- Saída PNG: pipelines/bonds/volatility_{window}d.png
"""
import argparse
import os
import pandas as pd
import matplotlib.pyplot as plt
from math import sqrt

def read_series(path):
    df = pd.read_csv(path, parse_dates=["date"])
    if "yield_pct" not in df.columns:
        raise RuntimeError(f"{path} must contain 'yield_pct'")
    # infer name
    name = None
    if "source" in df.columns and df["source"].notnull().any():
        s = df.loc[df["source"].first_valid_index(), "source"]
        name = s.split(":")[-1] if isinstance(s, str) and ":" in s else str(s)
    if not name:
        name = os.path.splitext(os.path.basename(path))[0]
    df = df[["date", "yield_pct"]].rename(columns={"yield_pct": name}).sort_values("date").reset_index(drop=True)
    return df, name

def main():
    p = argparse.ArgumentParser(description="Volatilidade realizada de yields (rolling std dos delta em bps)")
    p.add_argument("--files", nargs="+", required=True, help="CSV(s) de entrada (date,yield_pct,source)")
    p.add_argument("--window", type=int, default=30, help="janela em dias (default 30)")
    p.add_argument("--annualize", action="store_true", help="anualiza multiplicando por sqrt(252)")
    p.add_argument("--out", default=None, help="PNG de saída (opcional)")
    p.add_argument("--start", default=None)
    p.add_argument("--end", default=None)
    args = p.parse_args()

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

    if args.start:
        merged = merged[merged["date"] >= pd.to_datetime(args.start)]
    if args.end:
        merged = merged[merged["date"] <= pd.to_datetime(args.end)]

    # calc daily changes in bps (ppt * 100)
    for col in [c for c in merged.columns if c != "date"]:
        merged[f"{col}_delta_bps"] = merged[col].diff() * 100.0

    # rolling std
    for col in [c for c in merged.columns if c.endswith("_delta_bps")]:
        if args.annualize:
            merged[col.replace("_delta_bps","_vol")] = merged[col].rolling(window=args.window, min_periods=1).std() * sqrt(252)
        else:
            merged[col.replace("_delta_bps","_vol")] = merged[col].rolling(window=args.window, min_periods=1).std()

    vol_cols = [c for c in merged.columns if c.endswith("_vol")]

    # plot
    n = len(vol_cols)
    fig, axes = plt.subplots(nrows=n, ncols=1, figsize=(12, 3.5*n), sharex=True)
    if n == 1: axes = [axes]
    for i, vc in enumerate(vol_cols):
        ax = axes[i]
        label = vc.replace("_vol","")
        ax.plot(merged["date"], merged[vc], label=f"Vol {label} (window={args.window}d){' annualized' if args.annualize else ''}")
        ax.set_ylabel("bps" if not args.annualize else "bps (ann.)")
        ax.grid(True)
        ax.legend(loc="upper left")
    axes[-1].set_xlabel("Data")
    out = args.out or f"pipelines/bonds/volatility_{args.window}d.png"
    os.makedirs(os.path.dirname(out), exist_ok=True)
    plt.tight_layout()
    plt.savefig(out, dpi=150)
    plt.close()
    print("Saved:", out)
    print("Period:", merged['date'].min().date(), "→", merged['date'].max().date())

if __name__ == "__main__":
    main()
