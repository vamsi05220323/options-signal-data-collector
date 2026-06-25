from __future__ import annotations

import csv
import re
from datetime import date, datetime
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
                )
            )
    return signals


def parse_local_datetime(value: str, tz: ZoneInfo) -> datetime:
    cleaned = value.strip()
    timestamp = datetime.fromisoformat(cleaned)
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=tz)
    return timestamp.astimezone(tz)


def make_signal_id(symbol: str, timestamp: datetime, direction: str, strike: float) -> str:
    strike_key = str(strike).replace(".", "p")
    return f"{normalize_symbol(symbol)}_{timestamp.strftime('%Y%m%d_%H%M%S')}_{direction.upper()}_{strike_key}"


def _optional_float(value: str | None) -> float | None:
    if value is None or str(value).strip() == "":
        return None
    return float(value)
