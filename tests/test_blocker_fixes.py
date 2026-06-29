from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd

from src.config import AppConfig
from src.engine.capture_manager import _sanitize_news_error
from src.engine.metrics import (
    compute_mid,
    compute_raw_spread_abs,
    compute_spread_abs,
    compute_spread_pct,
    intrinsic_violation,
)
from src.engine.quote_validation import validate_quote
from src.engine.scoring import score_signal
from src.engine.summarizer import build_contract_summary
from src.models import ContractRole
from src.models import OptionType, TradeSignal
from src.news_providers.base import summarize_news
from src.news_providers.mock_news import MockNewsProvider


TZ = ZoneInfo("America/Chicago")


def test_signal_contract_cannot_create_opposite_opportunity():
    contracts = pd.DataFrame(
        [
            _contract_summary("SIGNAL_CONTRACT", 2.0),
            _contract_summary("OTM_OPPOSITE", -0.25),
        ]
    )
    stocks = pd.DataFrame([{"stock_price_at_signal": 100, "post_signal_high": 102, "stock_last": 99}])

    _score, _stock_result, found, skip = score_signal("S1", contracts, stocks)

    assert found is False
    assert skip == "insufficient_executable_bid_ask_evidence"


def test_invalid_rows_cannot_create_fake_conservative_profit():
    ts = datetime(2026, 6, 28, 10, 0, tzinfo=TZ)
    rows = pd.DataFrame(
        [
            _tick(ts, ask=0.10, bid=0.05, valid=False),
            _tick(ts + timedelta(seconds=1), ask=1.00, bid=0.90, valid=True),
            _tick(ts + timedelta(seconds=2), ask=5.00, bid=5.00, valid=False),
            _tick(ts + timedelta(seconds=3), ask=1.25, bid=1.20, valid=True),
        ]
    )

    summary = build_contract_summary(rows, AppConfig())[0]

    assert summary["raw_unfiltered_ask_to_bid_return"] == 49.0
    assert round(summary["best_conservative_ask_to_bid_return"], 6) == 0.20
    assert summary["hit_40pct_executable"] is False


def test_executable_threshold_flags_and_times_use_valid_quotes():
    ts = datetime(2026, 6, 28, 10, 0, tzinfo=TZ)
    rows = pd.DataFrame(
        [
            _tick(ts, ask=1.00, bid=0.95, valid=True),
            _tick(ts + timedelta(seconds=1), ask=1.45, bid=1.41, valid=True),
            _tick(ts + timedelta(seconds=2), ask=1.55, bid=1.51, valid=True),
            _tick(ts + timedelta(seconds=3), ask=2.05, bid=2.01, valid=True),
            _tick(ts + timedelta(seconds=4), ask=2.85, bid=2.81, valid=True),
        ]
    )

    summary = build_contract_summary(rows, AppConfig())[0]

    assert summary["hit_40pct_executable"] is True
    assert summary["hit_50pct_executable"] is True
    assert summary["hit_100pct_executable"] is True
    assert summary["hit_180pct_executable"] is True
    assert summary["time_hit_40pct"].endswith("10:00:01-05:00")
    assert summary["time_hit_180pct"].endswith("10:00:04-05:00")


def test_intrinsic_violation_flags_deep_itm_put_below_intrinsic():
    flag, amount, pct = intrinsic_violation(15.36, 14.10, 14.10, tolerance_abs=0.05, tolerance_pct=2.0)

    assert flag is True
    assert round(amount, 2) == 1.26
    assert round(pct, 2) == 8.20


def test_low_confidence_fallback_intrinsic_cannot_set_executable_return():
    ts = datetime(2026, 6, 28, 10, 0, tzinfo=TZ)
    rows = pd.DataFrame(
        [
            _tick(ts, ask=1.00, bid=0.90, valid=True),
            _tick(ts + timedelta(seconds=1), ask=2.10, bid=2.00, valid=True),
        ]
    )
    rows["intrinsic_validation_confidence"] = "LOW_FALLBACK"

    summary = build_contract_summary(rows, AppConfig())[0]

    assert summary["best_conservative_ask_to_bid_return"] is None
    assert summary["hit_100pct_executable"] is False


