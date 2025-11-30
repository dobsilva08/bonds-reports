#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Surface 3D da curva (maturidade x tempo x yield).
Saída: pipelines/bonds/curve_surface.png
"""

import os
import argparse
from datetime import datetime
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401

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
    parser.add_argument("--out", default="pipelines/bonds/curve_surface.png")
    parser.add_argument("--mstep", type=float, default=1.0)
    args = parser.parse_args()

    dfs = [read_series(p) for p in args.files]
    merged = dfs[0]
    for df in dfs[1:]:
        merged = pd.merge(merged, df, on="date", how="outer")
    merged = merged.sort_values("date").reset_index(drop=True)

    # map cols
    cols = [c for c in merged.columns if c!="date"]
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

    # resample monthly
    merged = merged.set_index("date").resample("MS").mean().interpolate().reset_index()
    maturities = np.arange(2,31,args.mstep)
    base_mats = np.array([2.0,10.0,30.0])

    grid = []
    for i, row in merged.iterrows():
        vals = np.array([row["US2Y"], row["US10Y"], row["US30Y"]], dtype=float)
        vals = np.nan_to_num(vals, nan=np.nanmean(vals))
        grid.append(np.interp(maturities, base_mats, vals))
    grid = np.array(grid)  # shape (T, M)

    # prepare mesh
    T = grid.shape[0]
    X, Y = np.meshgrid(maturities, np.arange(T))  # X=maturities, Y=time index
    Z = grid

    fig = plt.figure(figsize=(12,6))
    ax = fig.add_subplot(111, projection='3d')
    surf = ax.plot_surface(X, Y, Z, cmap='viridis', linewidth=0, antialiased=False)
    ax.set_xlabel('Maturidade (anos)')
    ax.set_ylabel('Tempo (index)')
    ax.set_zlabel('Yield (%)')
    fig.colorbar(surf, shrink=0.5, aspect=10)
    plt.title("Surface: Curva 2Y-30Y (tempo x maturidade x yield)")
    plt.tight_layout()
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    fig.savefig(args.out, dpi=150)
    plt.close(fig)
    print("[OK] surface salvo em", args.out)

if __name__ == "__main__":
    main()
