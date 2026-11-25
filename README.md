# 🇺🇸 US Treasury & Macro Intelligence
### Daily Fixed Income Market Monitor

A scheduled, data-first Treasury market monitor built around the US 2Y, 10Y and 30Y constant-maturity yields from Federal Reserve FRED.

## Daily coverage
- **Market Overview:** 2Y, 10Y and 30Y yields and daily changes in basis points.
- **Curve Structure:** 10Y–2Y, 30Y–10Y, 30Y–2Y and 30Y–10Y–2Y butterfly metric.
- **Volatility:** rolling realized volatility of daily yield changes.
- **Statistical Position:** rolling 252-observation Z-scores.
- **Macro Intelligence:** rules-based curve and movement labels with clear interpretation limits.
- **Charts:** yield history, spreads, volatility, Z-score, butterfly and curve-comparison visual.
- **Delivery:** Telegram publication and run artifacts.

## Pipeline
1. Collect DGS2, DGS10 and DGS30 from FRED.
2. Validate dates, numeric values, range and freshness.
3. Align observations and calculate curve analytics.
4. Build a structured daily executive report and macro context.
5. Generate chart pack.
6. Deliver via Telegram (scheduled run) and store artifacts.

## Analytics
- Yield changes (bps); rolling 30-observation volatility
- 10Y–2Y, 30Y–10Y, 30Y–2Y
- Butterfly: 30Y − 2×10Y + 2Y
- Rolling 252-observation Z-score

## Schedule & workflow
Unified pipeline: `.github/workflows/bonds_unified.yml` (10:05 UTC / 07:05 BRT). Legacy workflows are retained for manual use, with schedules disabled to avoid duplicate sends.

## Data & interpretation
FRED series: DGS2, DGS10, DGS30. Labels are mechanical descriptions of the supplied data and do not infer causality, inflation expectations, term premium, positioning, flows or news.

## Tests
`python -m unittest discover -s tests` and chart smoke checks in GitHub Actions.

## Secrets
Scheduled production requires `FRED_API_KEY`, `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`. Never log secret values.
