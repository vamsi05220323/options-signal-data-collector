from __future__ import annotations

import math
from collections import defaultdict
from datetime import datetime
from zoneinfo import ZoneInfo

from src.models import ContractRole, OptionContract, OptionQuote, StockQuote
from src.providers.base import BaseDataProvider


class MockProvider(BaseDataProvider):
    name = "mock"

    def __init__(self, timezone: str = "America/Chicago") -> None:
        self.timezone = timezone
        self._stock_steps: dict[str, int] = defaultdict(int)
        self._option_steps: dict[str, int] = defaultdict(int)
        self._base_stocks: dict[str, float] = {}

    def _now(self) -> datetime:
        return datetime.now(ZoneInfo(self.timezone))

    def get_stock_quote(self, symbol: str, fallback_price: float | None = None) -> StockQuote:
        symbol = symbol.upper().lstrip("$")
        if symbol not in self._base_stocks:
            self._base_stocks[symbol] = fallback_price or 35.0
        idx = self._stock_steps[symbol]
        self._stock_steps[symbol] += 1
        path = [1.000, 1.013, 1.027, 1.041, 1.058, 1.044, 1.022, 1.006, 0.992, 0.984, 0.978]
        multiplier = path[min(idx, len(path) - 1)]
        last = round(self._base_stocks[symbol] * multiplier, 2)
        now = self._now()
        return StockQuote(
            timestamp_local=now,
            symbol=symbol,
            bid=round(last - 0.02, 2),
            ask=round(last + 0.02, 2),
            last=last,
            volume=100_000 + idx * 12_000,
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
        reference = stock_price or self._base_stocks.get(symbol.upper(), 35.0)
        step = _default_step(reference)
        low = max(step, math.floor((reference - step * 8) / step) * step)
        high = math.ceil((reference + step * 8) / step) * step
        strikes: list[float] = []
        current = low
        while current <= high + 0.0001:
            strikes.append(round(current, 4))
            current += step
        return strikes

    def get_option_quote(self, contract: OptionContract, stock_last: float | None = None) -> OptionQuote:
        key = contract.storage_symbol
        idx = self._option_steps[key]
        self._option_steps[key] += 1
        if contract.role is ContractRole.SIGNAL_CONTRACT:
            path = [0.42, 0.54, 0.63, 0.59, 0.47, 0.36, 0.31, 0.29, 0.33, 0.30]
        elif contract.role is ContractRole.LOTTO_OBSERVATION_ONLY:
            path = [0.23, 0.17, 0.11, 0.08, 0.12, 0.22, 0.41, 0.33, 0.26, 0.20]
        else:
            path = [1.65, 1.30, 1.02, 0.78, 0.62, 0.82, 1.18, 1.74, 2.24, 2.02, 1.86]
        base_mid = path[min(idx, len(path) - 1)]
        moneyness_pad = 0.0
        if stock_last is not None:
            moneyness_pad = min(abs(contract.strike - stock_last) * 0.012, 0.35)
        mid = round(max(0.03, base_mid + moneyness_pad), 2)
        spread = max(0.04, min(mid * 0.12, 0.28))
        bid = round(max(0.01, mid - spread / 2), 2)
        ask = round(max(bid + 0.01, mid + spread / 2), 2)
        now = self._now()
        return OptionQuote(
            timestamp_local=now,
            option_symbol=contract.storage_symbol,
            bid=bid,
            ask=ask,
            mid=round((bid + ask) / 2, 2),
            last=mid,
            volume=120 + idx * 21,
            open_interest=700 + idx * 3,
            implied_volatility=round(0.55 + idx * 0.01, 4),
            delta=_mock_delta(contract, stock_last),
            gamma=0.05,
            theta=-0.03,
            vega=0.08,
            bid_size=5 + idx,
            ask_size=7 + idx,
            quote_timestamp=now,
            quote_age_seconds=0,
            provider=self.name,
        )


def _default_step(reference: float) -> float:
    if reference < 10:
        return 1.0
    if reference < 30:
        return 2.5
    return 1.0


def _mock_delta(contract: OptionContract, stock_last: float | None) -> float:
    if stock_last is None:
        return 0.5
    distance = contract.strike - stock_last
    if contract.option_type.value == "PUT":
        return round(max(-0.95, min(-0.05, -0.45 - distance * 0.03)), 3)
    return round(max(0.05, min(0.95, 0.45 - distance * 0.03)), 3)
