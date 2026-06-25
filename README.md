# Options Signal Data Collector

This project is a local research data collector for options signals. It does not place orders, does not auto-trade, and does not print buy/sell alerts.

The first research question is whether option chart spikes were actually tradable through live bid/ask quotes. The key metric is:

```text
conservative_return = best_future_bid / earlier_ask - 1
```

That asks whether a contract could have been bought at the ask and later sold at the bid.

## Install

```powershell
cd C:\workspace\options_alert_engine
python -m pip install -r requirements.txt
Copy-Item .env.example .env.local
```

Edit `.env.local` for local settings only. Do not put broker passwords in the repo.

## Preflight

Mock mode:

```powershell
python -m src.main preflight --mock
```

IBKR mode:

```powershell
python -m src.main preflight --provider ibkr
```

IBKR assumes TWS or IB Gateway is already open and manually logged in. Enable API access in TWS/Gateway and use the correct paper/live port, usually `7497` for paper TWS and `7496` for live TWS. U.S. options need OPRA data, and underlying stocks need live stock data.

## Collect Signals

Single signal:

```powershell
python -m src.main collect-signal --symbol BEAM --direction CALL --strike 40 --expiry 2026-07-17 --signal-premium 0.40 --stock-price 36.50 --provider mock --duration-seconds 30
```

CSV file:

```powershell
python -m src.main collect-file --signals-file data/sample_signals_today.csv --provider mock --duration-seconds 30
```

CSV columns:

```text
timestamp_local,symbol,direction,signal_strike,expiry,signal_premium,stock_price_at_signal
```

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
market_capture.sqlite
```

Summarize an existing run:

```powershell
python -m src.main summarize --run-folder data/runs/YYYY-MM-DD
```

Replay currently rebuilds summaries from an existing run folder:

```powershell
python -m src.main replay --run-folder data/runs/YYYY-MM-DD
```

## News Context

News is a context/ranking filter, not a trade trigger. The collector supports mock news by default and has official Alpha Vantage and Finnhub provider modules. Yahoo/yfinance news is deliberately not enabled by default because it is an unofficial fallback.

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