def test_crossed_market_preserves_raw_spread_and_is_invalid():
    bid, ask = 1.10, 1.00
    mid = compute_mid(bid, ask)
    spread = compute_spread_pct(bid, ask, mid)
    result = validate_quote(
        bid=bid,
        ask=ask,
        mid=mid,
        spread_pct=spread,
        spread_max_pct=35,
        role=ContractRole.OTM_OPPOSITE,
        volume=10,
        open_interest=10,
        crossed_market_flag=True,
    )

    assert round(compute_raw_spread_abs(bid, ask), 2) == -0.10
    assert round(compute_spread_abs(bid, ask), 2) == 0.10
    assert result.is_valid is False
    assert "crossed_market" in result.reason_invalid


def test_locked_market_is_invalid_unless_explicitly_allowed():
    base = dict(
        bid=1.00,
        ask=1.00,
        mid=1.00,
        spread_pct=0.0,
        spread_max_pct=35,
        role=ContractRole.OTM_OPPOSITE,
        volume=10,
        open_interest=10,
        locked_market_flag=True,
    )

    assert validate_quote(**base).is_valid is False
    assert validate_quote(**base, allow_locked_market=True).is_valid is True


def test_mock_news_cannot_change_opportunity_score():
    contracts = pd.DataFrame([_contract_summary("OTM_OPPOSITE", 0.75)])
    stocks = pd.DataFrame([{"stock_price_at_signal": 100, "post_signal_high": 102, "stock_last": 99}])
    without_news = score_signal("S1", contracts, stocks, None)[0]
    mock_news = pd.Series(
        {
            "news_score": 100,
            "news_score_effective": None,
            "news_source_confidence": "MOCK",
            "news_affects_score": False,
        }
    )

    with_mock = score_signal("S1", contracts, stocks, mock_news)[0]

    assert with_mock == without_news


def test_mock_news_summary_is_explicitly_non_scoring():
    signal = TradeSignal(
        signal_id="S1",
        timestamp_local=datetime(2026, 6, 28, 10, 0, tzinfo=TZ),
        symbol="XYZ",
        direction=OptionType.CALL,
        signal_strike=40,
        expiry=datetime(2026, 7, 17).date(),
        signal_premium=0.40,
        stock_price_at_signal=36.50,
    )
    provider = MockNewsProvider()
    articles = provider.fetch(signal, signal.timestamp_local)

    summary = summarize_news(signal, provider.name, articles)

    assert summary.news_score_effective is None
    assert summary.news_source_confidence == "MOCK"
    assert summary.news_affects_score is False


def test_news_errors_redact_configured_keys_and_query_tokens():
    config = AppConfig(alpha_vantage_api_key="secret-alpha", finnhub_api_key="secret-finnhub")
    error = RuntimeError("request failed apikey=secret-alpha&token=secret-finnhub")

    message = _sanitize_news_error(error, config)

    assert "secret-alpha" not in message
    assert "secret-finnhub" not in message
    assert message.count("[REDACTED]") == 2


def _contract_summary(role: str, conservative_return: float) -> dict:
    return {
        "signal_id": "S1",
        "contract_role": role,
        "best_conservative_ask_to_bid_return": conservative_return,
        "max_compression_pct": 50,
        "max_rebound_pct": 80,
        "percentage_of_valid_quotes": 100,
        "median_spread_pct": 10,
        "best_theoretical_mid_return": conservative_return,
    }


def _tick(timestamp: datetime, *, ask: float, bid: float, valid: bool) -> dict:
    mid = (ask + bid) / 2
    return {
        "timestamp_local": timestamp.isoformat(),
        "signal_id": "S1",
        "underlying_symbol": "XYZ",
        "option_symbol": "XYZ_TEST",
        "contract_role": "OTM_OPPOSITE",
        "expiry": "2026-07-17",
        "strike": 40,
        "option_type": "PUT",
        "bid": bid,
        "ask": ask,
        "mid": mid,
        "spread_pct": abs(ask - bid) / mid * 100,
        "compression_from_initial_pct": 10,
        "rebound_from_low_pct": 20,
        "quote_is_valid": valid,
        "quote_age_seconds": 0,
        "crossed_market_flag": False,
        "locked_market_flag": bid == ask,
        "intrinsic_violation_flag": False,
        "intrinsic_validation_confidence": "HIGH_LIVE",
        "market_data_type": "live",
    }
