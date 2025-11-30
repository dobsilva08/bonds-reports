#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Plota butterfly da curva:
BUTTERFLY = US30Y - 2*US10Y + US2Y
- Entrada: cs vs
- Saída: pipelines/bonds/butterfly.png
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
    p = argparse.ArgumentParser(description="Plot butterfly = 30Y - 2*10Y + 2Y")
    p.add_argument("--files", nargs=3, required=True, help="CSV: us2y us10y us30y (any order)")
    p.add_argument("--window", type=int, default=20, help="MA window for smoothing")
    p.add_argument("--out", default="pipelines/bonds/butterfly.png")
    p.add_argument("--start", default=None)
    p.add_argument("--end", default=None)
    args = p.parse_args()

    dfs, cols = [], []
    for f in args.files:
        if not os.path.exists(f):
            raise RuntimeError(f"File not found: {f}")
        df, name = read_series(f); dfs.append(df); cols.append(name)

    merged = dfs[0]
    for df in dfs[1:]:
        merged = pd.merge(merged, df, on="date", how="outer")
    merged = merged.sort_values("date").reset_index(drop=True)

    if args.start:
        merged = merged[merged["date"] >= pd.to_datetime(args.start)]
    if args.end:
        merged = merged[merged["date"] <= pd.to_datetime(args.end)]

    # try mapping heuristics
    def pick(keys):
        for k in keys:
            for c in merged.columns:
                if k.lower() in c.lower():
                    return c
        return None
    c2 = pick(["dgs2","2y","2"])
    c10 = pick(["dgs10","10y","10"])
    c30 = pick(["dgs30","30y","30"])
    cols_found = [c for c in [c2,c10,c30] if c]
    if len(cols_found) < 3:
        # fallback to order given
        cols_list = [c for c in merged.columns if c!="date"]
        if len(cols_list) >= 3:
            c2, c10, c30 = cols_list[0], cols_list[1], cols_list[2]
        else:
            raise RuntimeError("Não foi possível identificar séries 2y/10y/30y.")

    merged = merged.rename(columns={c2:"US2Y", c10:"US10Y", c30:"US30Y"})
    merged[["US2Y","US10Y","US30Y"]] = merged[["US2Y","US10Y","US30Y"]].apply(pd.to_numeric, errors="coerce")

    merged["BUTTERFLY"] = merged["US30Y"] - 2.0*merged["US10Y"] + merged["US2Y"]
    merged["BUTTER_MA"] = merged["BUTTERFLY"].rolling(window=args.window, min_periods=1).mean()

    latest = merged.dropna(subset=["BUTTERFLY"]).iloc[-1]
    print(f"Último butterfly ({latest['date'].date()}): {latest['BUTTERFLY']:.4f}")

    fig, ax = plt.subplots(figsize=(12,5))
    ax.plot(merged["date"], merged["BUTTERFLY"], label="Butterfly")
    ax.plot(merged["date"], merged["BUTTER_MA"], linestyle="--", label=f"MA{args.window}")
    ax.axhline(0, linestyle=":", linewidth=0.8)
    ax.set_ylabel("pp")
    ax.grid(True)
    ax.legend(loc="upper left")
    ax.set_title("Curve Butterfly = 30Y - 2×10Y + 2Y")

    out = args.out
    os.makedirs(os.path.dirname(out), exist_ok=True)
    plt.tight_layout()
    plt.savefig(out, dpi=150)
    plt.close()
    print("Saved:", out)
    print("Period:", merged['date'].min().date(), "→", merged['date'].max().date())

if __name__ == "__main__":
    main()
