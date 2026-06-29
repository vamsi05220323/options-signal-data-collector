# Fix Blockers Report

Date: 2026-06-28

Branch: `fix/research-summary-blockers-2026-06-28`

Scope: research false-positive blockers from `ARCHITECTURE_AUDIT_REPORT.md`

Broker/API access during this pass: none

Trading/order changes: none

## Result

The requested blocker corrections are implemented. Opposite-side conclusions now use only opposite contract roles and only executable entry/exit quote pairs that pass freshness, market-integrity, intrinsic-value, and quote-validity checks.

The application remains a data collection and research engine. No order placement, auto-trading, buy/sell alert, dashboard, liquidity module, or event-driven subscription redesign was added.

## Files Changed

### Configuration and models

- `.env.example`
  - Added intrinsic violation tolerances, stale quote setting, and locked-market control.
- `src/config.py`
  - Loads the new validation settings.
- `src/models.py`
  - Added stock provenance, source timing, market-data type, raw spread/extrinsic, intrinsic violation, news-confidence, and provider-error fields.
  - Added `SignalStatus.FAILED`.

### Capture and providers

- `src/engine/capture_manager.py`
  - Isolates connection, signal, stock, chain, option, news, and close failures.
  - Writes structured provider errors.
  - Calculates and stores integrity/provenance fields.
  - Updates contract runtime min/max/compression state only from valid quotes.
- `src/providers/base.py`
  - Adds structured provider error metadata and diagnostic draining.
- `src/providers/ibkr_provider.py`
  - Records market-data type and provider ticker timestamp when available.
  - Leaves quote age null when source timing is unknown.
  - Marks close/signal-price stock fallbacks explicitly.
  - Captures IBKR error events.
  - Selects option volume/open interest by CALL/PUT side.
- `src/providers/mock_provider.py`
  - Populates explicit mock provenance and timing fields.
- `src/providers/replay_provider.py`
  - Reads the new provenance/timing fields when present.

### Validation, summaries, scoring, and news

- `src/engine/metrics.py`
  - Preserves raw spread.
  - Adds crossed/locked detection.
  - Adds raw extrinsic value and intrinsic violation calculation.
- `src/engine/quote_validation.py`
  - Rejects crossed markets, locked markets unless allowed, and intrinsic violations.
- `src/engine/summarizer.py`
  - Separates raw unfiltered return from valid executable return.
  - Uses fresh, valid, live/mock/replay, non-crossed, non-locked, intrinsic-consistent rows.
  - Adds executable threshold flags and first-hit times.
  - Selects best signal-summary contracts from opposite roles only.
- `src/engine/scoring.py`
  - Restricts opposite opportunity inputs to opposite roles.
  - Keeps `SIGNAL_CONTRACT` only for signal-side weakening/confirmation.
  - Excludes mock/unavailable news from the score.
- `src/news_providers/base.py`
  - Adds effective score, source confidence, and affects-score fields.
  - Adds explicit `NEWS_UNAVAILABLE` summaries.

### Storage

- `src/storage/csv_writer.py`
  - Adds all new tick, summary, news, threshold, and provider-error columns.
- `src/storage/sqlite_store.py`
  - Adds `provider_errors` table.
  - Adds missing columns to existing SQLite tables when schemas expand.

### Tests and documentation

- `tests/test_blocker_fixes.py`
  - New blocker regression tests.
- `tests/test_provider_resilience.py`
  - New failure-isolation and stock-fallback tests.
- `tests/test_summarizer.py`
  - Updated fixtures to provide required executable-quote evidence.
- `README.md`
  - Documents valid-only returns, thresholds, provider errors, and non-scoring mock news.
- `PROJECT_FLOW.md`
  - Documents the corrected pipeline and tests.
- `KNOWN_GAPS_AND_DECISIONS.md`
  - Records the completed blocker pass.
- `FIX_BLOCKERS_REPORT.md`
  - This report.

## Exact Logic Changes

### 1. Opposite-side isolation

Only these roles contribute to opposite-side opportunity scoring and best-contract selection:

