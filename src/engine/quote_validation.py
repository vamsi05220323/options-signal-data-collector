from __future__ import annotations

from dataclasses import dataclass

from src.models import ContractRole


@dataclass(frozen=True, slots=True)
class QuoteValidation:
    is_valid: bool
    reason_invalid: str


def validate_quote(
    *,
    bid: float | None,
    ask: float | None,
    mid: float | None,
    spread_pct: float | None,
    spread_max_pct: float,
    role: ContractRole,
    volume: int | None = None,
    open_interest: int | None = None,
    quote_age_seconds: float | None = None,
    stale_quote_seconds: int = 900,
    crossed_market_flag: bool = False,
    locked_market_flag: bool = False,
    allow_locked_market: bool = False,
    intrinsic_violation_flag: bool = False,
) -> QuoteValidation:
    reasons: list[str] = []
    if bid is None:
        reasons.append("missing_bid")
    if ask is None:
        reasons.append("missing_ask")
    if ask is not None and ask <= 0:
        reasons.append("ask_lte_zero")
    if bid is not None and bid < 0:
        reasons.append("bid_lt_zero")
    if mid is None or mid <= 0:
        reasons.append("mid_lte_zero")
    if spread_pct is None:
        reasons.append("missing_spread")
    elif spread_pct > spread_max_pct:
        reasons.append("spread_too_wide")
    if _is_fake_penny_wide_quote(bid, ask):
        reasons.append("penny_bid_wide_ask")
    if crossed_market_flag:
        reasons.append("crossed_market")
    if locked_market_flag and not allow_locked_market:
        reasons.append("locked_market")
    if intrinsic_violation_flag:
        reasons.append("intrinsic_violation")
    if quote_age_seconds is not None and quote_age_seconds > stale_quote_seconds:
        reasons.append("stale_quote")
    if role is not ContractRole.LOTTO_OBSERVATION_ONLY:
        if (volume is None or volume <= 0) and (open_interest is None or open_interest <= 0):
            reasons.append("no_volume_or_open_interest")
    return QuoteValidation(is_valid=not reasons, reason_invalid=";".join(reasons))


def _is_fake_penny_wide_quote(bid: float | None, ask: float | None) -> bool:
    if bid is None or ask is None:
        return False
    return bid <= 0.01 and ask >= 0.10 and ask / max(bid, 0.01) >= 8.0
