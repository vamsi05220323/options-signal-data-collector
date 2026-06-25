from __future__ import annotations

import pandas as pd


def score_signal(
    signal_id: str,
    contract_rows: pd.DataFrame,
    stock_rows: pd.DataFrame,
    news_row: pd.Series | None = None,
) -> tuple[float, str, bool, str]:
    if contract_rows.empty:
        return 0.0, "NO_DATA", False, "no_contract_rows"

    best_return = _max_float(contract_rows.get("best_conservative_ask_to_bid_return"))
    best_compression = _max_float(contract_rows.get("max_compression_pct"))
    best_rebound = _max_float(contract_rows.get("max_rebound_pct"))
    valid_contracts = int((pd.to_numeric(contract_rows["percentage_of_valid_quotes"], errors="coerce") >= 50).sum())
    median_spread = pd.to_numeric(contract_rows["median_spread_pct"], errors="coerce").median()

    stock_result = classify_stock_result(stock_rows)
    microstructure = 0.0
    microstructure += min(max(best_return or 0.0, 0.0) * 100, 35)
    microstructure += min((best_compression or 0.0) / 2, 15)
    microstructure += min((best_rebound or 0.0) / 3, 15)
    microstructure += min(valid_contracts * 4, 20)
    if pd.notna(median_spread):
        microstructure += max(0, 15 - float(median_spread) / 4)
    if stock_result == "PUMP_THEN_FAILED":
        microstructure += 10
    microstructure = min(microstructure, 100.0)

    news_score = 50.0
    if news_row is not None and "news_score" in news_row:
        try:
            news_score = float(news_row["news_score"])
        except (TypeError, ValueError):
            news_score = 50.0

    signal_side_score = score_signal_contract(contract_rows)
    total = microstructure * 0.70 + news_score * 0.20 + signal_side_score * 0.10
    opportunity_found = bool(best_return is not None and best_return > 0.20 and valid_contracts > 0)
    skip_reason = "" if opportunity_found else "insufficient_executable_bid_ask_evidence"
    return round(max(0.0, min(total, 100.0)), 2), stock_result, opportunity_found, skip_reason


def classify_stock_result(stock_rows: pd.DataFrame) -> str:
    if stock_rows.empty:
        return "UNKNOWN"
    start = _first_float(stock_rows.get("stock_price_at_signal"))
    high = _max_float(stock_rows.get("post_signal_high"))
    last = _last_float(stock_rows.get("stock_last"))
    if start is None or high is None or last is None or start <= 0:
        return "UNKNOWN"
    pump_pct = (high - start) / start * 100.0
    pullback_pct = (high - last) / high * 100.0 if high > 0 else 0.0
    if pump_pct >= 1.0 and pullback_pct >= 1.0:
        return "PUMP_THEN_FAILED"
    if last > start:
        return "SIGNAL_DIRECTION_UP"
    if last < start:
        return "SIGNAL_DIRECTION_FAILED"
    return "FLAT"


def score_signal_contract(contract_rows: pd.DataFrame) -> float:
    signal_rows = contract_rows[contract_rows["contract_role"] == "SIGNAL_CONTRACT"]
    if signal_rows.empty:
        return 50.0
    best_return = _max_float(signal_rows.get("best_theoretical_mid_return"))
    conservative = _max_float(signal_rows.get("best_conservative_ask_to_bid_return"))
    if conservative is not None and conservative < 0:
        return 65.0
    if best_return is not None and best_return < 0:
        return 60.0
    return 45.0


def _max_float(values) -> float | None:
    if values is None:
        return None
    numeric = pd.to_numeric(values, errors="coerce").dropna()
    return None if numeric.empty else float(numeric.max())


def _first_float(values) -> float | None:
    if values is None:
        return None
    numeric = pd.to_numeric(values, errors="coerce").dropna()
    return None if numeric.empty else float(numeric.iloc[0])


def _last_float(values) -> float | None:
    if values is None:
        return None
    numeric = pd.to_numeric(values, errors="coerce").dropna()
    return None if numeric.empty else float(numeric.iloc[-1])