```text
EXACT_OPPOSITE
ITM_OPPOSITE
ATM_OPPOSITE
OTM_OPPOSITE
LOTTO_OBSERVATION_ONLY
```

`SIGNAL_CONTRACT` remains available to `score_signal_contract()` for signal-side weakening or confirmation. It cannot set `opposite_side_opportunity_found=true`.

### 2. Valid conservative return

`best_conservative_ask_to_bid_return` now requires:

Entry row:

- `quote_is_valid=true`
- `ask > 0.01`
- known `quote_age_seconds` within `STALE_QUOTE_SECONDS`
- supported market-data type (`live`, `mock`, or replayed captured data)
- not crossed
- not locked unless `ALLOW_LOCKED_MARKET=true`
- no intrinsic violation
- high-confidence live intrinsic validation (or explicit mock test data)

Exit row:

- same integrity requirements
- timestamp equal to or later than entry
- `bid > 0`

The old all-row calculation is retained only as:

```text
raw_unfiltered_ask_to_bid_return
```

It is diagnostic and is not used for opposite opportunity decisions.

### 3. Intrinsic violation

New option tick fields:

```text
raw_extrinsic_value
intrinsic_violation_flag
intrinsic_violation_amount
intrinsic_violation_pct
intrinsic_validation_confidence
```

Formulas:

```text
PUT intrinsic  = max(strike - stock_last, 0)
CALL intrinsic = max(stock_last - strike, 0)
raw_extrinsic  = mid - intrinsic
```

The violation threshold is:

```text
max(INTRINSIC_VIOLATION_TOLERANCE_ABS,
    intrinsic * INTRINSIC_VIOLATION_TOLERANCE_PCT / 100)
```

Defaults:

```text
INTRINSIC_VIOLATION_TOLERANCE_ABS=0.05
INTRINSIC_VIOLATION_TOLERANCE_PCT=2.0
```

Existing nonnegative `extrinsic_value` is retained, while raw negative extrinsic evidence is no longer hidden.

### 4. Crossed and locked markets

New fields:

```text
raw_spread_abs = ask - bid
spread_abs = abs(ask - bid)
crossed_market_flag = bid > ask
locked_market_flag = bid == ask
```

Crossed markets are always invalid. Locked markets are invalid unless explicitly enabled with:

```text
ALLOW_LOCKED_MARKET=true
```

The default is false.

### 5. Stock fallback provenance

New stock fields:

```text
stock_price_source
stock_quote_status
fallback_used
stock_quote_is_live
market_data_type
quote_source_timestamp
quote_age_seconds
```

IBKR behavior:

- Provider last: `PROVIDER_LAST`.
- Missing last but close available: `PROVIDER_CLOSE_FALLBACK` and `fallback_used=true`.
- Missing last/close but supplied price available: `SIGNAL_PRICE_FALLBACK` and `fallback_used=true`.
- Fallback prices are never labeled live.
- Intrinsic validation is labeled `LOW_FALLBACK` when fallback stock price is used.

### 6. IBKR diagnostics

IBKR ticker `marketDataType` values are mapped to:

```text
live
frozen
delayed
delayed_frozen
unknown
```

Ticker source/update time is stored when available. If unavailable, source timestamp and quote age remain null instead of being written as zero.

`provider_errors.csv` and SQLite `provider_errors` include:

```text
timestamp_local
signal_id
underlying_symbol
option_symbol
intended_contract
contract_role
failure_stage
provider
provider_error_code
provider_error_message
market_data_type
quote_source_timestamp
quote_age_seconds
```

IBKR error events, including farm/entitlement/pacing messages delivered by the API, are drained into this structure.

### 7. Mock and unavailable news

Mock news now produces:

```text
news_score_effective = null
news_source_confidence = MOCK
news_affects_score = false
```

External provider failure produces:

```text
news_provider = NEWS_UNAVAILABLE
news_source_confidence = UNAVAILABLE
news_affects_score = false
```

There is no scored mock fallback. Configured secrets and `apikey=`/`token=` query values are redacted from stored error messages.

