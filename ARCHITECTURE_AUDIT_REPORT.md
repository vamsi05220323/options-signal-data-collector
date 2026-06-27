# Architecture Audit Report

Audit date: 2026-06-27

Project: `options_alert_engine`

Audit mode: source, tests, configuration schema, and existing local artifacts only

Broker access: not attempted

Orders: not placed

Secrets: `.env.local` values and all account identifiers were excluded

## 1. Executive Summary

### What the application currently does

The application accepts one options signal from command-line fields or multiple signals from a CSV file. For each signal, it records the supplied signal time, underlying price, direction, strike, expiry, and optional premium. It then selects the original signal-side option plus several opposite-side contracts, obtains stock and option quotes from a selected provider, writes raw observations to CSV and SQLite, builds time bars, and creates contract-level and signal-level summaries.

The implemented providers are:

- IBKR through local TWS or IB Gateway using `ib_insync` in read-only mode.
- A deterministic mock provider for offline testing.
- A CSV replay provider class that is not wired into the CLI replay command.
- A deliberately unavailable Webull OpenAPI placeholder.

The application also has optional news modules for Alpha Vantage and Finnhub. Mock news is the default and is currently allowed to affect the score.

### What it does not do

- It does not place, stage, transmit, or manage broker orders.
- It does not auto-trade.
- It does not emit external alerts.
- It does not continuously ingest signals while an existing run is active.
- It does not backfill option bid/ask data between the real signal time and a later command start.
- It does not implement true historical replay; `replay` only rebuilds summaries.
- It does not calculate liquidity buckets, safe position size, volume since signal, immediate round-trip loss, or intrinsic-value violation flags.
- It does not explicitly label 40%, 50%, 100%, or 180% opportunity thresholds.
- It does not globally rank multiple signals or assign a rank number.

### What kind of application it is

It is primarily a **data collection and post-run research engine**. It also contains a rule-based opportunity score and summary selection logic. It is not presently an alert engine or trading engine despite legacy configuration names such as `ENABLE_ALERTS`, `SignalStatus.WATCH`, and the console `WATCH` label.

### Match to the original intent

The architecture substantially matches the collection intent: original signal details, stock quotes, option bid/ask/mid/last, volume, open interest, Greeks, quote sizes, spreads, conservative returns, CSV, SQLite, and multiple contract roles are present.

It does **not yet reliably answer the main business question** of whether opposite-side puts had executable 40%, 50%, 100%, or 180% opportunities. The most important reasons are:

1. Conservative return is calculated over all rows, including invalid quotes, and does not require the entry ask and exit bid rows themselves to be valid.
2. Signal-level `opposite_side_opportunity_found` can be triggered by the original signal-side contract because all contract roles are pooled.
3. Bid size, ask size, and traded volume are captured but are not used to establish executable size.
4. Intrinsic-value violations are not flagged; extrinsic value is clamped to zero and can hide the contradiction.
5. IBKR quote acquisition is serial. A representative ten-contract live artifact sampled each contract about every 12.2 seconds despite a configured one-second interval. Five signals and 25-40 contracts would be materially slower.
6. IBKR timestamps and quote age are locally fabricated as "now" and zero, so stale/delayed quote checks are ineffective.

### Can it support the research goal after 1-2 weeks?

Not safely in its current form. It can collect useful exploratory evidence, but a 1-2 week production research dataset should start only after the "Must fix before next live capture" items in Section 16 are resolved and regression-tested. Otherwise, the data can be retained as raw evidence but the opportunity conclusions may contain false positives, missed fast moves, and unverified liquidity assumptions.

### Major risks

| Risk | Severity | Business impact |
|---|---|---|
| Signal-side contracts can trigger an "opposite-side" opportunity | BLOCKER | Directly misclassifies the research outcome |
| Invalid quote rows can produce the reported conservative return | BLOCKER | A chart spike may be labeled executable when it was not |
| No 40/50/100/180 threshold outputs | HIGH | Core research question requires manual reconstruction |
| Serial IBKR sampling | HIGH | Fast moves can be missed, especially with five signals |
| No size/liquidity model despite captured sizes | HIGH | Cannot determine whether a return was scalable or only theoretical |
| No intrinsic violation flag | HIGH | Impossible/suspicious prices can pass into summaries |
| Quote timestamps/age are not source timestamps | HIGH | Stale and delayed data cannot be proven |
| Mock news affects real scoring and is fallback on provider failure | HIGH | Synthetic context can alter rankings |
| One signal/provider failure can abort a multi-signal batch | HIGH | Other valid signals can lose collection coverage |
| Daily default folder mixes separate runs | MEDIUM | Test and live signals can contaminate one summary |

## 2. Repository Inventory

### Git status

At audit start:

```text
## feature/ibkr-contract-resolution...origin/feature/ibkr-contract-resolution
```

The working tree was clean. The audit was moved to `audit/architecture-audit-2026-06-27`; this report is the only requested project file added.

### Project tree

Generated `.git/`, `.venv/`, `.pytest_cache/`, and `__pycache__/` internals are omitted. All tracked project files and local run folders are represented.

```text
options_alert_engine/
|-- .env.example
|-- .env.local                         # ignored; values not audited or printed
|-- .gitattributes
|-- .gitignore
|-- ARCHITECTURE_AUDIT_REPORT.md
|-- FEATURE_ENHANCEMENTS.md
|-- KNOWN_GAPS_AND_DECISIONS.md
|-- LAUNCH_GUIDE.md
|-- MARKET_DATA_AND_RUN_PLAN.md
|-- PROJECT_FLOW.md
|-- README.md
|-- requirements.txt
|-- data/
|   |-- .gitkeep
|   |-- sample_signals_today.csv
|   |-- sample_vrns.csv
|   `-- runs/                           # ignored generated data
|       |-- 2026-06-25/
|       |-- 2026-06-26/
|       |-- 2026-06-26_MAN_1413_CALL_10min/
|       `-- 2026-06-26_MAN_1413_CALL_10min_retry/
|-- scripts/
|   |-- ibkr_preflight.ps1
|   |-- mock_collect.ps1
|   |-- mock_preflight.ps1
|   |-- resolve_python.ps1
|   |-- run.ps1
|   |-- setup.ps1
|   |-- summarize_today.ps1
|   `-- test.ps1
|-- src/
|   |-- __init__.py
|   |-- config.py
|   |-- main.py
|   |-- models.py
|   |-- preflight.py
|   |-- engine/
|   |   |-- __init__.py
|   |   |-- capture_manager.py
|   |   |-- metrics.py
|   |   |-- quote_validation.py
|   |   |-- replay.py
|   |   |-- scoring.py
|   |   |-- signal_parser.py
|   |   |-- strike_selector.py
|   |   `-- summarizer.py
|   |-- news_providers/
|   |   |-- __init__.py
|   |   |-- alpha_vantage_news.py
|   |   |-- base.py
|   |   |-- finnhub_news.py
|   |   |-- mock_news.py
|   |   `-- yahoo_news.py
|   |-- providers/
|   |   |-- __init__.py
|   |   |-- base.py
|   |   |-- ibkr_provider.py
|   |   |-- mock_provider.py
|   |   |-- replay_provider.py
|   |   `-- webull_provider.py
|   |-- storage/
|   |   |-- __init__.py
|   |   |-- csv_writer.py
|   |   `-- sqlite_store.py
|   `-- ui/
|       |-- __init__.py
|       `-- live_console.py
`-- tests/
    |-- test_contract_identity.py
    |-- test_metrics.py
    |-- test_multi_signal.py
    |-- test_quote_validation.py
    |-- test_scoring.py
    |-- test_signal_parser.py
    |-- test_strike_selector.py
    `-- test_summarizer.py
