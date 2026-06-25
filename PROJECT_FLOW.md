# Options Signal Data Collector Project Flow

This document is the implementation map for future work. It explains every tracked project file, the runtime flow, where the application starts, where data ends up, and how the collector is intended to run in real-world use.

## Project Purpose

The app is a local options market-data collector and research engine. It is not an auto-trader and does not place broker orders.

The research question is:

```text
When an options chart shows a sudden spike, was the move actually tradable through live bid/ask?
```

The core execution-quality metric is:

```text
best_conservative_ask_to_bid_return = best_future_bid / earlier_ask - 1
```

This uses the conservative assumption that entry happens at the ask and exit happens at the bid.

## Start Point

The application starts at:

```text
src/main.py
```

Run commands through Python module execution:

```powershell
python -m src.main preflight --mock
python -m src.main preflight --provider ibkr
python -m src.main collect-signal --symbol BEAM --direction CALL --strike 40 --expiry 2026-07-17 --signal-premium 0.40 --stock-price 36.50
python -m src.main collect-file --signals-file data/sample_signals_today.csv --provider mock --duration-seconds 30
python -m src.main summarize --run-folder data/runs/YYYY-MM-DD
python -m src.main replay --run-folder data/runs/YYYY-MM-DD
```

## End Point

Every real or mock collection run writes to:

```text
data/runs/YYYY-MM-DD/
```

The final research outputs are:

```text
summary_by_contract.csv
summary_by_signal.csv
market_capture.sqlite
```

The raw evidence outputs are:

```text
signals.csv
stock_ticks.csv
option_ticks.csv
news_articles.csv
news_summary_by_signal.csv
option_5sec_bars.csv
option_1min_bars.csv
option_5min_bars.csv
```

`data/runs/` is ignored by Git because those files are local run artifacts and can grow quickly.

## Real-World Operating Flow

1. Open TWS or IB Gateway locally and log in manually.
2. Confirm API access is enabled in TWS/Gateway.
3. Confirm `.env.local` has the right IBKR host, port, and client id.
4. Run preflight:

```powershell
python -m src.main preflight --provider ibkr
```

5. Confirm stock bid/ask/last and option bid/ask are available. If option bid/ask is missing, check OPRA and market-data entitlements.
6. Enter signals manually with `collect-signal` or in bulk with `collect-file`.
7. Let the collector write quote snapshots during the observation window.
8. Run `summarize` at the end of the run or rely on the automatic summary after collection.
9. Analyze `summary_by_signal.csv` and `summary_by_contract.csv`.

## Signal Handling Flow

For each signal:

1. `src/main.py` parses CLI arguments.
2. `src/engine/signal_parser.py` parses CSV rows or signal text into `TradeSignal`.
3. `src/main.py` creates the selected provider.
4. `src/engine/capture_manager.py` starts collection.
5. The provider fetches the option chain for the signal expiry.
6. `src/engine/strike_selector.py` selects contracts to track:
   - Original signal-side contract.
   - Exact opposite strike.
   - One ITM opposite contract.
   - ATM or nearest opposite contract.
   - Multiple OTM opposite contracts.
   - Optional lotto observation contracts.
7. The capture loop writes stock ticks and option ticks.
8. News context is fetched once at signal entry.
9. The summarizer builds contract summaries, signal summaries, and bars.

## File-by-File Reference

### Root Files

`README.md`

User-facing setup and run instructions. Keep this concise and operational.

`PROJECT_FLOW.md`

Detailed project map for future development. This file should be updated whenever the architecture changes.

`requirements.txt`

Python dependencies for local development and runtime:

```text
pandas
requests
pydantic
python-dotenv
rich
pytest
ib_insync
```

`.env.example`

Template for local configuration. It intentionally contains no secrets.

`.env.local`

Local machine configuration written by preflight. This file is ignored by Git and must not contain broker passwords.

`.gitignore`

Keeps local secrets, generated run data, SQLite files, pytest cache, and Python bytecode out of version control.

### Data Files