### 8. Failure isolation

- A failed signal is stored with `status=FAILED` and does not stop other signals.
- A failed option contract is written to `provider_errors` and deactivated without stopping other contracts.
- Stock, option-chain, option-quote, news, connection, and close failures have explicit stages.
- A complete provider connection failure is recorded for every input signal and returns an error after writing evidence; no false data is generated.

### 9. Executable thresholds

New contract summary fields:

```text
hit_40pct_executable
hit_50pct_executable
hit_100pct_executable
hit_180pct_executable
time_hit_40pct
time_hit_50pct
time_hit_100pct
time_hit_180pct
```

Each flag/time is derived only from a valid entry ask followed by a valid executable bid. Mid-to-mid and raw invalid-row moves cannot set these fields.

## Tests Added or Updated

The blocker tests verify:

1. Original signal contract movement cannot create an opposite opportunity.
2. Invalid low asks/high bids cannot create executable profit.
3. Raw unfiltered return remains separately visible.
4. Valid rows set 40%, 50%, 100%, and 180% flags and first-hit times.
5. Stock 44.64 and 60P at 14.10 flags the 15.36 intrinsic violation.
6. Raw negative spread is preserved for crossed markets.
7. Crossed markets are invalid.
8. Locked markets are invalid unless explicitly allowed.
9. Mock news cannot change opportunity score.
10. Actual mock news summaries are marked non-scoring.
11. News API keys/query tokens are redacted.
12. Low-confidence fallback intrinsic data cannot set executable-return flags.
13. One bad signal in a multi-signal CSV does not stop a good signal.
14. One bad contract does not stop remaining contracts.
15. Missing IBKR stock last is explicitly marked as fallback with unknown age when no source time exists.

## Test Output

Command:

```powershell
python -m pytest -p no:cacheprovider
```

Result:

```text
collected 29 items
29 passed
```

An additional offline mock smoke collection completed successfully and produced:

- Raw signal, stock, and option CSVs.
- All three option bar files.
- Contract and signal summaries.
- News files with mock news marked non-scoring.
- `provider_errors.csv`.
- `market_capture.sqlite`.

No broker connection was made.

## Remaining Known Gaps

These items were intentionally not implemented in this blocker pass:

1. IBKR collection is still serial/polling-style and may miss fast moves across many contracts.
2. No liquidity score, liquidity bucket, volume-since-signal, safe-size, or position-size model exists.
3. Bid/ask size is captured but not yet used to estimate scalable execution quantity.
4. No dynamic signal ingestion while a collection process is already running.
5. No historical bid/ask backfill for late-entered signals.
6. Preflight still uses a fixed test symbol/expiry and has limited entitlement diagnostics.
7. Market-data pacing and line limits are recorded when IBKR reports them, but there is no scheduler/backoff manager.
8. IBKR ticker time is the provider update timestamp available to `ib_insync`; it is not guaranteed to be a direct exchange timestamp.
9. Raw CSV files from older runs are not automatically rewritten to the new raw schema. Old runs fail closed for executable summaries when required evidence is absent.
10. SQLite remains all-`TEXT` without keys/indexes.
11. Replay remains summary regeneration rather than timed replay.
12. There is no auto-trading, automated trade alerting, or order code by design.

## Small Live Capture Safety

Verdict: **SAFE_FOR_SMALL_CONTROLLED_LIVE_CAPTURE_WITH_GUARDRAILS**.

Recommended first validation run:

- One signal.
- A unique run folder.
- A short observation period.
- TWS/Gateway manually logged in with read-only API enabled.
- Preflight confirms stock and option bid/ask.
- Confirm `market_data_type=live` in captured rows.
- Confirm `quote_age_seconds` is populated.
- Inspect `provider_errors.csv` immediately after the run.
- Verify expected contract count and valid quote count before trusting summaries.

This verdict does not mean the application is ready for five-signal high-cadence collection or a full one-week production research campaign. The serial sampling and missing liquidity/size module remain important limitations.
