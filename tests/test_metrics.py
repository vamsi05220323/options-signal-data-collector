from src.engine.metrics import (
    compute_mid,
    compute_spread_pct,
    conservative_ask_to_bid_return,
    extrinsic_value,
    intrinsic_value,
    premium_compression_pct,
    rebound_from_low_pct,
)
from src.models import OptionType


def test_spread_intrinsic_extrinsic_and_returns():
    mid = compute_mid(0.80, 0.90)
    assert mid == 0.85
    assert round(compute_spread_pct(0.80, 0.90, mid), 3) == 11.765
    intrinsic = intrinsic_value(OptionType.PUT, 40, 35.60)
    assert round(intrinsic, 2) == 4.40
    assert round(extrinsic_value(5.10, intrinsic), 2) == 0.70
    assert premium_compression_pct(2.00, 1.00) == 50
    assert rebound_from_low_pct(1.50, 1.00) == 50
    assert conservative_ask_to_bid_return(1.00, 1.50) == 0.5
