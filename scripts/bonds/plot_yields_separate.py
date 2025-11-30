#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Plota gráficos separados (um por ativo) para US2Y, US10Y e US30Y.

Opções:
  --last-12m : filtra apenas os últimos 12 meses (altera saída para *_12m.png)
  --ema       : usa EMA em vez de SMA para a média móvel
  --window    : janela da média móvel (default 20)

Exemplo:
  python scripts/bonds/plot_yields_separate.py \
    --files pipelines/bonds/us2y_daily.csv pipelines/bonds/us10y_daily.csv pipelines/bonds/us30y_daily.csv \
    --window 20 --out pipelines/bonds/yields_separate.png
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
    name = None
    if "source" in df.columns and df["source"].notnull().any():
        src = df.loc[df["source"].first_valid_index(), "source"]
        if isinstance(src, str) and ":" in src:
            name = src.split(":")[-1]
        else:
            name = str(src)
    if not name:
        name = os.path.splitext(os.path.basename(path))[0]
    df = df[["date", "yield_pct"]].copy().sort_values("date").reset_index(drop=True)
    df.rename(columns={"yield_pct": name}, inplace=True)
    return df, name

def moving_average(series: pd.Series, window: int, ema: bool) -> pd.Series:
    if ema:
        return series.ewm(span=window, adjust=False, min_periods=1).mean()
    return series.rolling(window=window, min_periods=1).mean()

def ensure_out_name(out: str, last12: bool) -> str:
    if last12 and out.endswith(".png"):
        return out.replace(".png", "_12m.png")
    return out

def main():
    parser = argparse.ArgumentParser(description="Plota gráficos separados para yields (2Y,10Y,30Y).")
    parser.add_argument("--files", nargs="+", required=True, help="CSV(s) de entrada (date,yield_pct,source). Recomendo 3 arquivos (2Y,10Y,30Y).")
    parser.add_argument("--window", type=int, default=20, help="janela para média móvel (dias)")
    parser.add_argument("--ema", action="store_true", help="usar EMA ao invés de SMA")
    parser.add_argument("--out", default="pipelines/bonds/yields_separate.png", help="PNG de saída")
    parser.add_argument("--start", default=None, help="Data inicial filter YYYY-MM-DD")
    parser.add_argument("--end", default=None, help="Data final filter YYYY-MM-DD")
    parser.add_argument("--last-12m", action="store_true", help="Filtra apenas últimos 12 meses e ajusta nome do arquivo")
    args = parser.parse_args()

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

    if args.last_12m:
        cutoff = datetime.utcnow().date() - timedelta(days=365)
        merged = merged[merged["date"] >= pd.to_datetime(cutoff)]
        args.out = ensure_out_name(args.out, True)

    if merged.empty:
        raise RuntimeError("Nenhum dado após aplicar filtros de data.")

    # prepara plot
    cols = [c for c in merged.columns if c != "date"]
    n = len(cols)
    figsize = (12, 4 * n)
    fig, axes = plt.subplots(nrows=n, ncols=1, figsize=figsize, sharex=True)
    if n == 1:
        axes = [axes]

    for idx, col in enumerate(cols):
        ax = axes[idx]
        series = merged[["date", col]].copy().dropna()
        if series.empty:
            print(f"Warning: série {col} está vazia após filtro — pulando.")
            continue

        ax.plot(series["date"], series[col], label=f"{col} (yield)")
        ma = moving_average(merged[col], args.window, args.ema)
        ax.plot(merged["date"], ma, linestyle="--", label=f"{col} MA{args.window}{' EMA' if args.ema else ''}")

        ax.set_title(f"{col} — Yield e Média Móvel (window={args.window})")
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
    print("Séries plotadas:", cols)

if __name__ == "__main__":
    main()