`data/.gitkeep`

Keeps the `data/` folder in Git even when generated run folders are ignored.

`data/sample_signals_today.csv`

Current sample CSV for testing multi-signal collection. It matches the required signal schema.

`data/sample_vrns.csv`

Legacy/sample market data retained as reference input. It is not part of the live collection path.

`data/runs/YYYY-MM-DD/`

Generated output folder. Ignored by Git. Contains CSV and SQLite run artifacts.

### Package Entry

`src/__init__.py`

Package marker and short package description.

`src/main.py`

Primary CLI entry point. Defines commands:

```text
preflight
collect-signal
collect-file
replay
summarize
```

It loads config, parses arguments, chooses providers, creates signals, and calls the capture or summary engine.

`src/config.py`

Loads `.env.local` and exposes `AppConfig`. Owns defaults for:

```text
DATA_PROVIDER
IBKR_HOST
IBKR_PORT
IBKR_CLIENT_ID
strike tracking counts
snapshot timing
spread thresholds
news settings
```

It also writes non-secret preflight settings back to `.env.local`.

`src/models.py`

Core data models and enums:

```text
OptionType
ContractRole
SignalStatus
TradeSignal
OptionContract
StockQuote
OptionQuote
StockTick
OptionTick
NewsArticle
NewsSummary
```

It also has serialization helpers used by CSV and SQLite storage.

`src/preflight.py`

Provider health checks. For IBKR, it connects to local TWS/Gateway, requests a stock quote, requests an option chain, requests an option quote, and warns when bid/ask may be missing because of OPRA or market-data permissions.

### Market Data Providers

`src/providers/__init__.py`

Exports provider classes for the rest of the app.

`src/providers/base.py`

Defines the provider interface:

```text
connect
close
get_stock_quote
get_option_chain
get_option_quote
```

All downstream capture code depends on this interface, not on a broker-specific implementation.

`src/providers/mock_provider.py`

Synthetic quote provider for local testing. It simulates stock pump/failure and option compression/rebound behavior.

`src/providers/ibkr_provider.py`

IBKR provider using `ib_insync`. It lazy-imports IBKR dependencies so mock mode and tests work without TWS. It never stores broker credentials.

`src/providers/webull_provider.py`

Official Webull OpenAPI placeholder. It deliberately rejects use until official OpenAPI credentials and programmatic options quote access are verified.

`src/providers/replay_provider.py`

Reads previously captured CSV output as a provider-like source. Useful for future replay/backtesting extensions.

### News Providers

`src/news_providers/__init__.py`

Exports news provider classes and shared news errors.

`src/news_providers/base.py`

Defines the news provider interface and shared catalyst/sentiment logic:

```text
classify_catalyst
summarize_news
infer_news_bias
score_news_context
make_article
```

News is context only and should not override bid/ask execution evidence.

`src/news_providers/mock_news.py`

Synthetic news provider used by default for local testing.

`src/news_providers/alpha_vantage_news.py`

Official Alpha Vantage News & Sentiment integration. Uses `ALPHA_VANTAGE_API_KEY`.

`src/news_providers/finnhub_news.py`

Official Finnhub company-news integration. Uses `FINNHUB_API_KEY`.

`src/news_providers/yahoo_news.py`

Disabled unofficial fallback. It exists so the provider slot is explicit, but it does not run by default.

### Engine Modules

`src/engine/__init__.py`

Engine package marker.

`src/engine/signal_parser.py`

Parses signal text, expiry strings, local timestamps, and signal CSV files.

`src/engine/strike_selector.py`

Selects the original signal contract plus opposite-side contracts from the available option-chain strike grid. It does not assume fixed one-dollar or five-dollar increments when a chain is available.

`src/engine/metrics.py`

Pure calculations:

```text
mid
spread absolute and spread percent
intrinsic value
extrinsic value
percent change
premium compression
rebound from low
conservative ask-to-bid return
```

`src/engine/quote_validation.py`

