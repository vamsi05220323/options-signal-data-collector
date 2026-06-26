# IBKR Market Data And Run Plan

This document records the market-data subscription choices and runtime plan for the options signal data collector.

Last reviewed: 2026-06-26

Primary sources:

- IBKR API Market Data Subscriptions: https://www.interactivebrokers.com/campus/ibkr-api-page/market-data-subscriptions/
- IBKR OPRA Glossary: https://www.interactivebrokers.com/campus/glossary-terms/options-price-reporting-authority-opra/
- Current Client Portal subscription text copied from the account on 2026-06-26.

## Project Data Need

The collector needs real-time Level 1/top-of-book data for:

1. The underlying stock bid/ask/last.
2. The original signal-side option contract.
3. Opposite-side option contracts around ATM/OTM strikes.
4. Option bid/ask/mid/last, volume, open interest, implied volatility, and Greeks when available.

For this project, Level II/depth-of-book is not needed yet.

## Required Account/API Gates

Before live API quote capture works:

1. IBKR account must be open.
2. Account must be IBKR Pro for API market data.
3. Account must satisfy market-data minimum equity requirements.
4. Market Data API Acknowledgement must be enabled.
5. Market Data Subscriber Status must be set.
6. Correct market data subscriptions must be active for the same user that logs into TWS/API.
7. TWS or IB Gateway must be open, logged in, and API socket must be enabled.
8. `.env.local` must match the TWS API port.

Current TWS API setting observed:

```text
IBKR_HOST=127.0.0.1
IBKR_PORT=7496
IBKR_CLIENT_ID=12
```

## Subscriber Status

If this account is used only for personal trading/research and not for business, advisory, employer, client, registered securities/investment professional, or similar professional use, select:

```text
Non-Professional
```

If any professional-use condition applies, choose:

```text
Professional
```

Do not guess on this. The status is a legal/exchange classification, not a software setting.

## Recommended Subscription Path

## Portal Checkbox Decisions

This section maps the visible Client Portal choices to what we should select for this project.

### Image 1: Quote Bundles

Recommended lean path:

```text
Do not select anything in Quote Bundles.
```

Use this lean path when selecting individual Level I items in the `Level I (NBBO)` section:

```text
NASDAQ (Network C/UTP) (NP,L1)
NYSE (Network A/CTA) (NP,L1)
NYSE American, BATS, ARCA, IEX, and Regional Exchanges (Network B) (NP,L1)
OPRA (US Options Exchanges) (NP,L1)
```

Alternative bundle path:

```text
Select US Securities Snapshot and Futures Value Bundle (NP,L1)
Select US Equity and Options Add-On Streaming Bundle (NP)
```

Use the bundle path only if the portal makes the a la carte Level I path hard to complete.

Do not select:

```text
US Futures Value Bundle PLUS (NP,L2)
Cboe One Add-On Bundle (NP,L1)
```

Those are not needed for the current stock/options collector.

### Image 2: Indexes

Recommended:

```text
Select nothing.
```

Reason:

The current collector tracks equity options and underlying stocks from signal-provider alerts. It does not need index quotes yet.

Add index subscriptions later only if we intentionally collect SPX, VIX, SPY index context, or index-option data that requires a separate index feed.

### Images 3, 4, 5: Level I (NBBO)

Select:

```text
NASDAQ (Network C/UTP) (NP,L1) - USD 1.50/month
NYSE (Network A/CTA) (NP,L1) - USD 1.50/month
NYSE American, BATS, ARCA, IEX, and Regional Exchanges (Network B) (NP,L1) - USD 1.50/month
OPRA (US Options Exchanges) (NP,L1) - USD 1.50/month
```

Do not select:

```text
Canadian Exchange Group
Canadian Securities Exchange
Cboe One
CBOT Real-Time
CFE Enhanced
CME Real-Time
COMEX Real-Time
Mexican Futures Derivatives
Mexican Options Derivatives
Mexican Stock Exchange
Montreal Derivatives
NEO Exchange
NYMEX Real-Time
OTC Markets
```

Reason:

Those are not required for US equity options around stock signal alerts.

### Level II (Deep Book)

Recommended:

```text
Select nothing.
```

Reason:

