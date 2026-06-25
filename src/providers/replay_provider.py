from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.models import OptionContract, OptionQuote, StockQuote
from src.providers.base import BaseDataProvider, ProviderError


class ReplayProvider(BaseDataProvider):
    name = "replay"

    def __init__(self, run_folder: Path) -> None:
        self.run_folder = run_folder
        self.stock_ticks = self._load("stock_ticks.csv")
        self.option_ticks = self._load("option_ticks.csv")

    def get_stock_quote(self, symbol: str, fallback_price: float | None = None) -> StockQuote:
        rows = self.stock_ticks[self.stock_ticks["symbol"].str.upper() == symbol.upper()]
        if rows.empty:
            raise ProviderError(f"No replay stock rows for {symbol}")
        row = rows.iloc[0]
        self.stock_ticks = self.stock_ticks.drop(index=row.name)
        return StockQuote(
            timestamp_local=pd.to_datetime(row["timestamp_local"]).to_pydatetime(),
            symbol=str(row["symbol"]),
            bid=_float_or_none(row.get("stock_bid")),
            ask=_float_or_none(row.get("stock_ask")),
            last=_float_or_none(row.get("stock_last")),
            volume=_int_or_none(row.get("stock_volume")),
            provider=self.name,
        )

    def get_option_chain(
        self,
        symbol: str,
        expiry: str,
        option_type: str,
        stock_price: float | None = None,
    ) -> list[float]:
        rows = self.option_ticks[
            (self.option_ticks["underlying_symbol"].str.upper() == symbol.upper())
            & (self.option_ticks["expiry"] == expiry)
            & (self.option_ticks["option_type"].str.upper() == option_type.upper())
        ]
        return sorted(set(float(value) for value in rows["strike"].dropna().tolist()))

    def get_option_quote(self, contract: OptionContract, stock_last: float | None = None) -> OptionQuote:
        rows = self.option_ticks[self.option_ticks["option_symbol"] == contract.storage_symbol]
        if rows.empty:
            rows = self.option_ticks[
                (self.option_ticks["underlying_symbol"].str.upper() == contract.underlying_symbol.upper())
                & (self.option_ticks["expiry"] == contract.expiry.isoformat())
                & (self.option_ticks["option_type"].str.upper() == contract.option_type.value)
                & (self.option_ticks["strike"].astype(float).round(4) == round(contract.strike, 4))
            ]
        if rows.empty:
            raise ProviderError(f"No replay option rows for {contract.display}")
        row = rows.iloc[0]
        self.option_ticks = self.option_ticks.drop(index=row.name)
        return OptionQuote(
            timestamp_local=pd.to_datetime(row["timestamp_local"]).to_pydatetime(),
            option_symbol=str(row["option_symbol"]),
            bid=_float_or_none(row.get("bid")),
            ask=_float_or_none(row.get("ask")),
            mid=_float_or_none(row.get("mid")),
            last=_float_or_none(row.get("last")),
            volume=_int_or_none(row.get("volume")),
            open_interest=_int_or_none(row.get("open_interest")),
            implied_volatility=_float_or_none(row.get("implied_volatility")),
            delta=_float_or_none(row.get("delta")),
            gamma=_float_or_none(row.get("gamma")),
            theta=_float_or_none(row.get("theta")),
            vega=_float_or_none(row.get("vega")),
            bid_size=_int_or_none(row.get("bid_size")),
            ask_size=_int_or_none(row.get("ask_size")),
            quote_age_seconds=_float_or_none(row.get("quote_age_seconds")),
            provider=self.name,
        )

    def _load(self, filename: str) -> pd.DataFrame:
        path = self.run_folder / filename
        if not path.exists():
            raise ProviderError(f"Replay file missing: {path}")
        return pd.read_csv(path)


def _float_or_none(value) -> float | None:
    if value is None or pd.isna(value) or value == "":
        return None
    return float(value)


def _int_or_none(value) -> int | None:
    number = _float_or_none(value)
    return None if number is None else int(number)
