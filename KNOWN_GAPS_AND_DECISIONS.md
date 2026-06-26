# Known Gaps And Development Decisions

This file records issues discovered during setup, decisions made, and gaps that require approval before engine changes.

## Development Rule

Going forward:

1. Every project change should be committed and pushed to a remote branch.
2. Documentation, scripts, setup fixes, preflight clarity fixes, and output visibility improvements can be made proactively.
3. Main processing-engine logic must not be changed without explicit approval.
4. If a gap is found, document it immediately even if the code fix needs approval.

## Already Fixed Gap: Misleading IBKR Preflight

Problem:

The first IBKR preflight could print success even when bid/ask market data was missing.

Fix:

The preflight now separates:

```text
IBKR socket connection works
```

from:

```text
market data is complete
```

If stock or option bid/ask is missing, it prints:

```text
ibkr connection ok
market_data_incomplete=...
```

Commit:

```text
606739d Clarify IBKR preflight and port setup
```

## Approved And Implemented: IBKR Contract Resolution

Question:

If a signal says only:

```text
PEP 145 CALL 2026-07-17
```

how does the app know which `PEP` instrument/listing to use?

Previous behavior:

For IBKR stock and options, the provider used:

```text
Stock(symbol, "SMART", "USD")
Option(symbol, expiry, strike, right, "SMART", currency="USD")
```

That is usually correct for mainstream US-listed stocks and equity options, but it is not deterministic enough for ambiguous tickers.

Approval:

The user approved adding IBKR contract resolution on 2026-06-25 with the condition that ranking behavior must not change.

Implemented behavior:

1. Before capture, the IBKR provider resolves the stock contract through TWS.
2. If `ibkr_con_id` is supplied, the provider qualifies that conId directly.
3. Otherwise it requests IBKR contract details and prefers exact symbol, `STK`, `USD`, SMART routing, and common U.S. primary exchanges such as NASDAQ, NYSE, ARCA, AMEX, BATS, and IEX.
4. The resolved stock conId, primary exchange, currency, local symbol, trading class, and status are stored in `signals.csv`.
5. Qualified option conId, local symbol, trading class, and exchange are stored in `option_ticks.csv`.
6. Optional signal CSV columns are now accepted:

```text
underlying_exchange
primary_exchange
currency
ibkr_con_id
ibkr_local_symbol
ibkr_trading_class
```

Ranking impact:

No ranking formula change. The formula remains:

```text
70% stock/option microstructure
20% news context
10% signal-side contract behavior
```

## Implemented: News Inputs Visible In Main Summary

News was already used as a ranking input through `news_score` and written to separate files:

```text
news_articles.csv
news_summary_by_signal.csv
```

The main signal summary now also includes the news fields used in ranking:

```text
news_provider
news_count_24h
news_count_7d
latest_news_age_minutes
catalyst_detected
catalyst_type
news_bias
news_score
top_headlines_24h
news_skip_warning
```

This changes output visibility only. It does not change the ranking formula.

## Implemented: Signal Time And Capture Window Controls

Single-signal CLI mode originally used the current time as the signal timestamp. That was not enough for real alerts that are entered after they happened.

Implemented controls:

```text
--signal-time
--start-time
--end-time
```

Supported values:

```text
now
current
10:00
15:00
market-open
market-close
2026-06-26T10:00:00-05:00
```

Behavior:

- `--signal-time` records when the alert happened.
- `--start-time` controls when live collection begins.
- `--end-time` controls when live collection stops.
- Bare times use the configured `.env.local` timezone. Current default is `America/Chicago`.
- These controls do not backfill historical morning bid/ask data. They only schedule live collection and preserve the true signal timestamp.

## Implemented: Stop Retrying Invalid Option Contracts

During a live MAN test, IBKR rejected some far opposite-side option contracts with error 200/no security definition.

Fix:

If provider qualification fails for a selected option contract during a run, that contract is skipped for the rest of the run instead of being retried every polling loop.

Ranking impact:

No ranking formula change. The skipped contract simply has no quote rows and therefore cannot become a ranked opportunity.

## Current Known Gap: Expiration And Trading Class Ambiguity

IBKR can have multiple option trading classes or expiration classes for the same apparent symbol/date. The app now stores qualified option identity after quote qualification, but the chain-selection step still chooses by standard symbol, expiry, strike, and right.

Recommended future fix:

When option chain data is retrieved, store and validate:

```text
tradingClass
multiplier
exchange
localSymbol
conId
```

Approval needed before deeper engine behavior changes.

## Current Known Gap: Market Data Entitlement Diagnostics

Current preflight reports missing bid/ask. It does not yet inspect all IBKR error codes into a structured diagnostic table.

Recommended future fix:

Capture IBKR market-data errors into structured output:

```text
error_code
request_id
symbol
contract_type
probable_cause
recommended_subscription
```

This is a preflight/diagnostic improvement and can be made proactively.

## Current Known Gap: Market Hours Awareness

The app can run with `--duration-seconds`, but does not yet automatically stop at market close or adjust polling schedules by market session.

Recommended future fix:

Add market-hours calendar logic:

```text
regular market open
regular market close
early close
holiday
after-hours behavior
```

Approval needed before engine behavior change.

## Current Known Gap: News Is Mock By Default

News architecture exists, but real news APIs require keys.

Current providers:

```text
mock
alpha_vantage
finnhub
yahoo disabled fallback
```

Recommended future fix:

Add preflight checks for Alpha Vantage/Finnhub keys and clearly tag news confidence in summaries.

## Market Data Decision

For current collector phase, use only Level I/top-of-book market data:

```text
NASDAQ Network C
NYSE Network A
Network B
OPRA
```

Do not buy Level II/deep-book data yet.

Reason:

The primary research metric is ask entry vs future bid exit. That requires top-of-book bid/ask, not full book depth.
