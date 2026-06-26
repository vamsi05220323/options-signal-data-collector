from __future__ import annotations

import csv
import re
from datetime import date, datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

from src.models import OptionType, TradeSignal, normalize_symbol


SEPARATE_PATTERN = re.compile(
    r"^\s*\$?(?P<symbol>[A-Za-z]{1,8})\s+"
    r"(?P<strike>\d+(?:\.\d+)?)\s+"
    r"(?:(?:BUY|BOT|BTO|SELL|STO)\s+)?"
    r"(?P<option_type>CALL|PUT|C|P)\s+"
    r"(?P<expiry>\d{1,2}/\d{1,2}(?:/\d{2,4})?|\d{4}-\d{2}-\d{2})"
    r"(?:\s+@?\s*(?P<price>\d+(?:\.\d+)?))?\s*$",
    re.IGNORECASE,
)

COMPACT_PATTERN = re.compile(
    r"^\s*\$?(?P<symbol>[A-Za-z]{1,8})\s+"
    r"(?P<strike>\d+(?:\.\d+)?)(?P<option_type>[CP])\s+"
    r"(?P<expiry>\d{1,2}/\d{1,2}(?:/\d{2,4})?|\d{4}-\d{2}-\d{2})"
    r"(?:\s+@?\s*(?P<price>\d+(?:\.\d+)?))?\s*$",
    re.IGNORECASE,
)


def parse_expiry(value: str, today: date | None = None) -> date:
    cleaned = value.strip()
    if "-" in cleaned:
        year, month, day = (int(part) for part in cleaned.split("-", 2))
        return date(year, month, day)
    parts = [int(part) for part in cleaned.split("/")]
    if len(parts) not in {2, 3}:
        raise ValueError(f"Unsupported expiry format: {value}")
    month, day = parts[0], parts[1]
    if len(parts) == 3:
        year = parts[2] + 2000 if parts[2] < 100 else parts[2]
        return date(year, month, day)
    today = today or date.today()
    inferred = date(today.year, month, day)
    if inferred < today:
        inferred = date(today.year + 1, month, day)
    return inferred


def parse_signal_text(
    text: str,
    *,
    stock_price: float,
    timestamp_local: datetime,
    provider: str = "mock",
    today: date | None = None,
) -> TradeSignal:
    cleaned = text.strip().replace(",", " ")
    match = SEPARATE_PATTERN.match(cleaned) or COMPACT_PATTERN.match(cleaned)
    if not match:
        raise ValueError(f"Could not parse signal text: {text!r}")
    groups = match.groupdict()
    signal_id = make_signal_id(groups["symbol"], timestamp_local, groups["option_type"], float(groups["strike"]))
    return TradeSignal(
        signal_id=signal_id,
        timestamp_local=timestamp_local,
        symbol=groups["symbol"],
        direction=OptionType.from_text(groups["option_type"]),
        signal_strike=float(groups["strike"]),
        expiry=parse_expiry(groups["expiry"], today=today),
        signal_premium=float(groups["price"]) if groups.get("price") is not None else None,
        stock_price_at_signal=stock_price,
        provider=provider,
        raw_text=text,
    )


def read_signals_csv(path: Path, *, timezone: str, provider: str) -> list[TradeSignal]:
    tz = ZoneInfo(timezone)
    signals: list[TradeSignal] = []
    seen: dict[str, int] = {}
    with path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        required = {
            "timestamp_local",
            "symbol",
            "direction",
            "signal_strike",
            "expiry",
            "signal_premium",
            "stock_price_at_signal",
        }
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Signals CSV missing columns: {', '.join(sorted(missing))}")
        for row in reader:
            timestamp = parse_local_datetime(row["timestamp_local"], tz)
            symbol = normalize_symbol(row["symbol"])
            direction = OptionType.from_text(row["direction"])
            base_id = make_signal_id(symbol, timestamp, direction.value, float(row["signal_strike"]))
            count = seen.get(base_id, 0)
            seen[base_id] = count + 1
            signal_id = base_id if count == 0 else f"{base_id}_{count + 1}"
            signals.append(
                TradeSignal(
                    signal_id=signal_id,
                    timestamp_local=timestamp,
                    symbol=symbol,
                    direction=direction,
                    signal_strike=float(row["signal_strike"]),
                    expiry=parse_expiry(row["expiry"]),
                    signal_premium=_optional_float(row["signal_premium"]),
                    stock_price_at_signal=float(row["stock_price_at_signal"]),
                    provider=provider,
                    underlying_exchange=_optional_text(row.get("underlying_exchange")) or "SMART",
                    primary_exchange=_optional_text(row.get("primary_exchange")),
                    currency=_optional_text(row.get("currency")) or "USD",
                    ibkr_con_id=_optional_int(row.get("ibkr_con_id")),
                    ibkr_local_symbol=_optional_text(row.get("ibkr_local_symbol")),
                    ibkr_trading_class=_optional_text(row.get("ibkr_trading_class")),
                )
            )
    return signals


def parse_local_datetime(value: str, tz: ZoneInfo) -> datetime:
    cleaned = value.strip()
    timestamp = datetime.fromisoformat(cleaned)
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=tz)
    return timestamp.astimezone(tz)


def parse_runtime_datetime(value: str | None, tz: ZoneInfo, *, now: datetime | None = None) -> datetime | None:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    current = now or datetime.now(tz)
    lowered = cleaned.lower()
    if lowered in {"now", "current", "current-time", "current_time"}:
        return current.astimezone(tz)
    if lowered in {"market-open", "market_open", "open"}:
        market_open, _market_close = _market_hours_for_timezone(tz)
        return datetime.combine(current.date(), market_open, tzinfo=tz)
    if lowered in {"market-close", "market_close", "close"}:
        _market_open, market_close = _market_hours_for_timezone(tz)
        return datetime.combine(current.date(), market_close, tzinfo=tz)
    if re.fullmatch(r"\d{1,2}:\d{2}(?::\d{2})?", cleaned):
        parsed_time = time.fromisoformat(cleaned if cleaned.count(":") == 2 else f"{cleaned}:00")
        return datetime.combine(current.date(), parsed_time, tzinfo=tz)
    return parse_local_datetime(cleaned, tz)


def _market_hours_for_timezone(tz: ZoneInfo) -> tuple[time, time]:
    if getattr(tz, "key", "") == "America/New_York":
        return time(9, 30), time(16, 0)
    return time(8, 30), time(15, 0)


def make_signal_id(symbol: str, timestamp: datetime, direction: str, strike: float) -> str:
    strike_key = str(strike).replace(".", "p")
    return f"{normalize_symbol(symbol)}_{timestamp.strftime('%Y%m%d_%H%M%S')}_{direction.upper()}_{strike_key}"


def _optional_float(value: str | None) -> float | None:
    if value is None or str(value).strip() == "":
        return None
    return float(value)


def _optional_int(value: str | None) -> int | None:
    if value is None or str(value).strip() == "":
        return None
    return int(float(value))


def _optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None
