from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime
from enum import Enum
from typing import Any


class OptionType(str, Enum):
    CALL = "CALL"
    PUT = "PUT"

    @property
    def short(self) -> str:
        return "C" if self is OptionType.CALL else "P"

    @classmethod
    def from_text(cls, value: str | "OptionType") -> "OptionType":
        if isinstance(value, OptionType):
            return value
        cleaned = str(value).strip().upper()
        if cleaned in {"C", "CALL"}:
            return cls.CALL
        if cleaned in {"P", "PUT"}:
            return cls.PUT
        raise ValueError(f"Unknown option type: {value}")

    def opposite(self) -> "OptionType":
        return OptionType.PUT if self is OptionType.CALL else OptionType.CALL


class ContractRole(str, Enum):
    SIGNAL_CONTRACT = "SIGNAL_CONTRACT"
    EXACT_OPPOSITE = "EXACT_OPPOSITE"
    ITM_OPPOSITE = "ITM_OPPOSITE"
    ATM_OPPOSITE = "ATM_OPPOSITE"
    OTM_OPPOSITE = "OTM_OPPOSITE"
    LOTTO_OBSERVATION_ONLY = "LOTTO_OBSERVATION_ONLY"


class SignalStatus(str, Enum):
    COLLECTING = "COLLECTING"
    WATCH = "WATCH"
    INVALID_QUOTE = "INVALID_QUOTE"
    SKIP_CANDIDATE = "SKIP_CANDIDATE"


@dataclass(slots=True)
class TradeSignal:
    signal_id: str
    timestamp_local: datetime
    symbol: str
    direction: OptionType
    signal_strike: float
    expiry: date
    signal_premium: float | None
    stock_price_at_signal: float
    provider: str = "mock"
    status: SignalStatus = SignalStatus.COLLECTING
    raw_text: str | None = None

    def __post_init__(self) -> None:
        self.symbol = normalize_symbol(self.symbol)
        self.direction = OptionType.from_text(self.direction)
        self.signal_strike = float(self.signal_strike)
        self.stock_price_at_signal = float(self.stock_price_at_signal)
        if self.signal_premium is not None:
            self.signal_premium = float(self.signal_premium)
        if isinstance(self.status, str):
            self.status = SignalStatus(self.status)

    @property
    def opposite_direction(self) -> OptionType:
        return self.direction.opposite()

    @property
    def strike(self) -> float:
        return self.signal_strike

    @property
    def signal_price(self) -> float | None:
        return self.signal_premium

    @property
    def stock_price(self) -> float:
        return self.stock_price_at_signal

    @property
    def opposite_type(self) -> OptionType:
        return self.opposite_direction

    @property
    def display(self) -> str:
        premium = "" if self.signal_premium is None else f" @ {self.signal_premium:.2f}"
        return f"{self.symbol} {format_strike(self.signal_strike)} {self.direction.value} {self.expiry.isoformat()}{premium}"


@dataclass(slots=True)
class OptionContract:
    underlying_symbol: str
    expiry: date
    strike: float
    option_type: OptionType
    role: ContractRole
    option_symbol: str | None = None
    rank: int = 100
    exchange: str | None = None

    def __post_init__(self) -> None:
        self.underlying_symbol = normalize_symbol(self.underlying_symbol)
        self.option_type = OptionType.from_text(self.option_type)
        if isinstance(self.role, str):
            self.role = ContractRole(self.role)
        self.strike = float(self.strike)
        if self.option_symbol:
            self.option_symbol = self.option_symbol.strip().upper()

    @property
    def symbol(self) -> str:
        return self.underlying_symbol

    @property
    def display(self) -> str:
        return f"{self.underlying_symbol} {format_strike(self.strike)}{self.option_type.short} {self.expiry.isoformat()}"

    @property
    def storage_symbol(self) -> str:
        if self.option_symbol:
            return self.option_symbol
        yymmdd = self.expiry.strftime("%y%m%d")
        strike_key = int(round(self.strike * 1000))
        return f"{self.underlying_symbol}{yymmdd}{self.option_type.short}{strike_key:08d}"