IBKR states Level II is needed for market depth. Our app currently needs Level I/top-of-book bid and ask, not depth-of-book. Level II would add cost and complexity without answering the current research question.

Do not select any of these yet:

```text
Cboe BZX Depth
CBOT Real-Time L2
CFE Enhanced with Depth of Book
CME Real-Time L2
COMEX Real-Time L2
Global OTC and OTC Markets L2
ICE Futures U.S. L2
ISE Options L2
NASDAQ Options Market L2
NASDAQ TotalView-OpenView
NYSE AMEX Options L2
NYSE Arca Options L2
NYSE ArcaBook
NYSE OpenBook
OTC Global Equities L2
OTC Markets L2
Toronto Market by Price
TSX Venture Market by Price
```

Possible future use:

Level II might become useful if we later build a liquidity/slippage model using order-book depth. That is not part of this collector phase.

### Fixed Income

Recommended:

```text
Select nothing.
```

Do not select:

```text
Bond Ratings - USD 3.00/month
```

Reason:

The project is not collecting corporate/municipal bond data.

### Other Subscriptions

Recommended:

```text
Do not select paid order imbalance subscriptions.
```

Do not select:

```text
NYSE ARCA Order Imbalances - USD 1.00/month
NYSE MKT Order Imbalances - USD 1.00/month
NYSE Order Imbalances - USD 1.00/month
```

Already complimentary / okay to leave as-is:

```text
US Real-Time Non Consolidated Streaming Quotes - Fee Waived
ZEROHASH Cryptocurrency - Fee Waived
```

Reason:

Order imbalance feeds are auction/open-close data and are not required for option bid/ask tradability research.

## Recommended Subscription Path

### Recommended First Choice: A La Carte Level I

Use this if Client Portal allows selecting individual Level I subscriptions.

Select:

| Subscription | Purpose | Cost |
|---|---:|---:|
| OPRA (US Options Exchanges) (NP,L1) | US option bid/ask for all listed US options | USD 1.50/month |
| NASDAQ (Network C/UTP) (NP,L1) | NASDAQ-listed stock bid/ask, e.g. BEAM, TSLA, MSFT | USD 1.50/month |
| NYSE (Network A/CTA) (NP,L1) | NYSE-listed stock bid/ask | USD 1.50/month |
| NYSE American, BATS, ARCA, IEX, and Regional Exchanges (Network B) (NP,L1) | ARCA/AMEX/regional listings, many ETFs and exchange listings | USD 1.50/month |

Estimated total:

```text
USD 6.00/month before taxes/fees
```

Notes:

- OPRA fee may be waived when monthly commissions reach IBKR's listed waiver threshold.
- This is the leanest setup for a broad US-stock/US-options signal collector.
- If all signals are guaranteed NASDAQ-only, the bare minimum test setup could be OPRA + NASDAQ Network C = USD 3.00/month, but this is too narrow for real daily use.

### Simpler Bundle Choice

If the portal makes the bundle easier or requires the base bundle, select:

| Subscription | Purpose | Cost |
|---|---:|---:|
| US Securities Snapshot and Futures Value Bundle (NP,L1) | Required base bundle for add-on; snapshot data and listed derivatives top-of-book | USD 10.00/month |
| US Equity and Options Add-On Streaming Bundle (NP) | Streaming top-of-book for Network A, Network B, Network C, and OPRA | USD 4.50/month |

Estimated total:

```text
USD 14.50/month before taxes/fees
```

Notes:

- The USD 10.00 base bundle may be waived if monthly commissions reach IBKR's listed waiver threshold.
- This bundle includes the data we need, but may cost more than a la carte.

## What Not To Select Yet

Do not select these for the current collector unless a later feature explicitly needs them:

- Level II / depth-of-book packages.
- NASDAQ TotalView / OpenView.
- ISE Options Level II.
- NYSE Arca Options Level II.
- NYSE AMEX Options Level II.
- Futures data bundles.
- Cboe One Add-On unless we specifically need Cboe-only equities data.
- Order imbalance feeds.
- Quote Booster packs unless we exceed the market-data line cap.
- Paid news feeds such as Benzinga API unless we intentionally add paid news capture.

## Why Snapshot-Only Is Not Enough

The collector is designed to record continuous bid/ask snapshots every second during the signal window.

