#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Plota gráficos separados (um por ativo) para US2Y, US10Y e US30Y.

Cada subplot contém:
 - série diária de yield
 - média móvel (SMA por padrão; use --ema para EMA)

Uso exemplo:
  python scripts/bonds/plot_yields_separate.py \
    --files pipelines/bonds/us2y_daily.csv pipelines/bonds/us10y_daily.csv pipelines/bonds/us30y_daily.csv \
    --window 20 \
    --out pipelines/bonds/yields_separate.png

Argumentos:
  --files : 3 CSVs (ordem livre, mas recomendo 2Y 10Y 30Y)
  --window: janela (dias) para média móvel (default: 20)
  --ema    : usar EMA em vez de SMA (opcional)
  --out   : caminho do PNG de saída (default: pipelines/bonds/yields_separate.png)
  --start : (opcional) data inicial YYYY-MM-DD
  --end   : (opcional) data final YYYY-MM-DD
"""

import argparse
import os
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt

def read_series(path: str) -> (pd.DataFrame, str):
    df = pd.read_csv(path, parse_dates=["date"])
    if "yield_pct" not in df.columns:
        raise RuntimeError(f"Arquivo {path} não contém coluna 'yield_pct'.")
    # tenta inferir nome da série pela coluna source ou nome do arquivo
    name = None
    if "source" in df.columns and df["source"].notnull().any():
        src = df.loc[df["source"].first_valid_index(), "source"]
        if isinstance(src, str) and ":" in src:
            name = src.split(":")[-1]
        else:
            name = str(src)
    if not name:
        name = os.path.splitext(os.path.basename(path))[0]
    df = df[["date", "yield_pct"]].copy()
    df = df.sort_values("date").reset_index(drop=True)
    df.rename(columns={"yield_pct": name}, inplace=True)
    return df, name

def moving_average(series: pd.Series, window: int, ema: bool) -> pd.Series:
    if ema:
        return series.ewm(span=window, adjust=False, min_periods=1).mean()
    return series.rolling(window=window, min_periods=1).mean()

def main():
    parser = argparse.ArgumentParser(description="Plota gráficos separados para yields (2Y,10Y,30Y).")
    parser.add_argument("--files", nargs="+", required=True, help="CSV(s) de entrada (date,yield_pct,source). Recomendo 3 arquivos (2Y,10Y,30Y).")
    parser.add_argument("--window", type=int, default=20, help="janela para média móvel (dias)")
    parser.add_argument("--ema", action="store_true", help="usar EMA ao invés de SMA")
    parser.add_argument("--out", default="pipelines/bonds/yields_separate.png", help="PNG de saída")
    parser.add_argument("--start", default=None, help="Data inicial filter YYYY-MM-DD")
    parser.add_argument("--end", default=None, help="Data final filter YYYY-MM-DD")
    args = parser.parse_args()

    # lê séries (aceita menos de 3 arquivos, mas avisa)
    series_list = []
    names = []
    for path in args.files:
        if not os.path.exists(path):
            print(f"Warning: arquivo não encontrado: {path} — pulando.")
            continue
        df, name = read_series(path)
        series_list.append(df)
        names.append(name)

    if not series_list:
        raise RuntimeError("Nenhum arquivo válido fornecido. Saindo.")

    # merge por data para alinhamento (outer)
    merged = series_list[0]
    for df in series_list[1:]:
        merged = pd.merge(merged, df, on="date", how="outer")
    merged = merged.sort_values("date").reset_index(drop=True)

    # filtra período
    if args.start:
        start_dt = pd.to_datetime(args.start)
        merged = merged[merged["date"] >= start_dt]
    if args.end:
        end_dt = pd.to_datetime(args.end)
        merged = merged[merged["date"] <= end_dt]

    if merged.empty:
        raise RuntimeError("Nenhum dado após aplicar filtros de data.")

    # prepara plot: um subplot por série (ordem de names)
    n = len(names)
    figsize = (12, 4 * n)
    fig, axes = plt.subplots(nrows=n, ncols=1, figsize=figsize, sharex=True)
    if n == 1:
        axes = [axes]  # garante lista

    for idx, name in enumerate(names):
        ax = axes[idx]
        # pode haver NaN para alguma data; extrai série
        series = merged[["date", name]].copy()
        series = series.dropna(subset=[name])
        if series.empty:
            print(f"Warning: série {name} está vazia após filtro — pulando plot.")
            continue

        # plot da série (não especificamos cores)
        ax.plot(series["date"], series[name], label=f"{name} (yield)")

        # média móvel (aplicada à série alinhada)
        ma = moving_average(merged[name], args.window, args.ema)
        ax.plot(merged["date"], ma, linestyle="--", label=f"{name} MA{args.window}{' EMA' if args.ema else ''}")

        ax.set_title(f"{name} — Yield e Média Móvel (window={args.window})")
        ax.set_ylabel("Yield (%)")
        ax.grid(True)
        ax.legend(loc="upper left")

    axes[-1].set_xlabel("Data")

    out_path = os.path.abspath(args.out)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close(fig)

    print(f"Gráfico salvo em: {out_path}")
    print("Período plotado:", merged["date"].min().date(), "→", merged["date"].max().date())
    print("Séries plotadas:", names)

if __name__ == "__main__":
    main()
