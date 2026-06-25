import pandas as pd

from src.engine.scoring import score_signal


def test_scores_each_signal_independently():
    contracts = pd.DataFrame(
        [
            {
                "signal_id": "A",
                "contract_role": "OTM_OPPOSITE",
                "best_conservative_ask_to_bid_return": 0.75,
                "max_compression_pct": 45,
                "max_rebound_pct": 90,
                "percentage_of_valid_quotes": 90,
                "median_spread_pct": 12,
                "best_theoretical_mid_return": 1.0,
            }
        ]
    )
    stocks = pd.DataFrame(
        [{"stock_price_at_signal": 36.5, "post_signal_high": 38.0, "stock_last": 36.0}]
    )
    score, stock_result, found, skip = score_signal("A", contracts, stocks)
    assert score > 60
    assert stock_result == "PUMP_THEN_FAILED"
    assert found is True
    assert skip == ""
