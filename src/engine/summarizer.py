from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.config import AppConfig
from src.engine.scoring import OPPOSITE_ROLES, score_signal
from src.storage.csv_writer import (
    CONTRACT_SUMMARY_FIELDS,
    NEWS_SUMMARY_FIELDS,
    OPTION_BAR_FIELDS,
    SIGNAL_SUMMARY_FIELDS,
)
from src.storage.sqlite_store import RunStorage


def summarize_run(run_folder: Path, config: AppConfig) -> dict[str, Path]:
    storage = RunStorage(run_folder)
    option_path = run_folder / "option_ticks.csv"
    stock_path = run_folder / "stock_ticks.csv"
    signal_path = run_folder / "signals.csv"
    news_summary_path = run_folder / "news_summary_by_signal.csv"

    option_df = _read_csv(option_path)
    stock_df = _read_csv(stock_path)
    signals_df = _read_csv(signal_path)
    news_df = _read_csv(news_summary_path)

    contract_rows = build_contract_summary(option_df, config)
    storage.rewrite_table("contract_summary", contract_rows)

    storage.rewrite_table("option_bars_5sec", build_option_bars(option_df, "5s"))
    storage.rewrite_table("option_bars_1m", build_option_bars(option_df, "1min"))
    storage.rewrite_table("option_bars_5m", build_option_bars(option_df, "5min"))

    signal_rows = build_signal_summary(signals_df, stock_df, pd.DataFrame(contract_rows), news_df)
    storage.rewrite_table("signal_summary", signal_rows)
    storage.close()
    return {
        "summary_by_contract": run_folder / "summary_by_contract.csv",
        "summary_by_signal": run_folder / "summary_by_signal.csv",
        "sqlite": run_folder / "market_capture.sqlite",
    }


def build_contract_summary(option_df: pd.DataFrame, config: AppConfig) -> list[dict]:
    if option_df.empty:
        return []
    df = option_df.copy()
    defaults = {
        "quote_is_valid": False,
        "quote_age_seconds": None,
        "crossed_market_flag": False,
        "locked_market_flag": False,
        "intrinsic_violation_flag": True,
    }
    for column, default in defaults.items():
        if column not in df:
            df[column] = default
    for column in ["bid", "ask", "mid", "spread_pct", "compression_from_initial_pct", "rebound_from_low_pct"]:
        df[column] = pd.to_numeric(df[column], errors="coerce")
    df["timestamp_local"] = pd.to_datetime(df["timestamp_local"], errors="coerce")
    df["quote_is_valid_bool"] = df["quote_is_valid"].astype(str).str.lower().isin({"true", "1", "yes"})

    rows: list[dict] = []
    group_cols = ["signal_id", "underlying_symbol", "option_symbol", "contract_role", "expiry", "strike", "option_type"]
    for keys, group in df.sort_values("timestamp_local").groupby(group_cols, dropna=False):
        valid_group = group[group["quote_is_valid_bool"]]
        min_mid = _safe_min(group["mid"])
        max_mid = _safe_max(group["mid"])
        min_ask = _safe_min(group["ask"])
        max_bid = _safe_max(group["bid"])
        raw_return, _raw_ask_time, _raw_bid_time = best_ask_to_future_bid(group, valid_only=False)
        best_return, min_ask_time, max_bid_time, threshold_times = executable_return_analysis(
            group,
            stale_quote_seconds=config.stale_quote_seconds,
            allow_locked_market=config.allow_locked_market,
        )
        theoretical = None
        if min_mid is not None and min_mid > 0 and max_mid is not None:
            theoretical = max_mid / min_mid - 1.0
        valid_pct = float(group["quote_is_valid_bool"].mean() * 100.0) if len(group) else 0.0
        median_spread = _safe_median(valid_group["spread_pct"])
        max_spread = _safe_max(valid_group["spread_pct"])
        best_valid = bool(valid_pct >= 50 and (median_spread is None or median_spread <= config.wide_spread_max_pct))
        tradable = bool(best_return is not None and best_return > 0.20 and best_valid)
        row = dict(zip(group_cols, keys, strict=True))
        row.update(
            {
                "min_mid_after_signal": min_mid,
                "max_mid_after_signal": max_mid,
                "min_ask_after_signal": min_ask,
                "max_bid_after_signal": max_bid,
                "best_theoretical_mid_return": theoretical,
                "raw_unfiltered_ask_to_bid_return": raw_return,
                "best_conservative_ask_to_bid_return": best_return,
                "time_of_min_ask": min_ask_time,
                "time_of_max_bid_after_min_ask": max_bid_time,
                "max_compression_pct": _safe_max(valid_group["compression_from_initial_pct"]),
                "max_rebound_pct": _safe_max(valid_group["rebound_from_low_pct"]),
                "percentage_of_valid_quotes": valid_pct,
                "median_spread_pct": median_spread,
                "max_spread_pct": max_spread,
                "best_quote_valid": best_valid,
                "was_best_move_tradable": tradable,
                "hit_40pct_executable": bool(threshold_times[0.40]),
                "hit_50pct_executable": bool(threshold_times[0.50]),
                "hit_100pct_executable": bool(threshold_times[1.00]),
                "hit_180pct_executable": bool(threshold_times[1.80]),
                "time_hit_40pct": threshold_times[0.40],
                "time_hit_50pct": threshold_times[0.50],
                "time_hit_100pct": threshold_times[1.00],
                "time_hit_180pct": threshold_times[1.80],
            }
        )
        rows.append(_ordered(row, CONTRACT_SUMMARY_FIELDS))
    return rows


