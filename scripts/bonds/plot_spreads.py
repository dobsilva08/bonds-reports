#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Plota spreads da curva e sinaliza inversões.

Spreads calculados:
 - spread_10_2 = DGS10 - DGS2  (inversão se < 0)
 - spread_30_2 = DGS30 - DGS2  (inversão se < 0)
 - spread_30_10 = DGS30 - DGS10

Uso:
  python scripts/bonds/plot_spreads.py \
    --files pipelines/bonds/us2y_daily.csv pipelines/bonds/us10y_daily.csv pipelines/bonds/us30y_daily.csv \
    --window 20 \
    --ema \
    --out pipelines/bonds/spreads.png
"""
import argparse
import os
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt

def read_series(path):
    df = pd.read_csv(path, parse_dates=["date"])
    if "yield_pct" not in df.columns:
        raise RuntimeError(f"{path} missing yield_pct")
    # infer name from source or filename
    name = None
    if "source" in df.columns and df["source"].notnull().any():
        s = df.loc[df["source"].first_valid_index(), "source"]
        name = s.split(":")[-1] if isinstance(s, str) and ":" in s else str(s)
    if not name:
        name = os.path.splitext(os.path.basename(path))[0]
    df = df[["date", "yield_pct"]].rename(columns={"yield_pct": name})
    df = df.sort_values("date").reset_index(drop=True)
    return df, name

def moving(series, window, ema=False):
    if ema:
        return series.ewm(span=window, adjust=False, min_periods=1).mean()
    return series.rolling(window=window, min_periods=1).mean()

def main():
    parser = argparse.ArgumentParser(description="Plot spreads (2y-10y etc.) and signal inversions")
    parser.add_argument("--files", nargs=3, required=True, help="3 CSVs: us2y, us10y, us30y (any order)")
    parser.add_argument("--window", type=int, default=20, help="rolling window for smoothing")
    parser.add_argument("--ema", action="store_true", help="use EMA for smoothing (default SMA)")
    parser.add_argument("--out", default="pipelines/bonds/spreads.png", help="output PNG")
    parser.add_argument("--start", default=None, help="optional start date YYYY-MM-DD")
    parser.add_argument("--end", default=None, help="optional end date YYYY-MM-DD")
    args = parser.parse_args()

    # read files and build single DF
    dfs = []
    names = []
    for p in args.files:
        if not os.path.exists(p):
            raise RuntimeError(f"File not found: {p}")
        df, name = read_series(p)
        dfs.append(df)
        names.append(name)

    merged = dfs[0]
    for df in dfs[1:]:
        merged = pd.merge(merged, df, on="date", how="outer")
    merged = merged.sort_values("date").reset_index(drop=True)

    if args.start:
        merged = merged[merged["date"] >= pd.to_datetime(args.start)]
    if args.end:
        merged = merged[merged["date"] <= pd.to_datetime(args.end)]

    # Try to map columns to DGS2, DGS10, DGS30 heuristically
    col_map = {c: c for c in merged.columns if c != "date"}
    # prefer common names
    def pick_candidate(keys):
        for k in keys:
            for c in col_map:
                if k.lower() in c.lower():
                    return c
        return None

    c2 = pick_candidate(["DGS2", "2", "2y", "us2y", "us2"])
    c10 = pick_candidate(["DGS10", "10", "10y", "us10y", "us10"])
    c30 = pick_candidate(["DGS30", "30", "30y", "us30y", "us30"])

    if not (c2 and c10 and c30):
        # fallback: if only three non-date columns, assign in order provided
        cols = [c for c in merged.columns if c != "date"]
        if len(cols) >= 3:
            c2, c10, c30 = cols[0], cols[1], cols[2]
        else:
            raise RuntimeError("Não foi possível identificar 2y/10y/30y entre as colunas.")

    merged = merged[["date", c2, c10, c30]].rename(columns={c2: "US2Y", c10: "US10Y", c30: "US30Y"})
    # convert to numeric
    for col in ["US2Y","US10Y","US30Y"]:
        merged[col] = pd.to_numeric(merged[col], errors="coerce")

    merged = merged.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)

    # compute spreads
    merged["S_10_2"] = merged["US10Y"] - merged["US2Y"]
    merged["S_30_2"] = merged["US30Y"] - merged["US2Y"]
    merged["S_30_10"] = merged["US30Y"] - merged["US10Y"]

    # smoothing
    for s in ["S_10_2","S_30_2","S_30_10"]:
        merged[f"{s}_MA"] = moving(merged[s], args.window, ema=args.ema)

    # latest values & inversion flags
    last = merged.dropna(subset=["S_10_2","S_30_2","S_30_10"]).iloc[-1]
    info_lines = [
        f"Data (última): {last['date'].date()}",
        f"10y-2y: {last['S_10_2']:.2f}  (MA{args.window}={last['S_10_2_MA']:.2f})  -> {'INVERTIDA' if last['S_10_2']<0 else 'normal'}",
        f"30y-2y: {last['S_30_2']:.2f}  (MA{args.window}={last['S_30_2_MA']:.2f})  -> {'INVERTIDA' if last['S_30_2']<0 else 'normal'}",
        f"30y-10y: {last['S_30_10']:.2f}  (MA{args.window}={last['S_30_10_MA']:.2f})",
    ]
    print("\n".join(info_lines))

    # plot
    spreads = ["S_10_2","S_30_2","S_30_10"]
    n = len(spreads)
    fig, axes = plt.subplots(nrows=n, ncols=1, figsize=(12, 3.5*n), sharex=True)

    for i, s in enumerate(spreads):
        ax = axes[i]
        ax.plot(merged["date"], merged[s], label=s)
        ax.plot(merged["date"], merged[f"{s}_MA"], linestyle="--", label=f"{s} MA{args.window}")
        # shade inversion area where spread < 0
        neg = merged[s] < 0
        if neg.any():
            # find contiguous negative regions and shade
            merged["neg_flag"] = neg.astype(int)
            merged["neg_shift"] = merged["neg_flag"].diff().fillna(0).astype(int)
            starts = merged[merged["neg_shift"]==1].index.tolist()
            ends = merged[merged["neg_shift"]==-1].index.tolist()
            if neg.iloc[0]:
                starts = [0] + starts
            if neg.iloc[-1]:
                ends = ends + [len(merged)-1]
            for st, ed in zip(starts, ends):
                ax.axvspan(merged.loc[st,"date"], merged.loc[ed,"date"], alpha=0.12, color='grey')
            # cleanup temp cols
            merged.drop(columns=["neg_flag","neg_shift"], inplace=True, errors=True)

        ax.axhline(0, linewidth=0.6, linestyle=":", alpha=0.8)
        ax.set_ylabel("bps (pp)")  # in percent points
        ax.legend(loc="upper left")
        ax.grid(True)

    axes[-1].set_xlabel("Data")
    plt.suptitle("Spreads da Curva — sinal de inversão (áreas sombreadas = spread < 0)")
    plt.tight_layout(rect=[0,0,1,0.96])

    out_path = os.path.abspath(args.out)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    plt.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"Gráfico de spreads salvo em: {out_path}")

if __name__ == "__main__":
    main()
