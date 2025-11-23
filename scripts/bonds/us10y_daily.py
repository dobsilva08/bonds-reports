#!/usr/bin/env python3
"""
Baixa o yield do Treasury 10 anos (US10Y) via FRED.

Série padrão:
  - DGS10 = 10-Year Treasury Constant Maturity Rate (%)

Requisitos:
 - FRED_API_KEY (no ambiente)
 - requests, pandas

Saída:
 - CSV com colunas: date, yield_pct, source

Uso:
  python scripts/bonds/us10y_daily.py --out pipelines/bonds/us10y_daily.csv
"""

import argparse
import os
from datetime import datetime
import requests
import pandas as pd

FRED_BASE_URL = "https://api.stlouisfed.org/fred/series/observations"


def fetch_us10y_from_fred(
    api_key: str,
    series_id: str = "DGS10",
    observation_start: str = "2000-01-01",
) -> pd.DataFrame:
    params = {
        "series_id": series_id,
        "api_key": api_key,
        "file_type": "json",
        "observation_start": observation_start,
    }

    resp = requests.get(FRED_BASE_URL, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    observations = data.get("observations", [])

    rows = []
    for obs in observations:
        date_str = obs.get("date")
        value_str = obs.get("value")

        if value_str in (None, ".", ""):
            continue

        try:
            value = float(value_str)
        except ValueError:
            continue

        dt = datetime.strptime(date_str, "%Y-%m-%d").date()
        rows.append(
            {
                "date": dt,
                "yield_pct": value,
                "source": f"FRED:{series_id}",
            }
        )

    df = pd.DataFrame(rows)
    df = df.sort_values("date").reset_index(drop=True)
    return df


def main():
    parser = argparse.ArgumentParser(description="Baixa yield do US10Y (DGS10) via FRED.")
    parser.add_argument(
        "--out",
        required=True,
        help="Caminho do CSV de saída (ex: pipelines/bonds/us10y_daily.csv)",
    )
    parser.add_argument(
        "--series-id",
        default=os.environ.get("US10Y_FRED_SERIES_ID", "DGS10"),
        help="ID da série no FRED (padrão: DGS10 ou US10Y_FRED_SERIES_ID).",
    )
    parser.add_argument(
        "--start",
        default="2000-01-01",
        help="Data inicial (YYYY-MM-DD, default: 2000-01-01)",
    )
    args = parser.parse_args()

    api_key = os.environ.get("FRED_API_KEY")
    if not api_key:
        raise RuntimeError("FRED_API_KEY não configurado no ambiente.")

    df = fetch_us10y_from_fred(
        api_key=api_key,
        series_id=args.series_id,
        observation_start=args.start,
    )

    out_path = os.path.abspath(args.out)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    df.to_csv(out_path, index=False)
    print(f"[US10Y] CSV salvo em {out_path}")
    print(f"[US10Y] Linhas: {len(df)} — Período {df['date'].min()} → {df['date'].max()}")


if __name__ == "__main__":
    main()
