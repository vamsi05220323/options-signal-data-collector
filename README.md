# Options Signal Data Collector

This project is a local research data collector for options signals. It does not place orders, does not auto-trade, and does not print buy/sell alerts.

The first research question is whether option chart spikes were actually tradable through live bid/ask quotes. The key metric is:

```text
conservative_return = best_future_bid / earlier_ask - 1
```

That asks whether a contract could have been bought at the ask and later sold at the bid.

The executable metric only uses individually valid, fresh, non-crossed, non-locked quotes without intrinsic-value violations. The original signal contract is excluded from opposite-side opportunity decisions.

## Install

```powershell
cd C:\workspace\options_alert_engine
powershell -ExecutionPolicy Bypass -File .\scripts\setup.ps1
```

Edit `.env.local` for local settings only. Do not put broker passwords in the repo.

If normal `python` commands fail in PowerShell, use the scripts. See `LAUNCH_GUIDE.md`.

## Preflight

Mock mode:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\mock_preflight.ps1
```

IBKR mode:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\ibkr_preflight.ps1
```

IBKR assumes TWS or IB Gateway is already open and manually logged in. Enable API access in TWS/Gateway and use the correct paper/live port, usually `7497` for paper TWS and `7496` for live TWS. U.S. options need OPRA data, and underlying stocks need live stock data.

## Collect Signals

Single signal:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run.ps1 collect-signal --symbol BEAM --direction CALL --strike 40 --expiry 2026-07-17 --signal-premium 0.40 --stock-price 36.50 --provider mock --duration-seconds 30
```

Single signal with explicit signal/start/end times:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run.ps1 collect-signal --symbol MAN --direction PUT --strike 35 --expiry 2026-07-17 --stock-price 36.27 --provider ibkr --primary-exchange NYSE --signal-time 10:00 --start-time now --end-time market-close
```

When a time has no timezone offset, the app uses `TIMEZONE` from `.env.local`. The default project timezone is `America/Chicago`, which is Texas/Central time.

CSV file:

```powershell
.\scripts\mock_collect.ps1
```

CSV columns:

```text
timestamp_local,symbol,direction,signal_strike,expiry,signal_premium,stock_price_at_signal
```

Optional IBKR identity columns for ambiguous symbols:

```text
underlying_exchange,primary_exchange,currency,ibkr_con_id,ibkr_local_symbol,ibkr_trading_class
```

For normal U.S. NASDAQ/NYSE stock signals, these optional columns can be left blank. In IBKR mode the app resolves the stock contract through TWS, stores the selected conId/primary exchange in `signals.csv`, and stores option local symbol/trading class details in `option_ticks.csv`.

The collector tracks the original signal contract, exact opposite strike, one ITM opposite contract, ATM/nearest opposite contract, several OTM opposite contracts, and optional lotto observation contracts.

## Outputs

Daily run folders are written to:

```text
data/runs/YYYY-MM-DD/
```

Files:

```text
signals.csv
stock_ticks.csv
option_ticks.csv
option_5sec_bars.csv
option_1min_bars.csv
option_5min_bars.csv
summary_by_contract.csv
summary_by_signal.csv
news_articles.csv
news_summary_by_signal.csv
provider_errors.csv
market_capture.sqlite
```

`summary_by_contract.csv` includes executable 40%, 50%, 100%, and 180% threshold flags and first-hit times. `raw_unfiltered_ask_to_bid_return` is retained for diagnostics only and must not be treated as executable.

Summarize an existing run:

```powershell
python -m src.main summarize --run-folder data/runs/YYYY-MM-DD
```

Replay currently rebuilds summaries from an existing run folder:

```powershell
python -m src.main replay --run-folder data/runs/YYYY-MM-DD
```

## News Context

News is a context/ranking filter, not a trade trigger. The collector supports mock news for testing and has official Alpha Vantage and Finnhub provider modules. Mock news is explicitly non-scoring. A failed external provider is recorded as `NEWS_UNAVAILABLE` and is not replaced by scored mock news. Yahoo/yfinance news is deliberately not enabled by default because it is an unofficial fallback.

The ranking formula is:

```text
70% stock/option microstructure
20% news context
10% signal-side contract behavior
```

News details are written to `news_articles.csv`, `news_summary_by_signal.csv`, and the main `summary_by_signal.csv`.

Set one of these in `.env.local` if available:

```text
NEWS_PROVIDER=alpha_vantage
ALPHA_VANTAGE_API_KEY=...
```

or:

```text
NEWS_PROVIDER=finnhub
FINNHUB_API_KEY=...
```

News scoring is experimental and should not override bid/ask execution data.

## Safety

This is data collection and research software only. It is not financial advice, not an alert engine, and not an execution system. `ENABLE_TRADING` should stay `false`.
