# Known Gaps And Development Decisions

This file records issues discovered during setup, decisions made, and gaps that require approval before engine changes.

## Development Rule

Going forward:

1. Every project change should be committed and pushed to a remote branch.
2. Documentation, scripts, setup fixes, and preflight clarity fixes can be made proactively.
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

## Current Known Gap: Exchange And Contract Resolution

Question:

If a signal says only:

```text
PEP 145 CALL 2026-07-17
```

how does the app know which PEP instrument/listing to use?

Current behavior:

For IBKR stock and options, the provider currently uses:

```text
Stock(symbol, "SMART", "USD")
Option(symbol, expiry, strike, right, "SMART", currency="USD")
```

This is usually correct for mainstream US-listed stocks and equity options because:

- `SMART` routes to the primary/eligible US listing.
- US equity options are generally addressed by underlying symbol, expiry, strike, right, and SMART routing.

Risk:

Some tickers are ambiguous across countries, exchanges, currencies, share classes, or products. A symbol-only signal can be insufficient.

Examples:

- Same symbol may exist in more than one country.
- Same company may have ADR/local listings.
- A ticker may refer to a stock, ETF, warrant, or foreign listing.
- Some underlyings may need `primaryExchange` for deterministic qualification.

Recommended future fix:

Add a contract-resolution/preflight layer before live collection:

1. Resolve symbol through IBKR contract details.
2. Prefer US `STK`, currency `USD`, exchange `SMART`.
3. Store IBKR `conId`, primary exchange, trading class, and local symbol.
4. Present ambiguous matches and require user confirmation.
5. Allow optional signal CSV columns:

```text
underlying_exchange
primary_exchange
currency
ibkr_con_id
option_trading_class
```

6. Store selected contract identity in `signals.csv` and SQLite.

Approval needed:

This affects the main capture path and should be implemented only after explicit approval.

## Current Known Gap: Expiration And Trading Class Ambiguity

IBKR can have multiple option trading classes or expiration classes for the same apparent symbol/date. The app currently assumes a standard US equity option by symbol, expiry, strike, and right.

Recommended future fix:

When option chain data is retrieved, store and validate:

```text
tradingClass
multiplier
exchange
localSymbol
conId
```

Approval needed before engine change.

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