def build_signal_summary(
    signals_df: pd.DataFrame,
    stock_df: pd.DataFrame,
    contract_df: pd.DataFrame,
    news_df: pd.DataFrame,
) -> list[dict]:
    rows: list[dict] = []
    if signals_df.empty:
        return rows
    for _, signal in signals_df.iterrows():
        signal_id = signal["signal_id"]
        contracts = contract_df[contract_df["signal_id"] == signal_id] if not contract_df.empty else pd.DataFrame()
        opposite_contracts = (
            contracts[contracts["contract_role"].isin(OPPOSITE_ROLES)] if not contracts.empty else contracts
        )
        stocks = stock_df[stock_df["signal_id"] == signal_id] if not stock_df.empty else pd.DataFrame()
        news_row = None
        if not news_df.empty:
            matches = news_df[news_df["signal_id"] == signal_id]
            if not matches.empty:
                news_row = matches.iloc[-1]
        score, stock_result, found, skip_reason = score_signal(signal_id, contracts, stocks, news_row)
        row = {
            "signal_id": signal_id,
            "symbol": signal["symbol"],
            "best_contract_by_mid_return": _best_contract(opposite_contracts, "best_theoretical_mid_return"),
            "best_contract_by_conservative_return": _best_contract(
                opposite_contracts, "best_conservative_ask_to_bid_return"
            ),
            "best_ATM_or_OTM_contract": _best_contract(
                contracts[contracts["contract_role"].isin(["ATM_OPPOSITE", "OTM_OPPOSITE"])]
                if not contracts.empty
                else contracts,
                "best_conservative_ask_to_bid_return",
            ),
            "best_lotto_contract": _best_contract(
                contracts[contracts["contract_role"] == "LOTTO_OBSERVATION_ONLY"] if not contracts.empty else contracts,
                "best_conservative_ask_to_bid_return",
            ),
            "number_of_valid_contracts": _count_valid_contracts(opposite_contracts),
            "number_of_untradable_contracts": _count_untradable_contracts(opposite_contracts),
            "signal_direction_stock_result": stock_result,
            "opposite_side_opportunity_found": found,
            "opportunity_score": score,
            "skip_reason": skip_reason,
        }
        row.update(_news_summary_columns(news_row))
        rows.append(_ordered(row, SIGNAL_SUMMARY_FIELDS))
    return rows