```

### Important files

| File | Purpose |
|---|---|
| `src/main.py` | CLI parser and command dispatch |
| `src/config.py` | `.env`/`.env.local` loading and application defaults |
| `src/models.py` | Signals, contracts, quote/tick models, news models, enums |
| `src/preflight.py` | Mock/IBKR/Webull provider checks; writes non-secret settings to `.env.local` |
| `src/engine/capture_manager.py` | Main synchronous capture loop, per-signal runtime state, storage calls |
| `src/engine/signal_parser.py` | Text parser, CSV parser, expiry and time parsing, signal IDs |
| `src/engine/strike_selector.py` | Original and opposite-side strike/role selection |
| `src/engine/metrics.py` | Mid, spread, intrinsic, extrinsic, compression, rebound, returns |
| `src/engine/quote_validation.py` | Rule-based quote validity reasons |
| `src/engine/summarizer.py` | Bars and contract/signal summaries |
| `src/engine/scoring.py` | 70/20/10 rule-based score |
| `src/providers/ibkr_provider.py` | Read-only TWS/Gateway market-data adapter |
| `src/providers/mock_provider.py` | Offline synthetic quote paths |
| `src/providers/replay_provider.py` | Provider-like CSV reader, currently not used by CLI replay |
| `src/providers/webull_provider.py` | Safe, nonfunctional official-OpenAPI placeholder |
| `src/storage/csv_writer.py` | Exact CSV column definitions and writer |
| `src/storage/sqlite_store.py` | SQLite mirror; all columns are `TEXT` |
| `src/news_providers/*` | News fetch, catalyst classification, context scoring |
| `src/ui/live_console.py` | Console display only; no external alerting |
| `scripts/*.ps1` | Windows setup, launch, preflight, mock collection, test helpers |
| `README.md` | Concise operation guide |
| `PROJECT_FLOW.md` | File and flow documentation |
| `LAUNCH_GUIDE.md` | PowerShell/TWS launch guide |
| `MARKET_DATA_AND_RUN_PLAN.md` | IBKR subscriptions, costs, and schedule notes |
| `KNOWN_GAPS_AND_DECISIONS.md` | Existing design decisions and known issues |
| `FEATURE_ENHANCEMENTS.md` | Historical backfill and run-isolation backlog |

### Unused, duplicated, placeholder, broken, or stale items

| Item | Assessment |
|---|---|
| `src/engine/replay.py` | Thin unused wrapper; CLI calls `summarize_run` directly |
| `src/providers/replay_provider.py` | Implemented class but not exposed by `collect-*` or used by `replay` |
| `src/providers/webull_provider.py` | Intentional placeholder; always raises unavailable |
| `src/news_providers/yahoo_news.py` | Intentional disabled placeholder; never selected |
| `data/sample_vrns.csv` | Legacy schema incompatible with current `option_ticks.csv`; not in runtime path |
| `pydantic` dependency | Listed but not imported anywhere |
| `AppConfig.enable_alerts`/`enable_trading` | Loaded but not used; no alert/trade implementation exists |
| `aggressive_capture_minutes`/`normal_capture_seconds` | Loaded but unused |
| `min_compression_pct`/`min_rebound_pct` | Loaded but unused in decisions |
| `spread_max_pct` | Loaded, but capture uses hardcoded 35%/60% limits |
| `news_lookback_hours`/`news_context_days` | Loaded, but provider code hardcodes 24 hours/7 days |
| `news_refresh_minutes` | Loaded, but news is fetched only once |
| `stale_quote_seconds` | Loaded, but not passed into validation; validator default is always used |
| `RunStorage.create_daily` | Present but not called |
| `run_preflight(... assume_yes=...)` | Parameter is unused |
| `resolve_python.ps1` bundled path | Hardcoded to one Windows user profile; not portable |
| Fixed preflight expiry | Hardcoded `2026-07-17`; preflight will become stale after expiry |

### Trading, alerting, and credential review

- No `placeOrder`, order object, submit, cancel, bracket, or execution code was found.
- IBKR connects with `readonly=True`.
- `ENABLE_TRADING` and `ENABLE_ALERTS` are configuration-only fields and do not activate code.
- `WATCH` in the console is a display hint based on quote validity/rebound; it does not send an alert.
- No tracked hardcoded passwords, broker credentials, or populated API keys were found.
- `.env.local`, `.env`, SQLite files, and generated run folders are ignored by Git.
- IBKR username/password are neither requested nor stored.
- Alpha Vantage/Finnhub keys are passed as HTTP query parameters. Uncaught `requests` exceptions can include the request URL and therefore may expose a key in a traceback/log. This is a credential-handling risk to fix.

### Dependencies

`requirements.txt`:

```text
pandas>=2.2.0
requests>=2.31.0
pydantic>=2.7.0
python-dotenv>=1.0.1
rich>=13.7.1
pytest>=8.2.0
ib_insync>=0.9.86
```

Audited environment: Python 3.12.13, pandas 3.0.3, requests 2.34.2, pydantic 2.13.4, python-dotenv 1.2.2, rich 15.0.0, pytest 9.1.1, ib-insync 0.9.86. There is no lock file, hash pinning, package metadata, or CI workflow.

### `.env.example` keys

```text
DATA_PROVIDER
ENABLE_ALERTS
ENABLE_TRADING
TRACK_SIGNAL_CONTRACT
TRACK_EXACT_OPPOSITE
ITM_STRIKES_TO_TRACK
OTM_STRIKES_TO_TRACK
LOTTO_STRIKES_TO_TRACK
SNAPSHOT_INTERVAL_SECONDS
AGGRESSIVE_CAPTURE_MINUTES
NORMAL_CAPTURE_SECONDS
SPREAD_MAX_PCT
WIDE_SPREAD_MAX_PCT
MIN_COMPRESSION_PCT
MIN_REBOUND_PCT
TIMEZONE
IBKR_HOST
IBKR_PORT
IBKR_CLIENT_ID
ENABLE_NEWS
NEWS_PROVIDER
NEWS_LOOKBACK_HOURS
NEWS_CONTEXT_DAYS
NEWS_REFRESH_MINUTES
NEWS_MAX_ARTICLES_PER_SYMBOL
ALPHA_VANTAGE_API_KEY
FINNHUB_API_KEY
```

`DATA_DIR` and `STALE_QUOTE_SECONDS` are supported by code but missing from `.env.example`.

## 3. Entry Points and Commands

Primary entry point:

```powershell
.\.venv\Scripts\python.exe -m src.main <command> [options]
```

Recommended PowerShell wrapper:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run.ps1 <command> [options]
```

### `preflight`

```powershell
python -m src.main preflight [--mock] [--provider {ibkr,webull,mock}]
```

- Purpose: provider connectivity and one hardcoded stock/option availability check.
- Input: provider only; test signal is fixed in `src/preflight.py`.
- Providers: mock, IBKR, Webull placeholder.
- Writes: updates non-secret settings in `.env.local`; no run CSV/SQLite.
- Signal count: one hardcoded preflight signal.
- Mode: mock or live provider check.
- Audit result: command/help exists. It was not executed because IBKR access was prohibited and even mock preflight mutates `.env.local`. Code inspection confirms the path; prior run artifacts show IBKR collection has previously operated.
- Gap: detects missing stock/option bid/ask only by inference. It does not identify delayed mode, entitlement error codes, market-data-line exhaustion, or source quote age.

### `collect-signal`

```powershell
python -m src.main collect-signal `
  --symbol MRK --direction CALL --strike 110 --expiry 2026-07-17 `
  --signal-premium 0.40 --stock-price <price> `
  [--provider {ibkr,webull,mock}] `
  [--underlying-exchange SMART] [--primary-exchange NYSE] `
  [--currency USD] [--ibkr-con-id <id>] `
  [--signal-time now] [--start-time now] `
  [--end-time market-close | --duration-seconds 1800] `
  [--run-folder <path>] [--quiet]
```

- Purpose: collect exactly one signal.
- Required inputs: symbol, CALL/PUT, strike, expiry, and stock price at signal.
- Optional inputs: premium, provider, contract identity, timing, run folder.
- Provider: override or `DATA_PROVIDER`.
- Writes: all raw CSVs, news CSVs, bar CSVs, summaries, and SQLite.
- Mode: live IBKR, mock, or unavailable Webull.
- Signal count: one.
- Gap: it does not accept the raw text `MRK 110 CALL 7/17 @ 0.40`; fields must be split into flags.

### `collect-file`

```powershell
python -m src.main collect-file `
  --signals-file data\sample_signals_today.csv `
  [--provider {ibkr,webull,mock}] `
  [--start-time now] [--end-time market-close | --duration-seconds 1800] `
  [--run-folder <path>] [--quiet]
```

Required CSV columns:

```text
timestamp_local,symbol,direction,signal_strike,expiry,signal_premium,stock_price_at_signal
```

Optional identity columns:

```text
underlying_exchange,primary_exchange,currency,ibkr_con_id,ibkr_local_symbol,ibkr_trading_class
```

- Purpose: collect every CSV row in one shared capture loop.
- Provider/files/mode: same as `collect-signal`.
- Signal count: multiple; no fixed five-signal limit.
- Important behavior: all rows are registered before the loop, then sampled serially. It cannot add a new row while running.

### `replay`

```powershell
python -m src.main replay --run-folder data\runs\YYYY-MM-DD
```

- Actual purpose: call `summarize_run` on existing CSVs.
- Inputs: run folder containing signals/stock/option CSVs.
- Provider: none. `ReplayProvider` is not used.
- Writes: rewrites bar CSVs and summary CSVs; deletes and rebuilds corresponding SQLite summary/bar tables.
- Mode: summary rebuild, not timed replay.
- Audit result: command/help exists; summary logic is covered by tests. Not run against project data because audit mode prohibited modifying outputs.

### `summarize`

```powershell
python -m src.main summarize --run-folder data\runs\YYYY-MM-DD
```

- Purpose: same summary rebuild as `replay`, with output paths printed.
- Provider: none.
- Writes: same bar/summary CSVs and SQLite tables as `replay`.
- Signal count: every signal row in the folder.
- Mode: post-run summary.

### Tests

```powershell
python -m pytest
```

or:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\test.ps1
```

Audit execution used `python -m pytest -p no:cacheprovider`: **16 collected, 16 passed**.

## 4. End-to-End Flow

Example user signal:

```text
MRK 110 CALL 7/17 @ 0.40
```

### Detailed flow

1. **Input parsing**
   - The CLI does not parse that complete text.
   - The user supplies `--symbol MRK --direction CALL --strike 110 --expiry 2026-07-17 --signal-premium 0.40 --stock-price ...`.
   - `parse_signal_text()` can parse common text formats, but no command calls it.
   - `collect-file` parses one CSV row per signal.

2. **Signal ID**
   - CLI: `MRK_YYYYMMDD_HHMMSS`.
   - CSV/text parser: `MRK_YYYYMMDD_HHMMSS_CALL_110p0`, with `_2`, `_3`, etc. for duplicate CSV IDs.
   - Gap: two CLI signals for the same symbol in the same second can collide because direction/strike are omitted.

3. **Normalization**
   - Symbols are uppercase and a leading `$` is removed.
   - `C`/`CALL` and `P`/`PUT` normalize to enums.
   - Expiry accepts ISO, `M/D/YY`, `M/D/YYYY`, or `M/D` with year inference.
   - Bare times use `America/Chicago` by default and are DST-aware.

4. **Original signal contract**
   - If enabled, selector creates the exact requested strike and signal direction with role `SIGNAL_CONTRACT`.
   - It does not first verify that the signal-side strike exists in the returned chain.

5. **Opposite direction**
   - CALL becomes PUT; PUT becomes CALL.

6. **Opposite strike roles**
   - `EXACT_OPPOSITE`: available chain strike nearest the signal strike.
   - `ATM_OPPOSITE`: available strike nearest current/supplied stock price.
   - `ITM_OPPOSITE`: nearest unseen strikes in the ITM direction.
   - `OTM_OPPOSITE`: nearest unseen strikes in the OTM direction.
   - `LOTTO_OBSERVATION_ONLY`: next farther unseen OTM strikes after normal OTM selection.
   - Duplicate role/strike pairs are collapsed, so a strike receives only the first role selected.

7. **IBKR qualification**
   - Underlying is resolved through conId or contract details.
   - Selected stock contract identity is stored in `signals.csv`.
   - Option contracts are built with SMART/USD and qualified lazily on first quote.
   - Qualified option contracts are cached.

8. **Stock quote request**
   - `reqMktData(..., snapshot=False)` requests streaming data.
   - The code sleeps one second, reads the current ticker object, and writes one stock row.
   - If live `last` is missing, it uses close or the user-supplied stock price, which can make a non-live fallback appear current.

9. **Option quote request**
   - Generic ticks `100,101,106` request option volume, open interest, and implied volatility/Greeks data.
   - Code sleeps one second per contract and reads bid/ask/last/sizes/Greeks.

10. **Streaming versus polling**
    - IBKR subscriptions are streaming (`snapshot=False`).
    - Application persistence is polling-style: it serially samples ticker objects after a one-second sleep.
    - Subscriptions are not explicitly cancelled; disconnect releases them.

11. **Write interval**
    - A configured sleep occurs after a complete pass.
    - It is not the per-contract cadence. Existing ten-contract evidence shows about 12.2 seconds per contract.

12. **Raw storage**
    - Every returned stock tick and option tick is appended to CSV and SQLite and committed immediately.
    - Invalid quote rows are retained with reasons.
    - A contract qualification/provider error deactivates that contract and produces no failure row.

13. **Bars**
    - After capture, pandas resamples option ticks independently by signal/contract into 5-second, 1-minute, and 5-minute bars.
    - Bars include bid/ask/mid OHLC, tick count, valid ratio, and median spread.
    - There are no stock bars.

14. **Contract summaries**
    - Min/max bid/ask/mid, theoretical return, ask-to-future-bid return, compression, rebound, valid percentage, spreads, and tradability are calculated.

15. **Signal scoring**
    - A 70% microstructure, 20% news, 10% signal-side score is calculated per signal.
    - Rows are not globally sorted and no rank column is emitted.

16. **Outputs**
    - `signals.csv`, `stock_ticks.csv`, `option_ticks.csv`
    - `option_5sec_bars.csv`, `option_1min_bars.csv`, `option_5min_bars.csv`
    - `summary_by_contract.csv`, `summary_by_signal.csv`
    - `news_articles.csv`, `news_summary_by_signal.csv`
    - `market_capture.sqlite`

17. **Reviewer package**
    - Send the files ranked in Section 13, plus the exact command, run start/end, provider, market-data mode, timezone, and any stderr/stdout logs.

### Sequence diagram

```text
User signal/CSV
    |
    v
src.main -> signal_parser -> TradeSignal(s)
    |
    v
provider.connect -> provider.resolve_signal -> signals.csv/SQLite
    |
    v
provider option chain -> strike_selector -> OptionContract roles
    |
    +--> news provider -> news CSV/SQLite
    |
    v
capture loop (serial per signal, then serial per contract)
    |
    +--> stock reqMktData -> StockTick -> CSV/SQLite
    |
    +--> option reqMktData -> metrics + validation -> OptionTick -> CSV/SQLite
    |
    v
provider.close
    |
    v
summarizer -> bars + contract summaries -> scoring -> signal summaries
    |
    v
Reviewer receives summaries + raw evidence + database + logs
```

## 5. Data Provider Review

### IBKR

| Question | Audit result |
|---|---|
| Library | `ib_insync>=0.9.86` |
| TWS or Gateway | Either, through the local socket API |
| Host/port/client ID | `IBKR_HOST`, `IBKR_PORT`, `IBKR_CLIENT_ID`; defaults `127.0.0.1`, `7497`, `12` |
| Paper/live | No explicit mode flag; mode is determined by the TWS/Gateway socket port/session |
| Login | User must open and manually log into TWS/Gateway |
| Credentials stored | No broker credentials are requested or stored |
| Connection safety | `readonly=True` |
| Market-data request | Streaming subscription, sampled synchronously |
| Snapshot request | No; snapshot flag is false |
| Delayed data | Not requested, detected, or labeled |
| OPRA detection | Only inferred from missing option bid/ask in preflight |
| Underlying data detection | Only inferred from missing stock bid/ask |
| Pacing handling | None: no pacing error categorization, retry/backoff, or request scheduler |
| Market-data line handling | None: no line-budget calculation or error handling |
| Contract qualification | Underlying failure aborts; option failure deactivates that contract |
| Missing option bid/ask | Tick is stored and marked invalid if the provider still returns a quote object |
| Missing stock last | Falls back to close or user-supplied signal price |
| Quote timestamp | Local collection time, not exchange/source tick time |
| Quote age | Always zero in IBKR provider |
| Subscription cleanup | Disconnect only; no per-contract `cancelMktData` |

Important implementation risks:

- Repeated `reqMktData` calls are made in the sampling path.
- Every stock and option read waits one second, making five-signal capture slow.
- There is no IBKR error-event recorder, entitlement code recorder, farm status table, or market-data type field.
- Stock fallback can allow collection to continue without a genuine live last trade.
- Open interest chooses `putOpenInterest or callOpenInterest` rather than explicitly selecting by option type. Because zero is falsey, this can also mask a legitimate zero.

### Webull

- Only an official Webull OpenAPI placeholder exists.
- No unofficial scraping is implemented.
- It accepts constructor fields for key/secret/token but CLI/config never supplies them.
- `connect()` always raises that options quote support is not implemented.
- It cannot currently provide programmatic option bid/ask.
- It is safe by refusing to run, but should not be represented as a working provider.

### Mock and replay

- Mock provider is implemented and sufficient for deterministic offline development.
- Mock provider generates stock pump/failure and option compression/rebound paths.
- Tests can run without broker access.
- Replay provider can read current stock/option CSV rows, but the CLI `replay` command does not use it.
- Current replay is summary regeneration only, not time-controlled event replay.

## 6. Signal and Strike Selection Logic

### Implemented behavior

| Requirement | Result |
|---|---|
| Original signal-side option | Yes, exact requested strike/direction |
| Exact opposite | Yes, nearest available strike to signal strike |
| ATM opposite | Yes, nearest available strike to stock price |
| One ITM opposite | Configurable count; default one |
| Multiple OTM opposite | Configurable count; default five |
| Far OTM lotto | Configurable count; default one, chosen after normal OTM rows |
| Actual option-chain strikes | Yes when provider returns a chain |
| $1/$2.5/$5/irregular spacing | Yes when a real chain is available |
| Fallback spacing | Synthetic: $1 below $10, $2.50 from $10-$30, $1 above $30; not robust |
| Unavailable requested signal strike | Still creates it; IBKR qualification can fail and then no tick row is written |
| Stock between strikes | Nearest strike; exact tie chooses the lower strike |
| Configurable counts | `ITM_STRIKES_TO_TRACK`, `OTM_STRIKES_TO_TRACK`, `LOTTO_STRIKES_TO_TRACK` |

The chain request is made for the opposite direction argument, although IBKR security-definition parameters provide strike sets rather than quoteable right-specific contracts. Signal-side availability is therefore not separately validated.

### Examples

Assume a representative real chain; actual output depends on listed strikes.

**Stock 36, signal 40 CALL**

- Signal: 40C.
- Exact opposite: 40P.
- ATM: nearest to 36, for example 36P.
- ITM put: nearest unseen strike above 36, for example 37P.
- OTM puts: nearest strikes below 36, for example 35P, 34P, 33P, 32P, 31P.
- Lotto: next unseen farther OTM, for example 30P.

**Stock 140.82, signal 145 CALL**

- Signal: 145C.
- Exact opposite: 145P.
- ATM: nearest listed strike to 140.82, such as 140P, 141P, or 142.5P.
- ITM put: nearest unseen listed strike above 140.82.
- OTM puts: listed strikes immediately below 140.82, descending.
- Lotto: next farther listed OTM strike.

**Stock 44.64, signal 60 CALL**

- Signal: 60C.
- Exact opposite: 60P, which is deeply ITM.
- ATM: nearest listed strike to 44.64, often 45P.
- ITM put: nearest unseen strike above 44.64. If 45P is already ATM, the selector skips it and takes the next ITM strike.
- OTM puts: nearest listed strikes below 44.64.
- Lotto: farther OTM after the configured normal OTM set.

### Gaps

- The original signal contract is not snapped to or validated against the chain.
- Role deduplication means a contract that is both ATM and ITM is labeled only ATM; the reviewer loses overlapping semantic roles.
- Synthetic fallback can generate nonexistent contracts and trigger qualification failures.
- Expiration/trading-class ambiguity is not resolved from a specific IBKR option-chain class.

## 7. Multi-Signal Handling

| Question | Audit result |
|---|---|
| Can it accept five signals? | Yes, through `collect-file` |
| How are five ingested? | Five CSV rows are parsed before capture begins |
| Does `collect-file` exist? | Yes |
| Can it represent 25-40 contracts? | Yes in memory/storage; sampling performance is inadequate |
| Independent signal state? | Yes: each `SignalRuntime` has its own stock high/low and contracts |
| Independent stock high/low? | Yes, but initialized from supplied signal price rather than first observed live tick |
| Independent contract min/max? | Yes, per `ContractRuntime` |
| Multiple-signal ranking? | Scores are calculated independently; no cross-signal sort or rank column |
| One signal behavior | One summary row and its contract rows |
| All five fail | All may be false/skipped, unless a provider exception aborts the batch |
| Zero fail | All five may be true; no one-winner assumption exists |
| Only one winner assumed? | No |

Critical limitations:

1. Signals cannot be added dynamically. If alerts arrive minutes apart, the user must run another command. The default daily folder then appends to existing raw files and rebuilds combined summaries.
2. A failure in `resolve_signal`, stock quote retrieval, news HTTP call, or other uncaught provider operation can abort the entire batch.
3. Option quote errors are handled per contract, but the failed contract is silently deactivated after a console message and has no structured error row.
4. Sampling is serial. At one second per stock/contract, five signals and 25-40 options can take roughly 30-50+ seconds per pass before the configured loop sleep and network overhead.
5. `signal_id` and contract keys preserve logical separation, but SQLite has no keys, uniqueness constraints, or indexes.

## 8. Captured Fields

### Exact CSV columns

`signals.csv`:

```text
signal_id,timestamp_local,symbol,direction,signal_strike,expiry,signal_premium,stock_price_at_signal,opposite_direction,provider,status,underlying_exchange,primary_exchange,currency,ibkr_con_id,ibkr_local_symbol,ibkr_trading_class,contract_resolution_status,contract_resolution_message
```

`stock_ticks.csv`:

```text
timestamp_local,signal_id,symbol,stock_bid,stock_ask,stock_last,stock_mid,stock_volume,seconds_since_signal,stock_price_at_signal,post_signal_high,post_signal_low,stock_change_from_signal_pct,pump_from_signal_pct,pullback_from_high_pct
```

`option_ticks.csv`:

```text
timestamp_local,signal_id,underlying_symbol,option_symbol,option_con_id,option_local_symbol,option_trading_class,option_exchange,contract_role,expiry,strike,option_type,bid,ask,mid,last,volume,open_interest,implied_volatility,delta,gamma,theta,vega,bid_size,ask_size,spread_abs,spread_pct,intrinsic_value,extrinsic_value,quote_timestamp,quote_age_seconds,quote_is_valid,reason_invalid,seconds_since_signal,option_initial_mid,option_min_mid_since_signal,option_max_mid_since_signal,option_min_ask_since_signal,option_max_bid_since_signal,compression_from_initial_pct,rebound_from_low_pct
```

All three option bar files use:

```text
bar_start,signal_id,underlying_symbol,option_symbol,contract_role,expiry,strike,option_type,open_mid,high_mid,low_mid,close_mid,open_bid,high_bid,low_bid,close_bid,open_ask,high_ask,low_ask,close_ask,ticks,valid_quote_ratio,median_spread_pct
```

`summary_by_contract.csv`:

```text
signal_id,underlying_symbol,option_symbol,contract_role,expiry,strike,option_type,min_mid_after_signal,max_mid_after_signal,min_ask_after_signal,max_bid_after_signal,best_theoretical_mid_return,best_conservative_ask_to_bid_return,time_of_min_ask,time_of_max_bid_after_min_ask,max_compression_pct,max_rebound_pct,percentage_of_valid_quotes,median_spread_pct,max_spread_pct,best_quote_valid,was_best_move_tradable
```

`summary_by_signal.csv`:

```text
signal_id,symbol,best_contract_by_mid_return,best_contract_by_conservative_return,best_ATM_or_OTM_contract,best_lotto_contract,number_of_valid_contracts,number_of_untradable_contracts,signal_direction_stock_result,opposite_side_opportunity_found,opportunity_score,news_provider,news_count_24h,news_count_7d,latest_news_age_minutes,catalyst_detected,catalyst_type,news_bias,news_score,top_headlines_24h,news_skip_warning,skip_reason
```

`news_articles.csv`:

```text
timestamp_collected,signal_id,symbol,provider,article_published_at,article_age_minutes_at_signal,source,headline,summary,url,related_tickers,sentiment_label,sentiment_score,relevance_score,catalyst_type,is_within_24h,is_within_7d
```

`news_summary_by_signal.csv`:

```text
signal_id,symbol,signal_timestamp_local,news_provider,news_count_24h,news_count_7d,latest_news_age_minutes,positive_news_count_24h,negative_news_count_24h,neutral_news_count_24h,avg_sentiment_24h,avg_relevance_24h,top_sources_24h,top_headlines_24h,catalyst_detected,catalyst_type,news_bias,news_score,news_skip_warning,news_notes
```

### Required signal fields

| Field | Status | Notes |
|---|---|---|
| signal_id | IMPLEMENTED | CLI ID has collision risk |
| timestamp_local | IMPLEMENTED | Supplied/parsed local time |
| symbol | IMPLEMENTED | Normalized |
| direction | IMPLEMENTED | CALL/PUT |
| signal_strike | IMPLEMENTED | Float |
| expiry | IMPLEMENTED | Date |
| signal_premium | IMPLEMENTED | Optional |
| stock_price_at_signal | IMPLEMENTED | User supplied |
| opposite_direction | IMPLEMENTED | Derived |
| provider | IMPLEMENTED | Stored on signal |
| status | PARTIALLY IMPLEMENTED | Always remains `COLLECTING`; never transitions |

### Required stock fields

| Field | Status | Notes |
|---|---|---|
| timestamp_local | IMPLEMENTED | Collection time |
| signal_id | IMPLEMENTED | Per signal |
| symbol | IMPLEMENTED | Underlying |
| stock_bid/ask/last/mid | IMPLEMENTED | Last may fall back to close/signal price in IBKR |
| stock_volume | PARTIALLY IMPLEMENTED | Provider volume, generally cumulative day volume; semantics unlabeled |
| seconds_since_signal | IMPLEMENTED | Negative values are clamped to zero |
| stock_price_at_signal | IMPLEMENTED | Supplied value |
| post_signal_high/low | PARTIALLY IMPLEMENTED | Initialized with supplied signal price; late-entry gap is not observed |
| stock_change_from_signal_pct | IMPLEMENTED | Last versus signal price |
| pump_from_signal_pct | PARTIALLY IMPLEMENTED | Uses high initialized from supplied price |
| pullback_from_high_pct | PARTIALLY IMPLEMENTED | Same historical-gap limitation |

### Required option fields

| Field | Status | Notes |
|---|---|---|
| timestamp_local | IMPLEMENTED | Local sampling time |
| signal_id | IMPLEMENTED | Per signal |
| underlying_symbol | IMPLEMENTED | Yes |
| option_symbol | IMPLEMENTED | IBKR local/storage symbol |
| contract_role | IMPLEMENTED | Enum role |
| expiry/strike/option_type | IMPLEMENTED | Yes |
| bid/ask/mid/last | IMPLEMENTED | Missing values retained |
| volume | PARTIALLY IMPLEMENTED | Cumulative provider value, not volume since signal |
| open_interest | PARTIALLY IMPLEMENTED | Captured; IBKR side-selection uses `or` rather than explicit option type |
| implied_volatility | IMPLEMENTED | Model/bid/ask Greeks source |
| delta/gamma/theta/vega | IMPLEMENTED | May be absent |
| bid_size/ask_size | IMPLEMENTED | Captured but unused in validity/scoring |
| spread_abs/spread_pct | IMPLEMENTED | Crossed markets are mishandled; see Section 9 |
| intrinsic_value | IMPLEMENTED | Based on sampled/fallback stock last |
| extrinsic_value | PRESENT BUT WRONG | Clamped to zero, concealing negative/intrinsic violation |
| quote_timestamp | PRESENT BUT WRONG | IBKR sets it to local collection time |
| quote_age_seconds | PRESENT BUT WRONG | IBKR always sets zero |
| quote_is_valid/reason_invalid | PARTIALLY IMPLEMENTED | Important checks missing |
| seconds_since_signal | IMPLEMENTED | Negative clamped to zero |
| option_initial_mid | PARTIALLY IMPLEMENTED | First captured mid, even invalid and possibly late |
| option_min/max_mid | PARTIALLY IMPLEMENTED | Includes invalid rows |
| option_min_ask/max_bid | PARTIALLY IMPLEMENTED | Includes invalid rows |
| compression_from_initial_pct | PARTIALLY IMPLEMENTED | Correct formula, unreliable inputs possible |
| rebound_from_low_pct | PARTIALLY IMPLEMENTED | Correct formula, unreliable inputs possible |

### Required liquidity fields

| Field | Status | Notes |
|---|---|---|
| volume_today | PARTIALLY IMPLEMENTED | Named `volume`; semantics not explicit |
| open_interest | IMPLEMENTED | With side-selection caveat |
| bid_size | IMPLEMENTED | Not used |
| ask_size | IMPLEMENTED | Not used |
| immediate_round_trip_loss_pct | MISSING | Derivable but not stored |
| valid_bid_exists | MISSING | Only implicit in validation reason |
| valid_ask_exists | MISSING | Only implicit in validation reason |
| exit_bid_available | MISSING | No explicit field/rule |
| volume_since_signal | MISSING | No baseline/delta calculation |
| volume_per_minute_since_signal | MISSING | No calculation |
| liquidity_score | MISSING | No model |
| liquidity_bucket | MISSING | No model |
| max_safe_contracts_estimate | MISSING | No size model |
| max_safe_dollars_estimate | MISSING | No size model |
| position_size_bucket | MISSING | No model |

### SQLite

Tables:

```text
signals
stock_ticks
option_ticks
option_bars_5sec
option_bars_1m
option_bars_5m
contract_summary
signal_summary
news_articles
news_summary_by_signal
```

Each table mirrors the corresponding CSV fields. Every SQLite column is `TEXT`; there are no primary keys, foreign keys, uniqueness constraints, indexes, schema version, or run metadata table.

## 9. Calculations and Formulas

| Calculation | File/function | Formula | Inputs | Output | Assessment |
|---|---|---|---|---|---|
| Mid | `metrics.compute_mid` | `(bid + ask) / 2` | bid, ask | mid | Correct for normal markets; crossed markets not rejected |
| Spread absolute | `metrics.compute_spread_abs` | `max(ask - bid, 0)` | bid, ask | spread_abs | Wrong for crossed-market detection because negative spread becomes zero |
| Spread percent | `metrics.compute_spread_pct` | `spread_abs / mid * 100` | bid, ask, mid | spread_pct | Standard mid-based spread; crossed market can look perfect |
| Put intrinsic | `metrics.intrinsic_value` | `max(strike - stock, 0)` | type, strike, stock | intrinsic_value | Correct |
| Call intrinsic | `metrics.intrinsic_value` | `max(stock - strike, 0)` | type, strike, stock | intrinsic_value | Correct |
| Extrinsic | `metrics.extrinsic_value` | `max(mid - intrinsic, 0)` | mid, intrinsic | extrinsic_value | Numerically nonnegative but hides violations; raw difference/flag needed |
| Stock change | `metrics.percent_change` | `(current - base) / base * 100` | last/high, signal price | change/pump | Correct when inputs are genuine |
| Compression | `metrics.premium_compression_pct` | `max(0,(initial_mid-min_mid)/initial_mid*100)` | initial, min | compression | Correct; includes invalid quotes and late start |
| Rebound | `metrics.rebound_from_low_pct` | `max(0,(current_mid-min_mid)/min_mid*100)` | current, min | rebound | Correct; includes invalid quotes |
| Conservative return helper | `metrics.conservative_ask_to_bid_return` | `future_bid / earlier_ask - 1` | ask, later bid | return | Correct, but summarizer reimplements it |
| Best conservative return | `summarizer.best_ask_to_future_bid` | max of `future bid / earlier ask - 1` with future index >= entry index | all ask/bid rows | best return/times | Temporal order is correct; does not filter invalid quotes, require size, or require later time |
| Theoretical return | `summarizer.build_contract_summary` | `max_mid / min_mid - 1` | all mids | theoretical return | Weak: ignores temporal order and quote validity |
| Valid quote percentage | `build_contract_summary` | mean(valid boolean) * 100 | quote_is_valid | percentage | Correct aggregation, but underlying validation is incomplete |
| Tradable move | `build_contract_summary` | return > 20%, valid ratio >= 50%, median spread <= wide max | summaries | boolean | Insufficient: winning entry/exit rows need not be valid |
| Immediate round-trip loss | none | expected `bid/ask - 1` or `(ask-bid)/ask` | bid, ask | missing | MISSING |
| Liquidity score | none | none | size, volume, OI, spread | missing | MISSING |
| Opportunity score | `scoring.score_signal` | `0.70*microstructure + 0.20*news + 0.10*signal_side` | summaries/news/stock | 0-100 score | Implemented but not calibrated and role filtering is wrong |
| Intrinsic violation | none | expected `intrinsic > selected option value + tolerance` | intrinsic, bid/ask/mid/last | missing | MISSING |

### Opportunity score details

Microstructure points:

```text
min(max(best_return, 0) * 100, 35)
+ min(best_compression / 2, 15)
+ min(best_rebound / 3, 15)
+ min(valid_contract_count * 4, 20)
+ max(0, 15 - median_spread / 4)
+ 10 if stock result is PUMP_THEN_FAILED
capped at 100
```

Then:

```text
total = microstructure * 0.70
      + news_score * 0.20
      + signal_side_score * 0.10
```

`signal_side_score` is 65 when conservative signal-contract return is negative, 60 when theoretical return is negative, otherwise 45. Opportunity is true when pooled best return is greater than 20% and at least one pooled contract has at least 50% valid quotes.

### Intrinsic-value example

Given stock 44.64 and 60P:

```text
intrinsic = max(60 - 44.64, 0) = 15.36
```

If displayed mid or last is 14.10, current code calculates:

```text
extrinsic = max(14.10 - 15.36, 0) = 0
```

It does **not** flag the 1.26 intrinsic shortfall. If bid/ask spread and volume/OI checks pass, the quote can be marked valid. This is a HIGH gap because stale stock, delayed option data, bad contract identity, or a bad quote can contaminate the research result.

## 10. Quote Validity and Liquidity Logic

### Current invalid reasons

`missing_bid`, `missing_ask`, `ask_lte_zero`, `bid_lt_zero`, `mid_lte_zero`, `missing_spread`, `spread_too_wide`, `penny_bid_wide_ask`, `stale_quote`, and `no_volume_or_open_interest`.

### Required cases

| Case | Status | Behavior |
|---|---|---|
| Bid missing | IMPLEMENTED | Invalid |
| Ask missing | IMPLEMENTED | Invalid |
| Ask <= 0 | IMPLEMENTED | Invalid |
| Mid <= 0 | IMPLEMENTED | Invalid |
| Penny bid/wide ask | IMPLEMENTED | Invalid at bid <= .01, ask >= .10, ratio >= 8 |
| Spread too wide | IMPLEMENTED | 35% normal, 60% lotto, hardcoded |
| Stale quote | PARTIALLY IMPLEMENTED | Rule exists, IBKR age always zero |
| No volume | PARTIALLY IMPLEMENTED | Valid when OI exists; lotto exempt |
| No open interest | PARTIALLY IMPLEMENTED | Valid when volume exists; lotto exempt |
| Below intrinsic | MISSING | Not checked |
| Crossed market | PRESENT BUT WRONG | Negative spread clamped to zero; not invalidated |
| Locked market | MISSING | Not labeled; can be valid |
| Delayed data | MISSING | No market data type/status field |
| Ask size too small | MISSING | Size captured only |
| Bid size too small | MISSING | Size captured only |

### Storage of bad quotes

- Missing/wide/stale quote objects are retained and marked invalid, which is correct for research.
- Provider/qualification exceptions are not retained as structured quote/error rows. The contract becomes inactive and disappears from subsequent evidence.
- Runtime min/max/compression state updates before validation, so invalid quotes still affect derived fields.
- Contract summary min/max/returns also include invalid rows.

### Liquidity buckets

None of the requested buckets exists:

```text
LIQUID_SCALABLE
LIQUID_SMALL_SIZE_ONLY
LOTTO_EXPERIMENT_ONLY
UNTRADABLE_WIDE_SPREAD
UNTRADABLE_NO_EXIT_BID
```

None of the requested position-size buckets exists:

```text
NO_TRADE
MICRO_ONLY
SMALL_ONLY
NORMAL_SMALL
SCALABLE
```

The app does not estimate safe size from bid size, ask size, or volume since signal. Current `was_best_move_tradable` means only that a pooled return/validity/spread rule passed; it does not prove executable quantity.

## 11. News Module Review

| Capability | Status |
|---|---|
| Alpha Vantage | Implemented with API key |
| Finnhub | Implemented with API key |
| Yahoo fallback | Disabled placeholder, never selected |
| Mock news | Implemented and default |
| 24-hour lookback | Implemented in summary logic; provider fetch window is seven days |
| 7-day context | Implemented, hardcoded |
| News bias | Implemented from positive/negative counts |
| Catalyst classification | Implemented by keyword rules |
| News score | Implemented: 75/58/50/35/45 by bias |
| Affects opportunity score | Yes, 20% weight |
| Refresh | No; fetched once per signal despite config field |

Major concerns:

1. If the configured provider is absent/misconfigured, `_news_provider_from_config` silently returns mock.
2. If a provider raises `NewsProviderError`, capture falls back to mock and synthetic news affects the score.
3. Normal `requests` failures are not wrapped as `NewsProviderError`; they can abort capture.
4. API keys are query parameters and can appear in unhandled exception URLs/logs.
5. Finnhub rows have no sentiment calculation, so they generally become `UNKNOWN` with score 45.
6. The mock article explicitly says it is synthetic, but its score still contributes 20%.
7. Configured lookback/refresh values are not honored.

News is not a blocker for raw quote collection. It is a blocker for trusting the current composite score unless mock/failure context is excluded or explicitly labeled non-scorable.

## 12. Ranking and Opportunity Scoring

### What is ranked/selected

| Output | Status |
|---|---|
| Contracts within one signal by theoretical return | Best symbol emitted, but not full ordered ranking |
| Contracts within one signal by conservative return | Best symbol emitted, but not full ordered ranking |
| Multiple signals against each other | MISSING; output preserves signal input order |
| Best ATM/OTM candidate | Implemented by conservative return |
| Best lotto candidate | Implemented by conservative return |
| Best liquidity-adjusted candidate | MISSING |
| Best small-size candidate | MISSING |
| Best scalable candidate | MISSING |
| Signals to skip | Boolean/skip reason implemented |
| Explicit 40/50/100/180 categories | MISSING |

### Inputs currently used

- Best conservative ask-to-bid return across all contract roles.
- Maximum compression across all contract roles.
- Maximum rebound across all contract roles.
- Count of contracts with at least 50% valid quotes.
- Median contract spread.
- Stock pump-then-failed classification.
- News score.
- Original signal-side contract weakness.

Bid/ask quality influences the score indirectly through median spread and valid-contract count. Volume, open interest, bid size, ask size, exit size, volume since signal, and liquidity buckets do not influence it.

### Critical scoring defects

1. `score_signal` pools `SIGNAL_CONTRACT` and every opposite role when finding best return, compression, rebound, spread, and valid count.
2. `opposite_side_opportunity_found` therefore does not prove an opposite-side move.
3. `best_contract_by_conservative_return` can be the original signal contract.
4. Best return can come from invalid entry/exit quote rows.
5. News can be synthetic and still contribute 20%.
6. Score is hand-tuned, not calibrated against outcomes, and is not a probability.
7. Opportunity threshold is only >20%, not the requested 40/50/100/180 levels.

### One versus five signals

- One signal: its contracts are summarized and one score is emitted.
- Five signals: five independent scores are emitted in input order; the application does not sort or label rank 1-5.
- The app does not assume one winner. All five can be true, all five can be skipped, or any combination can occur.
- A batch-level provider exception can prevent those independent outcomes from being completed.

## 13. Output Review: What to Send to the Reviewer

1. **`summary_by_signal.csv`** - first index of signals, scores, outcomes, and skip reasons. Warn the reviewer that current opportunity logic has the role/validity defects described above.
2. **`summary_by_contract.csv`** - contract-level returns, timing, spread, validity ratio, and role. Essential for checking the signal-level conclusion.
3. **`option_ticks.csv`** - primary execution evidence. Required to independently recompute valid ask-to-later-valid-bid returns and intrinsic checks.
4. **`stock_ticks.csv`** - underlying path and pump/pullback evidence.
5. **`signals.csv`** - source signal facts, broker contract resolution, provider, and supplied stock price/time.
6. **`market_capture.sqlite`** - full machine-readable mirror for repeatable queries. It is useful despite all-TEXT schema limitations.
7. **`option_1min_bars.csv` and `option_5min_bars.csv`** - convenient chart/review views. Do not substitute them for raw ticks.
8. **`option_5sec_bars.csv`** - higher-resolution chart view; in slow serial runs it may contain only one tick per bar.
9. **`news_summary_by_signal.csv` and `news_articles.csv`** - send only with the provider clearly labeled. Mock rows are not real evidence.
10. **stdout/stderr/provider logs** - required when contracts disappear, farm connectivity changes, entitlements fail, or the run ends early.

Also send a small `run_context.txt` or message containing:

- Exact command.
- Local timezone.
- Supplied signal time versus actual process start/end.
- TWS or Gateway and paper/live session type.
- Whether market data was confirmed live or delayed.
- Active stock/options subscriptions.
- Expected versus captured signal and contract counts.

Compression guidance:

- Compress `option_ticks.csv`, `stock_ticks.csv`, `option_5sec_bars.csv`, logs, and SQLite together for longer/multi-signal runs.
- Summaries, signals, and news summaries are normally small enough to send uncompressed.
- Do not send `.env.local`, TWS settings exports, credentials, or account screenshots.

## 14. Testing Review

### Test execution

```text
Platform: Windows
Python: 3.12.13
pytest: 9.1.1
Collected: 16
Passed: 16
Failed: 0
Duration: 2.33s
Broker/network calls: none
```

### Existing coverage

| Area | Existing test |
|---|---|
| Signal parser | Standard/compact text, expiry inference, CSV identity, runtime times |
| Strike selector | Roles and irregular chain grid |
| Multi-signal capture | Two mock signals produce summary |
| Quote validity | Penny-wide rejection and lotto no-volume allowance |
| Intrinsic/extrinsic | Basic put example |
| Spread | Basic mid-based percentage |
| Conservative return | Future bid after earlier ask |
| Opportunity scoring | One positive synthetic case |
| Summary generation | Tradable move and news fields |
| Contract identity | Selected contracts carry currency/primary exchange |

### Missing critical tests

- No test proving `opposite_side_opportunity_found` excludes `SIGNAL_CONTRACT`.
- No test proving conservative return uses only valid entry and exit rows.
- No tests for 40%, 50%, 100%, and 180% threshold labels.
- No crossed-market, locked-market, intrinsic-violation, delayed, stale IBKR, or missing-size tests.
- No liquidity score/bucket or position-size tests because features are absent.
- No test for volume-since-signal or volume-per-minute.
- No five-signal/40-contract cadence, fairness, or performance test.
- No test where one signal fails while other signals continue.
- No IBKR provider tests with a mocked `IB` object for pacing, market-data type, contract failure, or subscription cleanup.
- No CLI integration tests for each command.
- No test for duplicate CLI signal IDs or duplicate daily-folder data.
- No test for unavailable requested signal strike.
- No temporal-order test for theoretical mid return.
- No test that mock news is excluded from live scoring.
- No API-key redaction/error handling test.
- No SQLite type/key/index or CSV/SQLite parity test.

The current green suite is useful but too small to certify the business conclusion.

## 15. Gaps Against Original Requirement

| Requirement | Implemented? | Evidence/File | Gap | Severity | Fix recommendation |
|---|---|---|---|---|---|
| Pure data collection | Yes | `src/engine/capture_manager.py` | Scoring is also automatic but no execution | LOW | Keep collection and scoring clearly separated |
| No auto-trading | Yes | `IBKRProvider.connect(readonly=True)`; no order code | Safety flags are unused but harmless | LOW | Add a regression test that provider remains read-only |
| IBKR live quotes | Partial | `src/providers/ibkr_provider.py` | No live/delayed label; timestamps fabricated | HIGH | Record market-data type and source timestamps/errors |
| Original signal call tracking | Yes | `strike_selector.py` | Unavailable strike not validated | MEDIUM | Validate against the chain and record failure |
| Opposite put tracking | Yes for CALL signals | `OptionType.opposite`, selector | Summary pools signal-side and opposite-side | BLOCKER | Filter all opposite analysis by role/type |
| ATM/ITM/OTM/lotto | Yes | `strike_selector.py` | Overlapping roles collapsed | LOW | Preserve role flags or document precedence |
| Multi-signal tracking | Partial | `collect-file`, `SignalRuntime` | Serial and batch-fragile; no dynamic add | HIGH | Concurrent subscriptions and per-signal fault isolation |
| Bid/ask/mid/last | Yes | `OPTION_TICK_FIELDS` | Missing source timestamp/type | HIGH | Add source metadata and validation |
| Bid size/ask size | Partial | `OptionTick` | Captured but unused | HIGH | Use in validity and size estimates |
| Volume/OI | Partial | IBKR generic ticks | No deltas; OI side selection weak | HIGH | Explicit side fields and volume baseline |
| Conservative ask-to-bid return | Partial | `best_ask_to_future_bid` | Uses invalid rows and no size | BLOCKER | Require valid, non-stale, sized entry/exit rows |
| Quote validity | Partial | `quote_validation.py` | No crossed/locked/intrinsic/delay/size checks | HIGH | Expand validation and tests |
| Liquidity bucket | No | None | Entire model absent | HIGH | Add research-only liquidity classification |
| Opportunity score | Partial | `scoring.py` | Role pooling, synthetic news, uncalibrated | BLOCKER | Correct role/validity inputs before use |
| 40/50/100/180 analysis | No | None | Only >20% boolean | HIGH | Emit threshold flags using executable return |
| Daily CSV outputs | Yes | `RunStorage` | Daily folder mixes separate runs | MEDIUM | Unique run IDs/manifests and explicit aggregation |
| SQLite outputs | Yes | `sqlite_store.py` | All TEXT; no keys/indexes/version | MEDIUM | Typed schema, indexes, run metadata |
| Replay mode | No, summary alias only | `main.py`, `engine/replay.py` | No timed/event replay | MEDIUM | Rename now; build true replay later |
| Summary mode | Yes | `summarizer.py` | Current formulas need correction | HIGH | Fix validity/role/temporal logic |
| Preflight mode | Partial | `preflight.py` | Fixed expiry, weak diagnostics, mutates env | HIGH | Dynamic liquid test contract and structured diagnostics |
| News module | Partial | `news_providers/*` | Mock affects score; error/key risks | HIGH | Disable mock scoring and sanitize exceptions |
| Tests | Partial | `tests/*` | 16 pass; business-critical cases absent | HIGH | Add tests listed in Section 14 |
| README | Yes | `README.md` | Overstates replay and does not warn about score defects | MEDIUM | Update after fixes; clearly label experimental outputs |

## 16. Recommended Next Fixes

### Must fix before next live capture

1. Restrict opposite-side summaries and `opposite_side_opportunity_found` to opposite contracts only; never let `SIGNAL_CONTRACT` trigger the result.
2. Compute conservative return only from entry and later exit rows that are individually valid, non-crossed, non-stale, and have positive ask/bid. Preserve the raw all-quote metric under a different name if useful.
3. Add intrinsic-value violation fields and invalidate suspicious quotes with a documented tolerance.
4. Record IBKR market-data type, error codes, farm/entitlement failures, and genuine source timestamps where available. Do not write quote age as zero without evidence.
5. Stop using locally supplied stock price as a silent current quote fallback during live capture. Record fallback status explicitly or fail that sample.
6. Prevent mock news from affecting a live opportunity score. Provider failure should produce `NEWS_UNAVAILABLE`, not synthetic context.
7. Isolate provider/contract failures so one signal does not abort all signals, and write structured failure rows/logs.
8. Add tests for every item above before another research run.

### Should fix before 1-week data collection

1. Replace serial one-second-per-contract sampling with one subscription per contract and event-driven or batched periodic snapshots.
2. Add explicit 40%, 50%, 100%, and 180% executable-return flags and timestamps.
3. Add immediate round-trip loss, volume baseline/delta, volume per minute, bid/ask size checks, liquidity score/buckets, and conservative safe-size estimates.
4. Add unique run folders/manifests and prevent accidental test/live aggregation.
5. Add dynamic/prevalidated expiration and trading-class selection.
6. Add typed/indexed SQLite schema and run/provider metadata.
7. Add five-signal/40-contract load testing and measured cadence acceptance criteria.
8. Pin dependencies with a reproducible lock strategy and add CI.
9. Make preflight read-only with respect to `.env.local`, use a non-expired configurable test symbol/expiry, and report live/delayed status.
10. Redact API keys from all news exceptions/logging and wrap network errors.

### Can wait until later

1. True historical replay with controllable clock speed.
2. Historical backfill for late-entered signals, subject to IBKR historical option-data limitations.
3. Dashboard/visual analytics.
4. Dynamic signal ingestion while a collector stays running.
5. More sophisticated catalyst NLP and calibrated statistical models.
6. Export packages and reviewer automation.

### Do not build yet

- Auto-trading or order placement.
- Broker order staging.
- Automated buy/sell alerts based on the current score.
- Position sizing that can transmit orders.
- Claims that the opportunity score is a probability or investment recommendation.

## 17. Reviewer Questions

The source audit is complete. These operational answers are still needed to certify a specific live run:

1. Which exact IBKR market-data subscriptions were active on the run date, including OPRA and underlying equity top-of-book?
2. Did TWS label the stock and option quotes as live, delayed, frozen, or delayed-frozen?
3. Was the session paper or live, and was TWS or IB Gateway used? Do not provide account identifiers.
4. What exact collection command was run, with secrets and account details removed?
5. What were the provider, local timezone, supplied signal time, actual process start, and actual process end?
6. Was `collect-signal` or `collect-file` used, and how many signals were expected?
7. How many signals, contracts, stock rows, and option rows were actually produced?
8. Did stderr/stdout contain IBKR farm, pacing, entitlement, qualification, or market-data-line errors?
9. Did every expected contract have at least one tick and a resolved local symbol/trading class?
10. Was news disabled, real-provider, unavailable, or mock for that run?
11. Was a unique run folder used, or was data appended to a daily folder containing earlier tests?
12. Did the reviewer receive the SQLite database and raw ticks, not only the summaries?

## 18. Final Verdict

# PARTIALLY_READY_NEEDS_FIXES

The project is a meaningful, well-scoped foundation for read-only options research. It has real strengths: no trading code, read-only IBKR connectivity, actual option-chain strike selection, original/opposite contract roles, raw bid/ask and size capture, retained invalid quotes, CSV plus SQLite storage, bars, summaries, contract identity, time controls, mock testing, and 16 passing tests.

It is not yet ready for a 1-2 week dataset whose summaries will be treated as evidence of executable opposite-side 40%, 50%, 100%, or 180% opportunities. The current role pooling, invalid-row return calculation, absent liquidity/size model, missing intrinsic violation check, fabricated quote age, serial cadence, and synthetic-news scoring are material defects. Raw collection can continue only as exploratory data with these limitations clearly disclosed; reviewer-grade collection should begin after the BLOCKER and HIGH pre-capture fixes are implemented and tested.
