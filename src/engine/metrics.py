from __future__ import annotations

from src.models import OptionType


def compute_mid(bid: float | None, ask: float | None) -> float | None:
    if bid is None or ask is None or bid < 0 or ask <= 0:
        return None
    mid = round((bid + ask) / 2.0, 10)
    return mid if mid > 0 else None


def compute_spread_abs(bid: float | None, ask: float | None) -> float | None:
    if bid is None or ask is None:
        return None
    return abs(ask - bid)


def compute_raw_spread_abs(bid: float | None, ask: float | None) -> float | None:
    if bid is None or ask is None:
        return None
    return ask - bid


def crossed_market(bid: float | None, ask: float | None) -> bool:
    return bool(bid is not None and ask is not None and bid > ask)


def locked_market(bid: float | None, ask: float | None) -> bool:
    return bool(bid is not None and ask is not None and bid == ask)


def compute_spread_pct(bid: float | None, ask: float | None, mid: float | None = None) -> float | None:
    mid = mid if mid is not None else compute_mid(bid, ask)
    spread = compute_spread_abs(bid, ask)
    if mid is None or mid <= 0 or spread is None:
        return None
    return spread / mid * 100.0


def intrinsic_value(option_type: OptionType | str, strike: float, stock_price: float | None) -> float | None:
    if stock_price is None:
        return None
    normalized = OptionType.from_text(option_type)
    if normalized is OptionType.PUT:
        return max(strike - stock_price, 0.0)
    return max(stock_price - strike, 0.0)


def extrinsic_value(mid: float | None, intrinsic: float | None) -> float | None:
    if mid is None or intrinsic is None:
        return None
    return max(mid - intrinsic, 0.0)


def raw_extrinsic_value(mid: float | None, intrinsic: float | None) -> float | None:
    if mid is None or intrinsic is None:
        return None
    return mid - intrinsic


def intrinsic_violation(
    intrinsic: float | None,
    mid: float | None,
    last: float | None,
    tolerance_abs: float,
    tolerance_pct: float,
) -> tuple[bool, float | None, float | None]:
    if intrinsic is None or intrinsic <= 0:
        return False, 0.0 if intrinsic == 0 else None, 0.0 if intrinsic == 0 else None
    values = [value for value in (mid, last) if value is not None and value >= 0]
    if not values:
        return False, None, None
    amount = max(intrinsic - value for value in values)
    pct = amount / intrinsic * 100.0
    threshold = max(tolerance_abs, intrinsic * tolerance_pct / 100.0)
    return amount > threshold, max(amount, 0.0), max(pct, 0.0)


def percent_change(current: float | None, base: float | None) -> float | None:
    if current is None or base is None or base == 0:
        return None
    return (current - base) / base * 100.0


def premium_compression_pct(initial_mid: float | None, min_mid: float | None) -> float | None:
    if initial_mid is None or min_mid is None or initial_mid <= 0:
        return None
    return max(0.0, (initial_mid - min_mid) / initial_mid * 100.0)


def rebound_from_low_pct(current_mid: float | None, min_mid: float | None) -> float | None:
    if current_mid is None or min_mid is None or min_mid <= 0:
        return None
    return max(0.0, (current_mid - min_mid) / min_mid * 100.0)


def conservative_ask_to_bid_return(earlier_ask: float | None, future_bid: float | None) -> float | None:
    if earlier_ask is None or future_bid is None or earlier_ask <= 0:
        return None
    return future_bid / earlier_ask - 1.0
