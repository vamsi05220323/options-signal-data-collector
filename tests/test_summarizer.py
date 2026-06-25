from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd

from src.config import AppConfig
from src.engine.summarizer import best_ask_to_future_bid, build_contract_summary


def test_conservative_return_uses_future_bid_after_earlier_ask():
    ts = datetime(2026, 6, 25, 10, 0, tzinfo=ZoneInfo("America/Chicago"))
    group = pd.DataFrame(
        [
            {"timestamp_local": ts, "ask": 1.00, "bid": 0.90},
            {"timestamp_local": ts + timedelta(seconds=1), "ask": 0.70, "bid": 0.62},
            {"timestamp_local": ts + timedelta(seconds=2), "ask": 1.80, "bid": 1.50},
        ]
    )
    best_return, ask_time, bid_time = best_ask_to_future_bid(group)
    assert round(best_return, 4) == round(1.50 / 0.70 - 1, 4)
    assert ask_time
    assert bid_time


def test_contract_summary_marks_tradable_move():
    ts = datetime(2026, 6, 25, 10, 0, tzinfo=ZoneInfo("America/Chicago"))
    df = pd.DataFrame(
        [
            {
                "timestamp_local": ts.isoformat(),
                "signal_id": "S1",
                "underlying_symbol": "BEAM",
                "option_symbol": "BEAM_TEST",
                "contract_role": "OTM_OPPOSITE",
                "expiry": "2026-07-17",
                "strike": 32,
                "option_type": "PUT",
                "bid": 0.90,
                "ask": 1.00,
                "mid": 0.95,
                "spread_pct": 10,
                "compression_from_initial_pct": 50,
                "rebound_from_low_pct": 100,
                "quote_is_valid": "true",
            },
            {
                "timestamp_local": (ts + timedelta(seconds=1)).isoformat(),
                "signal_id": "S1",
                "underlying_symbol": "BEAM",
                "option_symbol": "BEAM_TEST",
                "contract_role": "OTM_OPPOSITE",
                "expiry": "2026-07-17",
                "strike": 32,
                "option_type": "PUT",
                "bid": 1.50,
                "ask": 1.65,
                "mid": 1.575,
                "spread_pct": 9,
                "compression_from_initial_pct": 50,
                "rebound_from_low_pct": 100,
                "quote_is_valid": "true",
            },
        ]
    )
    rows = build_contract_summary(df, AppConfig())
    assert rows[0]["was_best_move_tradable"] is True