Snapshot market data is charged per request and is not available for options in the same way as streaming Level I option quotes. It is not the right base mode for this project.

Use streaming Level I subscriptions for this collector.

## Cost Rules To Remember

IBKR states:

1. Market data subscriptions are paid monthly.
2. Market data subscriptions are not prorated.
3. Once subscribed, there are not additional usage fees for that subscribed streaming data.

Practical meaning:

- Starting on the 1st of the month is cleaner.
- Subscribing near month-end can still charge the full month.
- Running the collector 30 minutes vs 6 hours does not change the subscription fee.
- Runtime affects laptop resources and market-data line usage, not monthly data-subscription price.

## Market Data Lines

IBKR provides a minimum of 100 concurrent market-data lines.

Our collector estimate:

```text
5 underlyings + 25 to 40 option contracts = about 30 to 45 lines
```

TWS watchlists and scanners use lines too. If TWS already shows many symbols, fewer lines are available for the API.

Check line usage in TWS:

```text
Ctrl + Alt + =
```

## Recommended Daily Run Schedule

US regular market hours:

```text
9:30 AM to 4:00 PM Eastern
8:30 AM to 3:00 PM Central
```

Recommended process in Central Time:

| Time | Action |
|---|---|
| 8:15 AM CT | Open TWS and log in. |
| 8:20 AM CT | Run IBKR preflight. |
| 8:30 AM CT | Market open. Keep app ready. |
| When signal arrives | Start `collect-signal` or add to CSV and run/continue `collect-file`. |
| First 30 minutes after each signal | Capture aggressively, ideally every 1 second. |
| After first 30 minutes | Capture every 5 seconds. |
| 3:00 PM CT | Stop collector at regular market close, summarize run. |

## Recommended Research Collection Window

For the first research phase:

```text
Collect 20 to 50 real signals before building alerts.
```

For each signal:

```text
Minimum useful capture: 30 minutes
Better capture: 60 to 120 minutes
Best full-day capture: until market close
```

Default for now:

```text
duration-seconds=1800
```

That is 30 minutes per run and is enough to test whether post-signal option compression/rebound is real.

## Commands

Preflight:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\ibkr_preflight.ps1
```

Single signal, 30 minutes:

```powershell
.\scripts\run.ps1 collect-signal --symbol BEAM --direction CALL --strike 40 --expiry 2026-07-17 --signal-premium 0.40 --stock-price 36.50 --provider ibkr --duration-seconds 1800
```

CSV signals, 30 minutes:

```powershell
.\scripts\run.ps1 collect-file --signals-file data/sample_signals_today.csv --provider ibkr --duration-seconds 1800
```

Summarize:

```powershell
.\scripts\summarize_today.ps1
```

## Validation After Subscription

After selecting subscriptions, log out and back in to TWS and Client Portal. Then run:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\ibkr_preflight.ps1
```

Good result:

```text
stock_quote bid=<number> ask=<number> last=<number>
option_quote ... bid=<number> ask=<number> last=<number>
ibkr preflight ok
```

Still not ready:

```text
market_data_incomplete=stock bid/ask, option bid/ask
```

If still incomplete after subscribing:

1. Confirm the subscriptions are active for the same username used in TWS.
2. Confirm TWS has been restarted after subscription.
3. Confirm API Market Data Acknowledgement is still enabled.
4. Confirm market is open.
5. Try a highly liquid symbol like `AAPL` or `SPY` for diagnostics.

## Current Recommendation

For this project right now:

1. Choose `Non-Professional` only if that is truthful for the account.
2. Prefer a la carte Level I:
   - OPRA (US Options Exchanges) (NP,L1)
   - NASDAQ (Network C/UTP) (NP,L1)
   - NYSE (Network A/CTA) (NP,L1)
   - NYSE American, BATS, ARCA, IEX, and Regional Exchanges (Network B) (NP,L1)
3. Estimated monthly cost: USD 6.00 before taxes/fees.
4. If a la carte selection does not work cleanly, use:
   - US Securities Snapshot and Futures Value Bundle (NP,L1)
   - US Equity and Options Add-On Streaming Bundle (NP)
5. Estimated bundle monthly cost: USD 14.50 before taxes/fees.
6. Do not buy Level II/depth or futures packages for this collector yet.
