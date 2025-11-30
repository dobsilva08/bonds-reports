#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gera GIF animado da evolução da curva (2Y->30Y) no tempo.
Saída padrão: pipelines/bonds/curve_anim.gif
"""

import os
import argparse
from datetime import datetime
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import imageio

def read_series(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["date"]).sort_values("date").reset_index(drop=True)
    ycol = None
    for c in df.columns:
        if c.lower() in ("yield", "yield_pct"):
            ycol = c
            break
    if ycol is None:
        ycol = df.columns[1]
    name = os.path.splitext(os.path.basename(path))[0]
    return df[["date", ycol]].rename(columns={ycol:name})

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--files", nargs=3, required=True)
    parser.add_argument("--out", default="pipelines/bonds/curve_anim.gif")
    parser.add_argument("--mstep", type=float, default=1.0)
    parser.add_argument("--fps", type=int, default=6)
    args = parser.parse_args()

    dfs = [read_series(p) for p in args.files]
    merged = dfs[0]
    for df in dfs[1:]:
        merged = pd.merge(merged, df, on="date", how="outer")
    merged = merged.sort_values("date").reset_index(drop=True)

    # detect columns and rename consistently
    cols = [c for c in merged.columns if c!="date"]
    # heuristics
    def find(patterns):
        for p in patterns:
            for c in cols:
                if p.lower() in c.lower():
                    return c
        return None
    c2 = find(["2y","dgs2","2"])
    c10 = find(["10y","dgs10","10"])
    c30 = find(["30y","dgs30","30"])
    merged = merged[[ "date", c2, c10, c30]].rename(columns={c2:"US2Y", c10:"US10Y", c30:"US30Y"})
    merged = merged.set_index("date").resample("MS").mean().interpolate().reset_index()

    maturities = np.arange(2,31, args.mstep)
    base_mats = np.array([2.0,10.0,30.0])

    frames = []
    tmp_dir = "/tmp/curve_anim_frames"
    os.makedirs(tmp_dir, exist_ok=True)

    for i, row in merged.iterrows():
        values = np.array([row["US2Y"], row["US10Y"], row["US30Y"]], dtype=float)
        values = np.nan_to_num(values, nan=np.nanmean(values))
        vals_interp = np.interp(maturities, base_mats, values)

        plt.figure(figsize=(8,4))
        plt.plot(maturities, vals_interp, marker='o')
        plt.ylim(np.nanmin(vals_interp)-0.5, np.nanmax(vals_interp)+0.5)
        plt.title(f"Yield curve — {row['date'].strftime('%Y-%m')}")
        plt.xlabel("Maturidade (anos)")
        plt.ylabel("Yield (%)")
        plt.grid(True)

        fname = os.path.join(tmp_dir, f"frame_{i:04d}.png")
        plt.tight_layout()
        plt.savefig(fname, dpi=120)
        plt.close()
        frames.append(imageio.imread(fname))

    # write gif
    imageio.mimsave(args.out, frames, fps=args.fps)
    # cleanup optional
    for f in os.listdir(tmp_dir):
        try:
            os.remove(os.path.join(tmp_dir, f))
        except Exception:
            pass
    print("[OK] GIF salvo em", args.out)

if __name__ == "__main__":
    main()
