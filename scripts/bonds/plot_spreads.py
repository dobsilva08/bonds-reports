#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Plota spreads da curva (10y-2y, 30y-2y, 30y-10y).
Opções:
  --last-12m : filtra últimos 12 meses e ajusta saída para *_12m.png
  --ema      : usar EMA no smoothing
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
    df = df.sort_values("date").reset_index(drop=True)
    return df, name

def moving(series, window, ema=False):
    if ema:
        return series.ewm(span=window, adjust=False, min_periods=1).mean()
    return series.rolling(window=window, min_periods=1).mean()

def ensure_out_name(out: str, last12: bool) -> str:
    if last12 and out.endswith(".png"):
        return out.replace(".png", "_12m.png")
    return out

def main():
    parser = argparse.ArgumentParser(description="Plot spreads (2y-10y etc.) and signal inversions")
    parser.add_argument("--files", nargs=3, required=True, help="3 CSVs: us2y, us10y, us30y (any order)")
    parser.add_argument("--window", type=int, default=20, help="rolling window for smoothing")
    parser.add_argument("--ema", action="store_true", help="use EMA for smoothing (default SMA)")
    parser.add_argument("--out", default="pipelines/bonds/spreads.png", help="output PNG")
    parser.add_argument("--start", default=None)
    parser.add_argument("--end", default=None)
    parser.add_argument("--last-12m", action="store_true", help="Filtrar últimos 12 meses e ajustar nome do arquivo")
    args = parser.parse_args()

    dfs = []
    for p in args.files:
        if not os.path.exists(p):
            raise RuntimeError(f"File not found: {p}")
        df, name = read_series(p)
        dfs.append(df)

    merged = dfs[0]
    for df in dfs[1:]:
        merged = pd.merge(merged, df, on="date", how="outer")
    merged = merged.sort_values("date").reset_index(drop=True)

    if args.start:
        merged = merged[merged["date"] >= pd.to_datetime(args.start)]
    if args.end:
        merged = merged[merged["date"] <= pd.to_datetime(args.end)]

    if args.last_12m:
        cutoff = datetime.utcnow().date() - timedelta(days=365)
        merged = merged[merged["date"] >= pd.to_datetime(cutoff)]
        args.out = ensure_out_name(args.out, True)

    # Try to map columns to DGS2, DGS10, DGS30 heuristically
    def pick_candidate(keys):
        for k in keys:
            for c in [col for col in merged.columns if col != "date"]:
                if k.lower() in c.lower():
                    return c
        return None

    c2 = pick_candidate(["DGS2", "2y", "2", "us2y"])
    c10 = pick_candidate(["DGS10", "10y", "10", "us10y"])
    c30 = pick_candidate(["DGS30", "30y", "30", "us30y"])

    cols = [c for c in merged.columns if c != "date"]
    if not (c2 and c10 and c30):
        if len(cols) >= 3:
            c2, c10, c30 = cols[0], cols[1], cols[2]
        else:
            raise RuntimeError("Não foi possível identificar 2y/10y/30y entre as colunas.")

    merged = merged[["date", c2, c10, c30]].rename(columns={c2: "US2Y", c10: "US10Y", c30: "US30Y"})
    for col in ["US2Y", "US10Y", "US30Y"]:
        merged[col] = pd.to_numeric(merged[col], errors="coerce")

    merged = merged.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)

    merged["S_10_2"] = merged["US10Y"] - merged["US2Y"]
    merged["S_30_2"] = merged["US30Y"] - merged["US2Y"]
    merged["S_30_10"] = merged["US30Y"] - merged["US10Y"]

    for s in ["S_10_2", "S_30_2", "S_30_10"]:
        merged[f"{s}_MA"] = moving(merged[s], args.window, ema=args.ema)

    # latest values & inversion flags
    last = merged.dropna(subset=["S_10_2", "S_30_2", "S_30_10"]).iloc[-1]
    info_lines = [
        f"Data (última): {last['date'].date()}",
        f"10y-2y: {last['S_10_2']:.2f}  (MA{args.window}={last['S_10_2_MA']:.2f})  -> {'INVERTIDA' if last['S_10_2']<0 else 'normal'}",
        f"30y-2y: {last['S_30_2']:.2f}  (MA{args.window}={last['S_30_2_MA']:.2f})  -> {'INVERTIDA' if last['S_30_2']<0 else 'normal'}",
        f"30y-10y: {last['S_30_10']:.2f}  (MA{args.window}={last['S_30_10_MA']:.2f})",
    ]
    print("\n".join(info_lines))

    spreads = ["S_10_2", "S_30_2", "S_30_10"]
    n = len(spreads)
    fig, axes = plt.subplots(nrows=n, ncols=1, figsize=(12, 3.5*n), sharex=True)

    for i, s in enumerate(spreads):
        ax = axes[i]
        ax.plot(merged["date"], merged[s], label=s)
        ax.plot(merged["date"], merged[f"{s}_MA"], linestyle="--", label=f"{s} MA{args.window}")
        neg = merged[s] < 0
        if neg.any():
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
            merged.drop(columns=["neg_flag","neg_shift"], inplace=True, errors=True)
        ax.axhline(0, linewidth=0.6, linestyle=":", alpha=0.8)
        ax.set_ylabel("pp")
        ax.legend(loc="upper left")
        ax.grid(True)

    axes[-1].set_xlabel("Data")
    plt.suptitle("Spreads da Curva — áreas sombreadas = spread < 0")
    plt.tight_layout(rect=[0,0,1,0.96])

    out_path = os.path.abspath(args.out)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    plt.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"Gráfico de spreads salvo em: {out_path}")

if __name__ == "__main__":
    main()
