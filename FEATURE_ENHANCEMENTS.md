# Feature Enhancements

This file tracks future improvements discussed during live testing and setup.

## 2026-06-26: Historical Backfill For Late-Entered Signals

Context:

If a signal happens at 9:00 AM Central but the user starts entering/running the command at 9:05 AM, the current live collector records the true signal timestamp but only captures market data from the time the collector actually starts.

Current behavior:

```text
--signal-time 09:00
```

records the alert time as 9:00 AM Central, but live bid/ask collection starts when the command starts, unless `--start-time` is set to a future time.

Missing enhancement:

Add historical backfill so the app can request earlier stock and option bars/quotes from IBKR for the gap between signal time and collection start time.

Example:

```text
signal_time = 09:00
command_started = 09:05
desired_backfill = 09:00 to 09:05
live_capture = 09:05 onward
```

Important limitation:

Historical option data may not have the same fidelity as live tick-by-tick bid/ask snapshots. This needs a careful design and validation step before it is used in ranking.

## 2026-06-26: Separate Live Runs From Test Runs

Context:

The default daily run folder can contain multiple signals collected on the same date. That is useful for a full trading-day batch, but it confused validation when test signals and live signals were written into the same folder.

Current workaround:

Use an explicit isolated run folder for real live tests:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run.ps1 collect-signal ... --run-folder data\runs\2026-06-26_MAN_1413_CALL_10min
```

Possible enhancement:

Add a `--new-run` or default unique run-folder mode for `collect-signal`, while keeping daily folders available for intentional multi-signal batch collection.
