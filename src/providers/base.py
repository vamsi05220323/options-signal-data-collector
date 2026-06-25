from __future__ import annotations

from abc import ABC, abstractmethod

from src.models import OptionContract, OptionQuote, StockQuote


class ProviderError(RuntimeError):
    """Raised when a market data provider cannot return requested data."""


class BaseDataProvider(ABC):
    name: str

    def connect(self) -> None:
        return None

    def close(self) -> None:
        return None

    @abstractmethod
    def get_stock_quote(self, symbol: str, fallback_price: float | None = None) -> StockQuote:
        raise NotImplementedError

    @abstractmethod
    def get_option_chain(
        self,
        symbol: str,
        expiry: str,
        option_type: str,
        stock_price: float | None = None,
    ) -> list[float]:
        raise NotImplementedError

    @abstractmethod
    def get_option_quote(self, contract: OptionContract, stock_last: float | None = None) -> OptionQuote:
        raise NotImplementedError
