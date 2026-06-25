from __future__ import annotations

from src.models import OptionContract, OptionQuote, StockQuote
from src.providers.base import BaseDataProvider, ProviderError


class WebullProvider(BaseDataProvider):
    """Official Webull OpenAPI placeholder; no unofficial scraping."""

    name = "webull"

    def __init__(self, app_key: str = "", app_secret: str = "", token: str = "") -> None:
        self.app_key = app_key
        self.app_secret = app_secret
        self.token = token

    def connect(self) -> None:
        if not self.app_key or not self.app_secret:
            raise ProviderError("Webull OpenAPI keys are not configured. Webull provider unavailable.")
        raise ProviderError("Webull OpenAPI support is not implemented until official option quote access is verified.")

    def get_stock_quote(self, symbol: str, fallback_price: float | None = None) -> StockQuote:
        self.connect()
        raise ProviderError("Webull provider unavailable.")

    def get_option_chain(
        self,
        symbol: str,
        expiry: str,
        option_type: str,
        stock_price: float | None = None,
    ) -> list[float]:
        self.connect()
        raise ProviderError("Webull provider unavailable.")

    def get_option_quote(self, contract: OptionContract, stock_last: float | None = None) -> OptionQuote:
        self.connect()
        raise ProviderError("Webull provider unavailable.")