Rule-based quote validation. Quotes are not discarded; invalid quotes are stored with `quote_is_valid=false` and a reason.

`src/engine/capture_manager.py`

The main collection runtime. It:

1. Appends signals.
2. Resolves contracts.
3. Captures initial news context.
4. Polls stock and option quotes.
5. Builds stock and option tick rows.
6. Writes CSV and SQLite rows.
7. Renders the live console.
8. Calls summarization at the end of collection.

`src/engine/summarizer.py`

Builds:

```text
summary_by_contract.csv
summary_by_signal.csv
option_5sec_bars.csv
option_1min_bars.csv
option_5min_bars.csv
```

It calculates best theoretical mid return and best conservative ask-to-bid return.

`src/engine/scoring.py`

Rule-based opportunity scoring from 0 to 100. The score is a ranking score, not a probability. It blends:

```text
70% stock/option microstructure
20% news context
10% signal-side contract behavior
```

Each signal is scored independently.

`src/engine/replay.py`

Thin replay wrapper that currently rebuilds summaries from an existing run folder. It is ready to expand into a fuller replay engine.

### Storage

`src/storage/__init__.py`

Exports `RunStorage`.

`src/storage/csv_writer.py`

Defines all CSV schemas and a small append/rewrite CSV helper.

`src/storage/sqlite_store.py`

Creates and writes SQLite tables matching the CSV schemas. The database is stored as:

```text
data/runs/YYYY-MM-DD/market_capture.sqlite
```

### Console UI

`src/ui/__init__.py`

Exports `LiveConsole`.

`src/ui/live_console.py`

Rich/plain console output for active signals and contracts. It displays stock price, contract role, bid/ask/mid/last-style quote fields, spread, compression, rebound, quote validity, and WATCH/COLLECTING status. It does not print BUY or SELL alerts.

### Tests

`tests/test_signal_parser.py`

Tests signal text parsing and expiry inference.

`tests/test_strike_selector.py`

Tests contract role selection and confirms chain strike grids are respected.

`tests/test_metrics.py`

Tests spread, intrinsic/extrinsic value, compression, rebound, and conservative returns.

`tests/test_quote_validation.py`

Tests invalid quote handling and lotto quote allowances.

`tests/test_summarizer.py`

Tests best future bid after earlier ask and contract-level tradability summary.

`tests/test_scoring.py`

Tests independent signal scoring behavior.

`tests/test_multi_signal.py`

Runs a short mock collection with multiple simultaneous signals and confirms summary output is produced.

## Provider Strategy

Current provider priority:

1. `mock` for local development and test replay.
2. `ibkr` for first real live data provider.
3. `webull` only after official OpenAPI access and options quote entitlements are verified.
4. `replay` for historical run analysis.

## Important Safety Rules

The app should continue to obey these rules:

1. Do not store broker usernames or passwords.
2. Do not place orders.
3. Do not add auto-trading without a separate explicit design.
4. Store invalid quotes instead of hiding them.
5. Keep opportunity scores as research ranking scores, not trade instructions.
6. Keep news as context, not a direct trigger.

## Common Development Commands

Install:

```powershell
python -m pip install -r requirements.txt
```

Run tests:

```powershell
python -m pytest
```

Mock preflight:

```powershell
python -m src.main preflight --mock
```

Mock collection:

```powershell
python -m src.main collect-file --signals-file data/sample_signals_today.csv --provider mock --duration-seconds 30
```

Summarize:

```powershell
python -m src.main summarize --run-folder data/runs/YYYY-MM-DD
```

IBKR preflight:

```powershell
python -m src.main preflight --provider ibkr
```

## Future Enhancement Notes

Likely next improvements:

1. Add async/streaming IBKR quote subscriptions to reduce polling overhead.
2. Add end-of-day news refresh.
3. Add market-hours stop conditions.
4. Add Discord/manual paste signal ingestion.
5. Add richer replay and backtest reports.
6. Add Streamlit or FastAPI dashboard.
7. Add statistical calibration after 20 to 50 collected signals.
