# Bonds Reports — US Treasury 2Y / 10Y / 30Y

Daily data and curve analytics based on FRED constant-maturity series:
- DGS2 — US 2-Year
- DGS10 — US 10-Year
- DGS30 — US 30-Year

## Unified workflow
The unified workflow is `.github/workflows/bonds_unified.yml`, scheduled for 07:05 BRT (10:05 UTC). It collects, validates, calculates curve metrics, generates charts, and sends charts plus a quantitative executive snapshot to Telegram.

Legacy workflows remain available via manual dispatch but have their schedules disabled to prevent duplicate automated deliveries.

## Validation
The data engine rejects missing columns, duplicate observations, too few valid observations, implausible yields, future dates, and stale observations (more than 10 calendar days).

## Metrics
- 10Y-2Y, 30Y-10Y, 30Y-2Y spreads
- 30Y-2×10Y+2Y butterfly
- daily changes (basis points)
- 30-observation rolling realized volatility
- 252-observation rolling Z-score

## Macro and AI boundaries
Macro context describes supplied curve data only and warns that yields alone cannot establish macro causes, news, flows, term premium, or institutional positioning. Shared LLM prompt and report validation are groundwork for a later integration stage; the current unified scheduled workflow delivers a quantitative snapshot, not generated macro commentary.

## Testing
Run offline tests: `python -m unittest discover -s tests`

## Secrets
Scheduled production requires `FRED_API_KEY`, `TELEGRAM_BOT_TOKEN`, and `TELEGRAM_CHAT_ID`. Never print credentials in logs.
