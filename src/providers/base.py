from __future__ import annotations

from abc import ABC, abstractmethod

from src.models import OptionContract, OptionQuote, StockQuote, TradeSignal


class ProviderError(RuntimeError):
    """Raised when a market data provider cannot return requested data."""

    def __init__(self, message: str, *, code: str | int | None = None, market_data_type: str = "unknown") -> None:
        super().__init__(message)
        self.code = "" if code is None else str(code)
        self.market_data_type = market_data_type


class BaseDataProvider(ABC):
    name: str

    def connect(self) -> None:
        return None

    def close(self) -> None:
        return None

    def drain_diagnostics(self) -> list[dict[str, str]]:
        return []

    def resolve_signal(self, signal: TradeSignal) -> TradeSignal:
        return signal

    @abstractmethod
    def get_stock_quote(self, symbol: str, fallback_price: float | None = None) -> StockQuote:
        raise NotImplementedError

    def get_stock_quote_for_signal(self, signal: TradeSignal, fallback_price: float | None = None) -> StockQuote:
        return self.get_stock_quote(signal.symbol, fallback_price)

    @abstractmethod
    def get_option_chain(
        self,
        symbol: str,
        expiry: str,
        option_type: str,
        stock_price: float | None = None,
    ) -> list[float]:
        raise NotImplementedError

    def get_option_chain_for_signal(
        self,
        signal: TradeSignal,
        option_type: str,
        stock_price: float | None = None,
    ) -> list[float]:
        return self.get_option_chain(signal.symbol, signal.expiry.isoformat(), option_type, stock_price)

    @abstractmethod
    def get_option_quote(self, contract: OptionContract, stock_last: float | None = None) -> OptionQuote:
        raise NotImplementedError
