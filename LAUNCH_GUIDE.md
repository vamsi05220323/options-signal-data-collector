# Launch Guide

This guide explains how to make the project work from a normal Windows PowerShell window.

## What Failed Before

Your PowerShell did not have a real `python` command available. It pointed here:

```text
C:\Users\cmedu\AppData\Local\Microsoft\WindowsApps\python.exe
```

That is the Microsoft Store shortcut, not a working Python install. So commands like this failed:

```powershell
python -m src.main preflight --mock
```

To avoid that problem, this project now includes PowerShell scripts that find a usable Python, create a project virtual environment, and run the app through that environment.

## What API This App Uses

There are several different meanings of "API" here.

### 1. The App Command API

This is the command-line interface in:

```text
src/main.py
```

You run it with commands like:

```powershell
.\scripts\run.ps1 preflight --mock
.\scripts\run.ps1 collect-file --signals-file data/sample_signals_today.csv --provider mock --duration-seconds 30
```

### 2. Mock Provider

Mock mode uses no outside market data API. It generates fake stock and option quotes locally so we can test the project without IBKR.

Use mock mode first. If mock mode works, the app is installed correctly.

### 3. IBKR API

Live market data uses the Interactive Brokers TWS/Gateway local socket API through Python package:

```text
ib_insync
```

The app connects to:

```text
127.0.0.1:7497
```

by default.

Important: the app does not log in to IBKR. You log in manually through TWS or IB Gateway. Then this app connects to the already-open local API socket.

### 4. News APIs

News is optional. The app has support modules for:

```text
Alpha Vantage News & Sentiment
Finnhub Company News
```

If no news API key is configured, the app uses mock news for testing.

### 5. GitHub API

GitHub CLI was used only to create and push the GitHub repo. It is not part of the trading data collector runtime.

## One-Time Setup

Open PowerShell and run:

```powershell
cd C:\workspace\options_alert_engine
powershell -ExecutionPolicy Bypass -File .\scripts\setup.ps1
```

What this does:

1. Finds a usable Python.
2. Creates `.venv`.
3. Installs dependencies from `requirements.txt`.
4. Creates `.env.local` if missing.

After setup, the project should use:

```text
C:\workspace\options_alert_engine\.venv\Scripts\python.exe
```

You do not need to type that long path directly. The scripts use it for you.

## Step 1: Confirm The App Works Without IBKR

Run:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\mock_preflight.ps1
```

Expected result:

```text
Preflight
provider=mock
alerts=false
trading=false
stock_quote bid=... ask=... last=...
option_chain strikes=...
option_quote ... bid=... ask=... last=...
mock preflight ok
```

If this works, Python and the project dependencies are installed correctly.

## Step 2: Run A 30-Second Mock Collection

Run:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\mock_collect.ps1
```

This reads:

```text
data/sample_signals_today.csv
```

It writes output to:

```text
data/runs/YYYY-MM-DD/
```

Expected important files:

```text
signals.csv
stock_ticks.csv
option_ticks.csv
summary_by_contract.csv
summary_by_signal.csv
market_capture.sqlite
```

If this works, the full collector flow works in mock mode.

## Time Inputs

The app timezone is controlled by `.env.local`:

```text
TIMEZONE=America/Chicago
```

That means bare times like `10:00` or `15:00` are treated as Texas/Central time. ISO timestamps with offsets also work:

```text
2026-06-26T10:00:00-05:00
```

Useful values:

```text
--signal-time now
--signal-time 10:00
--start-time now
--end-time 15:00
--end-time market-close
```

`--signal-time` records when the alert happened. `--start-time` and `--end-time` control when the collector actually pulls live data. If the signal was at 10:00 AM but the app starts at 1:54 PM, the collector starts with live data from 1:54 PM unless a historical backfill feature is added later.

## Step 3: Read The Summary

Open:

```text
data/runs/YYYY-MM-DD/summary_by_signal.csv
data/runs/YYYY-MM-DD/summary_by_contract.csv
```

Important columns:

```text
best_conservative_ask_to_bid_return
percentage_of_valid_quotes
median_spread_pct
was_best_move_tradable
opportunity_score
news_score
news_bias
catalyst_type
```

The most important one is:

```text
best_conservative_ask_to_bid_return
```

That tells us whether the move was tradable using ask entry and bid exit.

## Step 4: Configure IBKR TWS

Before live data, TWS or IB Gateway must be open and logged in by you.

In TWS, check:

1. Open TWS.
2. Log in manually.
3. Go to `File > Global Configuration`.
4. Go to `API > Settings`.
5. Enable `Enable ActiveX and Socket Clients`.
6. Confirm socket port:
   - Paper TWS usually uses `7497`.
   - Live TWS usually uses `7496`.
7. Optional but useful: add trusted IP `127.0.0.1`.
8. For data collection, read-only API mode is fine.

You also need market data:

1. OPRA real-time options data for U.S. options.
2. Real-time underlying stock data.
3. Enough market data lines for all tracked symbols/contracts.

The app does not need and does not store your IBKR password.

### What Your TWS Screenshots Showed

Your API settings looked mostly correct:

```text
Enable ActiveX and Socket Clients: checked
Read-Only API: checked
Socket port: 7496
Allow connections from localhost only: checked
```

That means the app must use:

```text
IBKR_PORT=7496
```

in `.env.local`.

The earlier connection-refused error happened because the app was trying `7497`, but TWS was listening on `7496`.

`Allow connections from localhost only` is good for this app because the collector runs on the same laptop as TWS.

`Trusted IPs` can stay empty when `Allow connections from localhost only` is checked. Adding `127.0.0.1` is optional.

### Do We Need "Use Local PC To Calculate Bid/Ask IV"?

No, not for connecting to IBKR and not for collecting bid/ask quotes.

That setting is for TWS volatility/model calculations. The collector needs the actual option bid and ask first. Later, if IBKR supplies implied volatility/Greeks, the app stores them. But this checkbox does not fix API connection or OPRA market-data permission problems.

## Step 5: Run IBKR Preflight

Run:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\ibkr_preflight.ps1
```

Expected success means:

1. TWS/Gateway socket is reachable.
2. A stock quote comes back.
3. An option chain comes back.
4. An option quote comes back.

If bid/ask is missing, the most likely cause is market data entitlement, especially OPRA.

For the exact subscription choices, estimated monthly costs, and recommended daily run schedule, see:

```text
MARKET_DATA_AND_RUN_PLAN.md
```

If the output says:

```text
ibkr connection ok
market_data_incomplete=stock bid/ask, option bid/ask
```

then the API socket is working. The remaining issue is market data availability, usually one of:

1. Market is closed.
2. Delayed-only data is available.
3. OPRA options data is not subscribed for API use.
4. US stock top-of-book/NBBO data is not subscribed for API use.

## Step 6: Collect Real IBKR Data

Once IBKR preflight works, run a real collection:

```powershell
.\scripts\run.ps1 collect-file --signals-file data/sample_signals_today.csv --provider ibkr --duration-seconds 1800
```

That runs for 30 minutes.

For one manual signal:

```powershell
.\scripts\run.ps1 collect-signal --symbol BEAM --direction CALL --strike 40 --expiry 2026-07-17 --signal-premium 0.40 --stock-price 36.50 --provider ibkr --duration-seconds 1800
```

## How To Enter Real Signals

For multiple signals, edit:

```text
data/sample_signals_today.csv
```

Use columns:

```text
timestamp_local,symbol,direction,signal_strike,expiry,signal_premium,stock_price_at_signal
```

Optional columns for IBKR contract identity:

```text
underlying_exchange,primary_exchange,currency,ibkr_con_id,ibkr_local_symbol,ibkr_trading_class
```

For the normal workflow where you enter one NASDAQ/NYSE ticker at a time, you do not need to fill those optional columns. Leave them blank and the IBKR provider will resolve the stock contract through TWS, store the selected conId/primary exchange, and use SMART routing for the option contracts.

Example:

```csv
timestamp_local,symbol,direction,signal_strike,expiry,signal_premium,stock_price_at_signal
2026-06-25T10:05:00-05:00,BEAM,CALL,40,2026-07-17,0.40,36.50
```

Then run:

```powershell
.\scripts\run.ps1 collect-file --signals-file data/sample_signals_today.csv --provider ibkr --duration-seconds 1800
```

For one IBKR signal with explicit time controls:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run.ps1 collect-signal --symbol MAN --direction PUT --strike 35 --expiry 2026-07-17 --stock-price 36.27 --provider ibkr --primary-exchange NYSE --signal-time 10:00 --start-time now --end-time market-close
```

## What The Application Actually Does

For each CALL signal:

1. Tracks the original CALL contract.
2. Tracks the exact opposite PUT strike.
3. Tracks one ITM PUT.
4. Tracks the nearest ATM PUT.
5. Tracks several OTM PUTs.
6. Tracks optional lotto PUTs as observation only.
7. Saves stock bid/ask/last.
8. Saves option bid/ask/mid/last/spread/volume/OI/IV/Greeks if available.
9. Marks invalid quotes instead of hiding them.
10. Calculates conservative ask-to-bid returns.
11. Adds news context to the ranking inputs.
12. Scores every signal independently using 70% bid/ask microstructure, 20% news context, and 10% signal-side contract behavior.

It does not send buy/sell alerts yet.

It does not place trades.

It does not connect to Robinhood.

## Troubleshooting

### Error: running scripts is disabled

Use:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup.ps1
```

### Error: Python not found

Run setup:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup.ps1
```

If setup still says Python is missing, install Python 3.11+ from:

```text
https://www.python.org/downloads/windows/
```

During install, select:

```text
Add python.exe to PATH
```

### Error: Could not connect to IBKR

Check:

1. TWS or IB Gateway is open.
2. You are logged in.
3. API socket clients are enabled.
4. `.env.local` uses the correct port.
5. No firewall is blocking local socket connections.

### Error: option quote has no bid/ask

Most likely:

1. OPRA data is not enabled.
2. Market is closed or quote is delayed.
3. Contract is illiquid.
4. IBKR market-data line limits are hit.

## The Correct Learning Path

Use this order:

1. `setup.ps1`
2. `mock_preflight.ps1`
3. `mock_collect.ps1`
4. Open the generated CSV files.
5. Configure TWS API.
6. `ibkr_preflight.ps1`
7. Collect one real signal.
8. Collect 5 real signals.
9. Review summaries after 20 to 50 signals.
10. Only then discuss alerts.