def build_option_bars(option_df: pd.DataFrame, frequency: str) -> list[dict]:
    if option_df.empty:
        return []
    df = option_df.copy()
    df["timestamp_local"] = pd.to_datetime(df["timestamp_local"], errors="coerce")
    df = df.dropna(subset=["timestamp_local"])
    for column in ["mid", "bid", "ask", "spread_pct"]:
        df[column] = pd.to_numeric(df[column], errors="coerce")
    df["quote_is_valid_bool"] = df["quote_is_valid"].astype(str).str.lower().isin({"true", "1", "yes"})
    rows: list[dict] = []
    group_cols = ["signal_id", "underlying_symbol", "option_symbol", "contract_role", "expiry", "strike", "option_type"]
    for keys, group in df.groupby(group_cols, dropna=False):
        indexed = group.set_index("timestamp_local").sort_index()
        for bar_start, bar in indexed.resample(frequency):
            if bar.empty:
                continue
            row = dict(zip(group_cols, keys, strict=True))
            row.update(
                {
                    "bar_start": bar_start.isoformat(),
                    "open_mid": _first_valid(bar["mid"]),
                    "high_mid": _safe_max(bar["mid"]),
                    "low_mid": _safe_min(bar["mid"]),
                    "close_mid": _last_valid(bar["mid"]),
                    "open_bid": _first_valid(bar["bid"]),
                    "high_bid": _safe_max(bar["bid"]),
                    "low_bid": _safe_min(bar["bid"]),
                    "close_bid": _last_valid(bar["bid"]),
                    "open_ask": _first_valid(bar["ask"]),
                    "high_ask": _safe_max(bar["ask"]),
                    "low_ask": _safe_min(bar["ask"]),
                    "close_ask": _last_valid(bar["ask"]),
                    "ticks": len(bar),
                    "valid_quote_ratio": float(bar["quote_is_valid_bool"].mean()) if len(bar) else 0.0,
                    "median_spread_pct": _safe_median(bar["spread_pct"]),
                }
            )
            rows.append(_ordered(row, OPTION_BAR_FIELDS))
    return rows


def best_ask_to_future_bid(
    group: pd.DataFrame,
    *,
    valid_only: bool = True,
    stale_quote_seconds: int = 900,
    allow_locked_market: bool = False,
) -> tuple[float | None, str, str]:
    if valid_only:
        best_return, ask_time, bid_time, _thresholds = executable_return_analysis(
            group,
            stale_quote_seconds=stale_quote_seconds,
            allow_locked_market=allow_locked_market,
        )
        return best_return, ask_time, bid_time
    ordered = group.sort_values("timestamp_local").reset_index(drop=True)
    best_return: float | None = None
    best_ask_time = ""
    best_bid_time = ""
    for idx, row in ordered.iterrows():
        ask = row.get("ask")
        if pd.isna(ask) or ask <= 0:
            continue
        future = ordered.loc[idx:, ["bid", "timestamp_local"]].dropna()
        if future.empty:
            continue
        best_future_idx = future["bid"].astype(float).idxmax()
        future_bid = float(ordered.loc[best_future_idx, "bid"])
        candidate = future_bid / float(ask) - 1.0
        if best_return is None or candidate > best_return:
            best_return = candidate
            best_ask_time = row["timestamp_local"].isoformat() if pd.notna(row["timestamp_local"]) else ""
            bid_time = ordered.loc[best_future_idx, "timestamp_local"]
            best_bid_time = bid_time.isoformat() if pd.notna(bid_time) else ""
    return best_return, best_ask_time, best_bid_time


def executable_return_analysis(
    group: pd.DataFrame,
    *,
    stale_quote_seconds: int = 900,
    allow_locked_market: bool = False,
) -> tuple[float | None, str, str, dict[float, str]]:
    ordered = group.sort_values("timestamp_local").reset_index(drop=True)
    best_return: float | None = None
    best_ask_time = ""
    best_bid_time = ""
    threshold_datetimes = {0.40: None, 0.50: None, 1.00: None, 1.80: None}
    for entry_idx, entry in ordered.iterrows():
        ask = _numeric_value(entry.get("ask"))
        if ask is None or ask <= 0.01:
            continue
        if not _eligible_executable_row(entry, stale_quote_seconds, allow_locked_market):
            continue
        for exit_idx in range(entry_idx, len(ordered)):
            exit_row = ordered.iloc[exit_idx]
            bid = _numeric_value(exit_row.get("bid"))
            if bid is None or bid <= 0:
                continue
            if not _eligible_executable_row(exit_row, stale_quote_seconds, allow_locked_market):
                continue
            candidate = bid / ask - 1.0
            entry_time = entry.get("timestamp_local")
            exit_time = exit_row.get("timestamp_local")
            if best_return is None or candidate > best_return:
                best_return = candidate
                best_ask_time = entry_time.isoformat() if pd.notna(entry_time) else ""
                best_bid_time = exit_time.isoformat() if pd.notna(exit_time) else ""
            for threshold in threshold_datetimes:
                current_hit = threshold_datetimes[threshold]
                if candidate >= threshold and pd.notna(exit_time) and (current_hit is None or exit_time < current_hit):
                    threshold_datetimes[threshold] = exit_time
    threshold_times = {
        threshold: hit.isoformat() if hit is not None else "" for threshold, hit in threshold_datetimes.items()
    }
    return best_return, best_ask_time, best_bid_time, threshold_times


