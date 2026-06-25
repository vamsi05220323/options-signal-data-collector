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
    return max(ask - bid, 0.0)


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
