from __future__ import annotations

import math
from datetime import datetime
from zoneinfo import ZoneInfo

from src.models import OptionContract, OptionQuote, StockQuote
from src.providers.base import BaseDataProvider, ProviderError


class IBKRProvider(BaseDataProvider):
    name = "ibkr"

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 7497,
        client_id: int = 12,
        timezone: str = "America/Chicago",
    ) -> None:
        self.host = host
        self.port = port
        self.client_id = client_id
        self.timezone = timezone
        self.ib = None

    def connect(self) -> None:
        if self.ib is not None and self.ib.isConnected():
            return
        try:
            from ib_insync import IB
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise ProviderError("ib_insync is not installed. Run: pip install ib_insync") from exc
        self.ib = IB()
        try:
            self.ib.connect(self.host, self.port, clientId=self.client_id, timeout=5, readonly=True)
        except Exception as exc:  # pragma: no cover - requires TWS/Gateway
            raise ProviderError(f"Could not connect to IBKR at {self.host}:{self.port}: {exc}") from exc

    def close(self) -> None:
        if self.ib is not None and self.ib.isConnected():
            self.ib.disconnect()

    def get_stock_quote(self, symbol: str, fallback_price: float | None = None) -> StockQuote:
        self.connect()
        from ib_insync import Stock

        contract = Stock(symbol.upper(), "SMART", "USD")
        self.ib.qualifyContracts(contract)
        ticker = self.ib.reqMktData(contract, "", False, False)
        self.ib.sleep(1.0)
        bid = _clean_number(ticker.bid)
        ask = _clean_number(ticker.ask)
        last = _clean_number(ticker.last) or _clean_number(ticker.close) or fallback_price
        if last is None:
            raise ProviderError(f"IBKR stock quote has no usable price for {symbol}")
        now = self._now()
        return StockQuote(
            timestamp_local=now,
            symbol=symbol,
            bid=bid,
            ask=ask,
            last=last,
            volume=_clean_int(ticker.volume),
            provider=self.name,
            quote_timestamp=now,
        )

    def get_option_chain(
        self,
        symbol: str,
        expiry: str,
        option_type: str,
        stock_price: float | None = None,
    ) -> list[float]:
        self.connect()
        from ib_insync import Stock

        stock = Stock(symbol.upper(), "SMART", "USD")
        qualified = self.ib.qualifyContracts(stock)
        if not qualified:
            raise ProviderError(f"IBKR could not qualify stock contract for {symbol}")
        params = self.ib.reqSecDefOptParams(symbol.upper(), "", "STK", qualified[0].conId)
        expiry_key = expiry.replace("-", "")
        strikes: set[float] = set()
        for chain in params:
            if expiry_key in set(chain.expirations):
                strikes.update(float(strike) for strike in chain.strikes if strike and strike > 0)
        if not strikes:
            raise ProviderError(f"IBKR returned no option strikes for {symbol} {expiry}")
        return sorted(strikes)

    def get_option_quote(self, contract: OptionContract, stock_last: float | None = None) -> OptionQuote:
        self.connect()
        from ib_insync import Option

        right = "C" if contract.option_type.value == "CALL" else "P"
        ib_contract = Option(
            contract.underlying_symbol,
            contract.expiry.strftime("%Y%m%d"),
            contract.strike,
            right,
            contract.exchange or "SMART",
            currency="USD",
        )
        qualified = self.ib.qualifyContracts(ib_contract)
        if not qualified:
            raise ProviderError(f"IBKR could not qualify option {contract.display}")
        ticker = self.ib.reqMktData(qualified[0], "100,101,106", False, False)
        self.ib.sleep(1.0)
        bid = _clean_number(ticker.bid)
        ask = _clean_number(ticker.ask)
        last = _clean_number(ticker.last)
        mid = (bid + ask) / 2 if bid is not None and ask is not None else None
        greeks = ticker.modelGreeks or ticker.bidGreeks or ticker.askGreeks
        now = self._now()
        return OptionQuote(
            timestamp_local=now,
            option_symbol=contract.storage_symbol,
            bid=bid,
            ask=ask,
            mid=mid,
            last=last,
            volume=_clean_int(ticker.volume),
            open_interest=_clean_int(getattr(ticker, "putOpenInterest", None) or getattr(ticker, "callOpenInterest", None)),
            implied_volatility=_clean_number(getattr(greeks, "impliedVol", None)) if greeks else None,
            delta=_clean_number(getattr(greeks, "delta", None)) if greeks else None,
            gamma=_clean_number(getattr(greeks, "gamma", None)) if greeks else None,
            theta=_clean_number(getattr(greeks, "theta", None)) if greeks else None,
            vega=_clean_number(getattr(greeks, "vega", None)) if greeks else None,
            bid_size=_clean_int(ticker.bidSize),
            ask_size=_clean_int(ticker.askSize),
            quote_timestamp=now,
            quote_age_seconds=0,
            provider=self.name,
        )

    def _now(self) -> datetime:
        return datetime.now(ZoneInfo(self.timezone))


def _clean_number(value) -> float | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return number


def _clean_int(value) -> int | None:
    number = _clean_number(value)
    return None if number is None else int(number)
