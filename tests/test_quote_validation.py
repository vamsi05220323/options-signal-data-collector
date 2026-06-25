from src.engine.metrics import compute_mid, compute_spread_pct
from src.engine.quote_validation import validate_quote
from src.models import ContractRole


def test_rejects_wide_penny_quote():
    mid = compute_mid(0.01, 0.60)
    spread = compute_spread_pct(0.01, 0.60, mid)
    result = validate_quote(
        bid=0.01,
        ask=0.60,
        mid=mid,
        spread_pct=spread,
        spread_max_pct=300,
        role=ContractRole.OTM_OPPOSITE,
        volume=10,
        open_interest=10,
    )
    assert not result.is_valid
    assert "penny_bid_wide_ask" in result.reason_invalid


def test_lotto_allows_no_volume_or_oi():
    mid = compute_mid(0.10, 0.12)
    spread = compute_spread_pct(0.10, 0.12, mid)
    result = validate_quote(
        bid=0.10,
        ask=0.12,
        mid=mid,
        spread_pct=spread,
        spread_max_pct=60,
        role=ContractRole.LOTTO_OBSERVATION_ONLY,
        volume=0,
        open_interest=0,
    )
    assert result.is_valid