@dataclass(slots=True)
class StockQuote:
    timestamp_local: datetime
    symbol: str
    bid: float | None
    ask: float | None
    last: float | None
    volume: int | None
    provider: str
    quote_timestamp: datetime | None = None

    def __post_init__(self) -> None:
        self.symbol = normalize_symbol(self.symbol)


@dataclass(slots=True)
class OptionQuote:
    timestamp_local: datetime
    option_symbol: str
    bid: float | None
    ask: float | None
    mid: float | None
    last: float | None
    volume: int | None
    open_interest: int | None
    implied_volatility: float | None
    provider: str
    delta: float | None = None
    gamma: float | None = None
    theta: float | None = None
    vega: float | None = None
    bid_size: int | None = None
    ask_size: int | None = None
    quote_timestamp: datetime | None = None
    quote_age_seconds: float | None = None


@dataclass(slots=True)
class StockTick:
    timestamp_local: datetime
    signal_id: str
    symbol: str
    stock_bid: float | None
    stock_ask: float | None
    stock_last: float | None
    stock_mid: float | None
    stock_volume: int | None
    seconds_since_signal: float
    stock_price_at_signal: float
    post_signal_high: float
    post_signal_low: float
    stock_change_from_signal_pct: float | None
    pump_from_signal_pct: float | None
    pullback_from_high_pct: float | None


@dataclass(slots=True)
class OptionTick:
    timestamp_local: datetime
    signal_id: str
    underlying_symbol: str
    option_symbol: str
    contract_role: ContractRole
    expiry: date
    strike: float
    option_type: OptionType
    bid: float | None
    ask: float | None
    mid: float | None
    last: float | None
    volume: int | None
    open_interest: int | None
    implied_volatility: float | None
    delta: float | None
    gamma: float | None
    theta: float | None
    vega: float | None
    bid_size: int | None
    ask_size: int | None
    spread_abs: float | None
    spread_pct: float | None
    intrinsic_value: float | None
    extrinsic_value: float | None
    quote_timestamp: datetime | None
    quote_age_seconds: float | None
    quote_is_valid: bool
    reason_invalid: str
    seconds_since_signal: float
    option_initial_mid: float | None
    option_min_mid_since_signal: float | None
    option_max_mid_since_signal: float | None
    option_min_ask_since_signal: float | None
    option_max_bid_since_signal: float | None
    compression_from_initial_pct: float | None
    rebound_from_low_pct: float | None


@dataclass(slots=True)
class NewsArticle:
    timestamp_collected: datetime
    signal_id: str
    symbol: str
    provider: str
    article_published_at: datetime | None
    article_age_minutes_at_signal: float | None
    source: str
    headline: str
    summary: str
    url: str
    related_tickers: str
    sentiment_label: str
    sentiment_score: float | None
    relevance_score: float | None
    catalyst_type: str
    is_within_24h: bool
    is_within_7d: bool


@dataclass(slots=True)
class NewsSummary:
    signal_id: str
    symbol: str
    signal_timestamp_local: datetime
    news_provider: str
    news_count_24h: int
    news_count_7d: int
    latest_news_age_minutes: float | None
    positive_news_count_24h: int
    negative_news_count_24h: int
    neutral_news_count_24h: int
    avg_sentiment_24h: float | None
    avg_relevance_24h: float | None
    top_sources_24h: str
    top_headlines_24h: str
    catalyst_detected: bool
    catalyst_type: str
    news_bias: str
    news_score: float
    news_skip_warning: str
    news_notes: str


def normalize_symbol(value: str) -> str:
    return value.strip().upper().lstrip("$")


def format_strike(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else f"{value:g}"


def serialize_row(obj: Any) -> dict[str, Any]:
    row = asdict(obj) if hasattr(obj, "__dataclass_fields__") else dict(obj)
    return {key: serialize_value(value) for key, value in row.items()}


def serialize_value(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, bool):
        return "true" if value else "false"
    return value
