#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Plota gráficos separados (um por ativo) para US2Y, US10Y e US30Y
limitando o período aos últimos 12 meses.

Cada subplot contém:
 - série diária de yield
 - média móvel (SMA por padrão; use --ema para EMA)

Uso:
  python scripts/bonds/plot_yields_12m.py \
    --files pipelines/bonds/us2y_daily.csv pipelines/bonds/us10y_daily.csv pipelines/bonds/us30y_daily.csv \
    --window 20 \
    --out pipelines/bonds/yields_12m.png
"""

import argparse
import os
from datetime import datetime, timedelta
import pandas as pd
import matplotlib.pyplot as plt


def read_series(path: str):
    df = pd.read_csv(path, parse_dates=["date"])
    if "yield_pct" not in df.columns:
        raise RuntimeError(f"Arquivo {path} não contém coluna 'yield_pct'.")
    # tenta inferir nome
    if "source" in df.columns and df["source"].notnull().any():
        src = df.loc[df["source"].first_valid_index(), "source"]
        name = src.split(":")[-1] if isinstance(src, str) and ":" in src else str(src)
    else:
        name = os.path.splitext(os.path.basename(path))[0]

    df = df.sort_values("date").reset_index(drop=True)
    df = df[["date", "yield_pct"]].rename(columns={"yield_pct": name})
    return df, name


def moving_average(series: pd.Series, window: int, use_ema: bool):
    if use_ema:
        return series.ewm(span=window, adjust=False, min_periods=1).mean()
    return series.rolling(window=window, min_periods=1).mean()


def main():
    parser = argparse.ArgumentParser(description="Plota gráficos separados (2Y,10Y,30Y) últimos 12 meses.")
    parser.add_argument("--files", nargs="+", required=True, help="CSV(s) de entrada")
    parser.add_argument("--window", type=int, default=20, help="janela da média móvel")
    parser.add_argument("--ema", action="store_true", help="usar EMA ao invés de SMA")
    parser.add_argument("--out", default="pipelines/bonds/yields_12m.png", help="PNG de saída")
    args = parser.parse_args()

    series_list = []
    names = []

    for path in args.files:
        if not os.path.exists(path):
            print(f"Arquivo não encontrado: {path}, pulando.")
            continue
        df, name = read_series(path)
        series_list.append(df)
        names.append(name)

    if not series_list:
        raise RuntimeError("Nenhum arquivo válido fornecido.")

    merged = series_list[0]
    for df in series_list[1:]:
        merged = pd.merge(merged, df, on="date", how="outer")

    merged = merged.sort_values("date").reset_index(drop=True)

    # --- FILTRO PARA ÚLTIMOS 12 MESES ---
    cutoff = datetime.utcnow().date() - timedelta(days=365)
    merged = merged[merged["date"] >= pd.to_datetime(cutoff)]

    if merged.empty:
        raise RuntimeError("Nenhum dado nos últimos 12 meses.")

    # --- PLOT ---
    n = len(names)
    fig, axes = plt.subplots(nrows=n, ncols=1, figsize=(12, 4 * n), sharex=True)
    if n == 1:
        axes = [axes]

    for i, name in enumerate(names):
        ax = axes[i]
        series = merged[["date", name]].dropna()
        if series.empty:
            print(f"Série {name} vazia após filtro — pulando.")
            continue

        ax.plot(series["date"], series[name], label=f"{name} (yield)")

        ma = moving_average(merged[name], args.window, args.ema)
        ax.plot(merged["date"], ma, linestyle="--", label=f"{name} MA{args.window}")

        ax.set_title(f"{name} — Últimos 12 meses (MA={args.window})")
        ax.set_ylabel("Yield (%)")
        ax.grid(True)
        ax.legend(loc="upper left")

    axes[-1].set_xlabel("Data")

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    plt.tight_layout()
    plt.savefig(args.out, dpi=150)
    plt.close(fig)

    print(f"[OK] Gráfico salvo em {args.out}")
    print("Período:", merged["date"].min().date(), "→", merged["date"].max().date())


if __name__ == "__main__":
    main()
