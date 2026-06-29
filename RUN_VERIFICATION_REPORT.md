# Run Verification Report

Verification date: 2026-06-29

Mode: mock provider only

Live broker/API connection: not used

Project root:

```text
C:\workspace\options_alert_engine
```

## Result

- Tests: `29 passed`
- Fresh mock collection: completed successfully
- Explicit summarize command: completed successfully
- Sample signals: 2
- Contract summaries: 20
- Signal summaries: 2
- Option ticks: 520
- Stock ticks: 52
- Structured provider error rows: 0

## Fresh Mock Run Folder

```text
C:\workspace\options_alert_engine\data\runs\mock_blocker_verify_20260629_001603
```

## Absolute Artifact Paths

```text
C:\workspace\options_alert_engine\pytest_output.txt
C:\workspace\options_alert_engine\data\runs\mock_blocker_verify_20260629_001603\summary_by_contract.csv
C:\workspace\options_alert_engine\data\runs\mock_blocker_verify_20260629_001603\summary_by_signal.csv
C:\workspace\options_alert_engine\data\runs\mock_blocker_verify_20260629_001603\option_ticks.csv
C:\workspace\options_alert_engine\data\runs\mock_blocker_verify_20260629_001603\stock_ticks.csv
C:\workspace\options_alert_engine\data\runs\mock_blocker_verify_20260629_001603\signals.csv
C:\workspace\options_alert_engine\data\runs\mock_blocker_verify_20260629_001603\provider_errors.csv
C:\workspace\options_alert_engine\data\runs\mock_blocker_verify_20260629_001603\market_capture.sqlite
```

## Command Outputs

### 1. Working directory and existing artifact search

Command:

```powershell
$root=(Get-Location).Path
"CURRENT_WORKING_DIRECTORY=$root"
"PROJECT_ROOT_EXISTS=$(Test-Path -LiteralPath 'C:\workspace\options_alert_engine')"
Get-ChildItem -LiteralPath 'C:\workspace\options_alert_engine' -Recurse -File |
  Where-Object { $_.Name -in @('pytest_output.txt','summary_by_contract.csv','summary_by_signal.csv','FIX_BLOCKERS_REPORT.md') }
```

Output:

```text
CURRENT_WORKING_DIRECTORY=C:\workspace\options_alert_engine
PROJECT_ROOT_EXISTS=True
--- ARTIFACT SEARCH ---
C:\workspace\options_alert_engine\data\runs\2026-06-25\summary_by_contract.csv
C:\workspace\options_alert_engine\data\runs\2026-06-25\summary_by_signal.csv
C:\workspace\options_alert_engine\data\runs\2026-06-26\summary_by_contract.csv
C:\workspace\options_alert_engine\data\runs\2026-06-26\summary_by_signal.csv
C:\workspace\options_alert_engine\data\runs\2026-06-26_MAN_1413_CALL_10min\summary_by_contract.csv
C:\workspace\options_alert_engine\data\runs\2026-06-26_MAN_1413_CALL_10min\summary_by_signal.csv
C:\workspace\options_alert_engine\data\runs\2026-06-26_MAN_1413_CALL_10min_retry\summary_by_contract.csv
C:\workspace\options_alert_engine\data\runs\2026-06-26_MAN_1413_CALL_10min_retry\summary_by_signal.csv
C:\workspace\options_alert_engine\FIX_BLOCKERS_REPORT.md
```

No existing `pytest_output.txt` was found before verification.

### 2. Pytest

Command:

```powershell
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider *> pytest_output.txt
```

Exact captured output:

```text
============================= test session starts =============================
platform win32 -- Python 3.12.13, pytest-9.1.1, pluggy-1.6.0
rootdir: C:\workspace\options_alert_engine
collected 29 items

tests\test_blocker_fixes.py ..........                                   [ 34%]
tests\test_contract_identity.py .                                        [ 37%]
tests\test_metrics.py .                                                  [ 41%]
tests\test_multi_signal.py .                                             [ 44%]
tests\test_provider_resilience.py ...                                    [ 55%]
tests\test_quote_validation.py ..                                        [ 62%]
tests\test_scoring.py .                                                  [ 65%]
tests\test_signal_parser.py .....                                        [ 82%]
tests\test_strike_selector.py ..                                         [ 89%]
tests\test_summarizer.py ...                                             [100%]

============================= 29 passed in 4.78s ==============================
```

Exit code: `0`

### 3. Fresh mock collection

Command:

```powershell
.\.venv\Scripts\python.exe -m src.main collect-file `
  --signals-file data\sample_signals_today.csv `
  --provider mock `
  --duration-seconds 30 `
  --run-folder C:\workspace\options_alert_engine\data\runs\mock_blocker_verify_20260629_001603
```

Exact durable output lines surrounding the Rich live-table redraws:

```text
FRESH_RUN_FOLDER=C:\workspace\options_alert_engine\data\runs\mock_blocker_verify_20260629_001603
BEAM_20260625_100500_CALL_40p0: tracking 10 contracts
VRNS_20260625_100700_CALL_40p0: tracking 10 contracts
run_folder=C:\workspace\options_alert_engine\data\runs\mock_blocker_verify_20260629_001603
```

The command also rendered six Rich `Options Signal Data Collector` tables during the 30-second run. They were terminal redraws rather than persistent log lines. Exit code: `0`.

### 4. Explicit summarize

Command:

```powershell
.\.venv\Scripts\python.exe -m src.main summarize --run-folder C:\workspace\options_alert_engine\data\runs\mock_blocker_verify_20260629_001603
```

Exact output:

```text
summary_by_contract=C:\workspace\options_alert_engine\data\runs\mock_blocker_verify_20260629_001603\summary_by_contract.csv
summary_by_signal=C:\workspace\options_alert_engine\data\runs\mock_blocker_verify_20260629_001603\summary_by_signal.csv
sqlite=C:\workspace\options_alert_engine\data\runs\mock_blocker_verify_20260629_001603\market_capture.sqlite
```

Exit code: `0`

### 5. Corrected artifact verification

Exact output:

```text
EXISTS=True BYTES=2206 LINES=15 PATH=C:\workspace\options_alert_engine\pytest_output.txt
EXISTS=True BYTES=9161 LINES=21 PATH=C:\workspace\options_alert_engine\data\runs\mock_blocker_verify_20260629_001603\summary_by_contract.csv
EXISTS=True BYTES=1044 LINES=3 PATH=C:\workspace\options_alert_engine\data\runs\mock_blocker_verify_20260629_001603\summary_by_signal.csv
EXISTS=True BYTES=237337 LINES=521 PATH=C:\workspace\options_alert_engine\data\runs\mock_blocker_verify_20260629_001603\option_ticks.csv
EXISTS=True BYTES=13291 LINES=53 PATH=C:\workspace\options_alert_engine\data\runs\mock_blocker_verify_20260629_001603\stock_ticks.csv
EXISTS=True BYTES=565 LINES=3 PATH=C:\workspace\options_alert_engine\data\runs\mock_blocker_verify_20260629_001603\signals.csv
EXISTS=True BYTES=215 LINES=1 PATH=C:\workspace\options_alert_engine\data\runs\mock_blocker_verify_20260629_001603\provider_errors.csv
EXISTS=True BYTES=397312 LINES=n/a PATH=C:\workspace\options_alert_engine\data\runs\mock_blocker_verify_20260629_001603\market_capture.sqlite
```

`provider_errors.csv` contains its header and zero error rows.

## First Five Contract Summary Rows

The header plus the first five data rows are shown verbatim:

```csv
signal_id,underlying_symbol,option_symbol,contract_role,expiry,strike,option_type,min_mid_after_signal,max_mid_after_signal,min_ask_after_signal,max_bid_after_signal,best_theoretical_mid_return,raw_unfiltered_ask_to_bid_return,best_conservative_ask_to_bid_return,time_of_min_ask,time_of_max_bid_after_min_ask,max_compression_pct,max_rebound_pct,percentage_of_valid_quotes,median_spread_pct,max_spread_pct,best_quote_valid,was_best_move_tradable,hit_40pct_executable,hit_50pct_executable,hit_100pct_executable,hit_180pct_executable,time_hit_40pct,time_hit_50pct,time_hit_100pct,time_hit_180pct
BEAM_20260625_100500_CALL_40p0,BEAM,BEAM260717C00040000,SIGNAL_CONTRACT,2026-07-17,40.0,CALL,0.33,0.66,0.35,0.62,1.0,0.26530612244897966,0.26530612244897966,2026-06-29T00:16:04.080239-05:00,2026-06-29T00:16:06.467670-05:00,28.26086956521739,43.47826086956522,100.0,11.428571428571423,13.114754098360669,True,True,False,False,False,False,,,,
BEAM_20260625_100500_CALL_40p0,BEAM,BEAM260717P00030000,LOTTO_OBSERVATION_ONLY,2026-07-17,30.0,PUT,0.18,0.5,0.2,0.47,1.7777777777777777,1.3499999999999996,1.3499999999999996,2026-06-29T00:16:07.703194-05:00,2026-06-29T00:16:11.188400-05:00,41.935483870967744,177.7777777777778,100.0,14.814814814814806,22.222222222222225,True,True,True,True,True,False,2026-06-29T00:16:10.013808-05:00,2026-06-29T00:16:11.188400-05:00,2026-06-29T00:16:11.188400-05:00,
BEAM_20260625_100500_CALL_40p0,BEAM,BEAM260717P00031000,OTM_OPPOSITE,2026-07-17,31.0,PUT,0.71,2.3,0.75,2.16,2.23943661971831,1.8800000000000003,1.8800000000000003,2026-06-29T00:16:08.826677-05:00,2026-06-29T00:16:13.468234-05:00,58.72093023255815,223.943661971831,100.0,12.5,12.727272727272718,True,True,True,True,True,True,2026-06-29T00:16:11.152600-05:00,2026-06-29T00:16:11.152600-05:00,2026-06-29T00:16:12.308410-05:00,2026-06-29T00:16:13.468234-05:00
BEAM_20260625_100500_CALL_40p0,BEAM,BEAM260717P00032000,OTM_OPPOSITE,2026-07-17,32.0,PUT,0.7,2.29,0.74,2.15,2.271428571428572,1.9054054054054053,1.9054054054054053,2026-06-29T00:16:08.834509-05:00,2026-06-29T00:16:13.474746-05:00,58.82352941176471,227.1428571428572,100.0,11.57894736842104,12.844036697247695,True,True,True,True,True,True,2026-06-29T00:16:11.159898-05:00,2026-06-29T00:16:11.159898-05:00,2026-06-29T00:16:12.315408-05:00,2026-06-29T00:16:13.474746-05:00
BEAM_20260625_100500_CALL_40p0,BEAM,BEAM260717P00033000,OTM_OPPOSITE,2026-07-17,33.0,PUT,0.69,2.28,0.73,2.14,2.3043478260869565,1.9315068493150687,1.9315068493150687,2026-06-29T00:16:08.842734-05:00,2026-06-29T00:16:13.487170-05:00,59.171597633136095,230.43478260869568,100.0,11.64021164021164,12.359550561797752,True,True,True,True,True,True,2026-06-29T00:16:11.166898-05:00,2026-06-29T00:16:11.166898-05:00,2026-06-29T00:16:12.322406-05:00,2026-06-29T00:16:13.487170-05:00
```

## First Five Signal Summary Rows

The file contains two data rows, so both available rows are shown with the header:

```csv
signal_id,symbol,best_contract_by_mid_return,best_contract_by_conservative_return,best_ATM_or_OTM_contract,best_lotto_contract,number_of_valid_contracts,number_of_untradable_contracts,signal_direction_stock_result,opposite_side_opportunity_found,opportunity_score,news_provider,news_count_24h,news_count_7d,latest_news_age_minutes,catalyst_detected,catalyst_type,news_bias,news_score,news_score_effective,news_source_confidence,news_affects_score,top_headlines_24h,news_skip_warning,skip_reason
BEAM_20260625_100500_CALL_40p0,BEAM,BEAM260717P00040000,BEAM260717P00037000,BEAM260717P00036000,BEAM260717P00030000,8,1,PUMP_THEN_FAILED,True,74.5,mock,1,1,180.0,False,UNKNOWN,UNKNOWN,45.0,,MOCK,False,BEAM sees unusual options interest without confirmed company catalyst,,
VRNS_20260625_100700_CALL_40p0,VRNS,VRNS260717P00037000,VRNS260717P00037000,VRNS260717P00036000,VRNS260717P00030000,7,2,PUMP_THEN_FAILED,True,74.5,mock,1,1,180.0,False,UNKNOWN,UNKNOWN,45.0,,MOCK,False,VRNS sees unusual options interest without confirmed company catalyst,,
```

Mock news is correctly marked `MOCK`, `news_affects_score=False`, with an empty effective score.

## Errors Encountered

Application, test, collection, summarize, and provider errors: none.

One verification-only PowerShell command initially constructed the path array incorrectly. Exact error:

```text
Join-Path : Cannot convert 'System.Object[]' to the type 'System.String' required by parameter 'ChildPath'. Specified method is not supported.
```

Impact: none. It occurred after the run while checking file existence. The command was corrected and all eight required files returned `EXISTS=True`. `provider_errors.csv` has zero data rows.

## Final Verification Verdict

`PASS_MOCK_RUN_VERIFIED`

The requested reviewer artifacts exist at the absolute paths listed above. This verification used only the mock provider and made no live broker connection.