def _eligible_executable_row(row: pd.Series, stale_quote_seconds: int, allow_locked_market: bool) -> bool:
    if not _bool_value(row.get("quote_is_valid")):
        return False
    age = _numeric_value(row.get("quote_age_seconds"))
    if age is None or age > stale_quote_seconds:
        return False
    bid = _numeric_value(row.get("bid"))
    ask = _numeric_value(row.get("ask"))
    if bid is not None and ask is not None and bid > ask:
        return False
    if _bool_value(row.get("crossed_market_flag")):
        return False
    locked = bool(bid is not None and ask is not None and bid == ask) or _bool_value(row.get("locked_market_flag"))
    if locked and not allow_locked_market:
        return False
    if _bool_value(row.get("intrinsic_violation_flag")):
        return False
    confidence = str(row.get("intrinsic_validation_confidence") or "UNKNOWN").strip().upper()
    if confidence not in {"HIGH_LIVE", "MOCK"}:
        return False
    market_data_type = str(row.get("market_data_type") or "unknown").strip().lower()
    if market_data_type not in {"live", "mock", "replay"}:
        return False
    return True


def _numeric_value(value) -> float | None:
    try:
        if value is None or pd.isna(value):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _bool_value(value) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes"}


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    return pd.read_csv(path)


def _safe_min(values) -> float | None:
    values = pd.to_numeric(values, errors="coerce").dropna()
    return None if values.empty else float(values.min())


def _safe_max(values) -> float | None:
    values = pd.to_numeric(values, errors="coerce").dropna()
    return None if values.empty else float(values.max())


def _safe_median(values) -> float | None:
    values = pd.to_numeric(values, errors="coerce").dropna()
    return None if values.empty else float(values.median())


def _first_valid(values) -> float | None:
    values = pd.to_numeric(values, errors="coerce").dropna()
    return None if values.empty else float(values.iloc[0])


def _last_valid(values) -> float | None:
    values = pd.to_numeric(values, errors="coerce").dropna()
    return None if values.empty else float(values.iloc[-1])


def _best_contract(contracts: pd.DataFrame, column: str) -> str:
    if contracts.empty or column not in contracts:
        return ""
    values = pd.to_numeric(contracts[column], errors="coerce")
    if values.dropna().empty:
        return ""
    idx = values.idxmax()
    return str(contracts.loc[idx, "option_symbol"])


def _count_valid_contracts(contracts: pd.DataFrame) -> int:
    if contracts.empty:
        return 0
    return int((pd.to_numeric(contracts["percentage_of_valid_quotes"], errors="coerce") >= 50).sum())


def _count_untradable_contracts(contracts: pd.DataFrame) -> int:
    if contracts.empty:
        return 0
    tradable = contracts["was_best_move_tradable"].astype(str).str.lower().isin({"true", "1", "yes"})
    return int((~tradable).sum())


def _news_summary_columns(news_row: pd.Series | None) -> dict:
    fields = [
        "news_provider",
        "news_count_24h",
        "news_count_7d",
        "latest_news_age_minutes",
        "catalyst_detected",
        "catalyst_type",
        "news_bias",
        "news_score",
        "news_score_effective",
        "news_source_confidence",
        "news_affects_score",
        "top_headlines_24h",
        "news_skip_warning",
    ]
    if news_row is None:
        return {field: None for field in fields}
    return {
        field: None if pd.isna(news_row.get(field)) else news_row.get(field)
        for field in fields
    }


def _ordered(row: dict, fields: list[str]) -> dict:
    return {field: row.get(field) for field in fields}
