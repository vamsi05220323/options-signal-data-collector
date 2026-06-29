from __future__ import annotations

import csv
from pathlib import Path
from typing import Any


SIGNAL_FIELDS = [
    "signal_id",
    "timestamp_local",
    "symbol",
    "direction",
    "signal_strike",
    "expiry",
    "signal_premium",
    "stock_price_at_signal",
    "opposite_direction",
    "provider",
    "status",
    "underlying_exchange",
    "primary_exchange",
    "currency",
    "ibkr_con_id",
    "ibkr_local_symbol",
    "ibkr_trading_class",
    "contract_resolution_status",
    "contract_resolution_message",
]

STOCK_TICK_FIELDS = [
    "timestamp_local",
    "signal_id",
    "symbol",
    "stock_bid",
    "stock_ask",
    "stock_last",
    "stock_mid",
    "stock_volume",
    "seconds_since_signal",
    "stock_price_at_signal",
    "post_signal_high",
    "post_signal_low",
    "stock_change_from_signal_pct",
    "pump_from_signal_pct",
    "pullback_from_high_pct",
    "stock_price_source",
    "stock_quote_status",
    "fallback_used",
    "stock_quote_is_live",
    "market_data_type",
    "quote_source_timestamp",
    "quote_age_seconds",
]

OPTION_TICK_FIELDS = [
    "timestamp_local",
    "signal_id",
    "underlying_symbol",
    "option_symbol",
    "option_con_id",
    "option_local_symbol",
    "option_trading_class",
    "option_exchange",
    "contract_role",
    "expiry",
    "strike",
    "option_type",
    "bid",
    "ask",
    "mid",
    "last",
    "volume",
    "open_interest",
    "implied_volatility",
    "delta",
    "gamma",
    "theta",
    "vega",
    "bid_size",
    "ask_size",
    "raw_spread_abs",
    "spread_abs",
    "spread_pct",
    "crossed_market_flag",
    "locked_market_flag",
    "intrinsic_value",
    "raw_extrinsic_value",
    "extrinsic_value",
    "intrinsic_violation_flag",
    "intrinsic_violation_amount",
    "intrinsic_violation_pct",
    "intrinsic_validation_confidence",
    "market_data_type",
    "quote_timestamp",
    "quote_source_timestamp",
    "quote_age_seconds",
    "quote_is_valid",
    "reason_invalid",
    "seconds_since_signal",
    "option_initial_mid",
    "option_min_mid_since_signal",
    "option_max_mid_since_signal",
    "option_min_ask_since_signal",
    "option_max_bid_since_signal",
    "compression_from_initial_pct",
    "rebound_from_low_pct",
]

OPTION_BAR_FIELDS = [
    "bar_start",
    "signal_id",
    "underlying_symbol",
    "option_symbol",
    "contract_role",
    "expiry",
    "strike",
    "option_type",
    "open_mid",
    "high_mid",
    "low_mid",
    "close_mid",
    "open_bid",
    "high_bid",
    "low_bid",
    "close_bid",
    "open_ask",
    "high_ask",
    "low_ask",
    "close_ask",
    "ticks",
    "valid_quote_ratio",
    "median_spread_pct",
]

CONTRACT_SUMMARY_FIELDS = [
    "signal_id",
    "underlying_symbol",
    "option_symbol",
    "contract_role",
    "expiry",
    "strike",
    "option_type",
    "min_mid_after_signal",
    "max_mid_after_signal",
    "min_ask_after_signal",
    "max_bid_after_signal",
    "best_theoretical_mid_return",
    "raw_unfiltered_ask_to_bid_return",
    "best_conservative_ask_to_bid_return",
    "time_of_min_ask",
    "time_of_max_bid_after_min_ask",
    "max_compression_pct",
    "max_rebound_pct",
    "percentage_of_valid_quotes",
    "median_spread_pct",
    "max_spread_pct",
    "best_quote_valid",
    "was_best_move_tradable",
    "hit_40pct_executable",
    "hit_50pct_executable",
    "hit_100pct_executable",
    "hit_180pct_executable",
    "time_hit_40pct",
    "time_hit_50pct",
    "time_hit_100pct",
    "time_hit_180pct",
]

SIGNAL_SUMMARY_FIELDS = [
    "signal_id",
    "symbol",
    "best_contract_by_mid_return",
    "best_contract_by_conservative_return",
    "best_ATM_or_OTM_contract",
    "best_lotto_contract",
    "number_of_valid_contracts",
    "number_of_untradable_contracts",
    "signal_direction_stock_result",
    "opposite_side_opportunity_found",
    "opportunity_score",
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
    "skip_reason",
]

NEWS_ARTICLE_FIELDS = [
    "timestamp_collected",
    "signal_id",
    "symbol",
    "provider",
    "article_published_at",
    "article_age_minutes_at_signal",
    "source",
    "headline",
    "summary",
    "url",
    "related_tickers",
    "sentiment_label",
    "sentiment_score",
    "relevance_score",
    "catalyst_type",
    "is_within_24h",
    "is_within_7d",
]

NEWS_SUMMARY_FIELDS = [
    "signal_id",
    "symbol",
    "signal_timestamp_local",
    "news_provider",
    "news_count_24h",
    "news_count_7d",
    "latest_news_age_minutes",
    "positive_news_count_24h",
    "negative_news_count_24h",
    "neutral_news_count_24h",
    "avg_sentiment_24h",
    "avg_relevance_24h",
    "top_sources_24h",
    "top_headlines_24h",
    "catalyst_detected",
    "catalyst_type",
    "news_bias",
    "news_score",
    "news_score_effective",
    "news_source_confidence",
    "news_affects_score",
    "news_skip_warning",
    "news_notes",
]

PROVIDER_ERROR_FIELDS = [
    "timestamp_local",
    "signal_id",
    "underlying_symbol",
    "option_symbol",
    "intended_contract",
    "contract_role",
    "failure_stage",
    "provider",
    "provider_error_code",
    "provider_error_message",
    "market_data_type",
    "quote_source_timestamp",
    "quote_age_seconds",
]


class CsvTable:
    def __init__(self, path: Path, fieldnames: list[str]) -> None:
        self.path = path
        self.fieldnames = fieldnames
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            with self.path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=self.fieldnames)
                writer.writeheader()

    def append(self, row: dict[str, Any]) -> None:
        with self.path.open("a", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=self.fieldnames, extrasaction="ignore")
            writer.writerow({field: _csv_value(row.get(field)) for field in self.fieldnames})

    def rewrite(self, rows: list[dict[str, Any]]) -> None:
        with self.path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=self.fieldnames, extrasaction="ignore")
            writer.writeheader()
            for row in rows:
                writer.writerow({field: _csv_value(row.get(field)) for field in self.fieldnames})


def _csv_value(value: Any) -> Any:
    if value is None:
        return ""
    return value
