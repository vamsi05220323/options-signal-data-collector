from __future__ import annotations

import math
from dataclasses import replace
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from src.models import OptionContract, OptionQuote, StockQuote, TradeSignal
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
        self._stock_contracts: dict[str, object] = {}
        self._option_contracts: dict[str, object] = {}
        self._diagnostics: list[dict[str, str]] = []
        self._last_market_data_type = "unknown"

    def connect(self) -> None:
        if self.ib is not None and self.ib.isConnected():
            return
        try:
            from ib_insync import IB
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise ProviderError("ib_insync is not installed. Run: pip install ib_insync") from exc
        self.ib = IB()
        self.ib.errorEvent += self._on_error
        try:
            self.ib.connect(self.host, self.port, clientId=self.client_id, timeout=5, readonly=True)
        except Exception as exc:  # pragma: no cover - requires TWS/Gateway
            raise ProviderError(f"Could not connect to IBKR at {self.host}:{self.port}: {exc}") from exc

    def close(self) -> None:
        if self.ib is not None and self.ib.isConnected():
            self.ib.disconnect()

    def drain_diagnostics(self) -> list[dict[str, str]]:
        diagnostics = self._diagnostics[:]
        self._diagnostics.clear()
        return diagnostics

    def resolve_signal(self, signal: TradeSignal) -> TradeSignal:
        self.connect()
        contract, match_count = self._resolve_stock_contract(signal)
        message = (
            f"Resolved {signal.symbol} to conId={getattr(contract, 'conId', None)} "
            f"primaryExchange={getattr(contract, 'primaryExchange', None) or 'UNKNOWN'} "
            f"currency={getattr(contract, 'currency', None) or signal.currency}"
        )
        if match_count > 1:
            message += f"; selected best match from {match_count} IBKR contract matches"
        resolved = replace(
            signal,
            symbol=(getattr(contract, "symbol", None) or signal.symbol).upper(),
            underlying_exchange=getattr(contract, "exchange", None) or signal.underlying_exchange,
            primary_exchange=getattr(contract, "primaryExchange", None) or signal.primary_exchange,
            currency=getattr(contract, "currency", None) or signal.currency,
            ibkr_con_id=getattr(contract, "conId", None) or signal.ibkr_con_id,
            ibkr_local_symbol=getattr(contract, "localSymbol", None) or signal.ibkr_local_symbol,
            ibkr_trading_class=getattr(contract, "tradingClass", None) or signal.ibkr_trading_class,
            contract_resolution_status="RESOLVED",
            contract_resolution_message=message,
        )
        self._cache_stock_contract(resolved, contract)
        return resolved

    def get_stock_quote(self, symbol: str, fallback_price: float | None = None) -> StockQuote:
        self.connect()
        contract = self._stock_contracts.get(f"symbol:{symbol.upper()}") or self._make_stock_contract(symbol.upper())
        return self._request_stock_quote(contract, symbol.upper(), fallback_price)

    def get_stock_quote_for_signal(self, signal: TradeSignal, fallback_price: float | None = None) -> StockQuote:
        self.connect()
        contract = self._stock_contract_for_signal(signal)
        return self._request_stock_quote(contract, signal.symbol, fallback_price)

    def _request_stock_quote(self, contract, symbol: str, fallback_price: float | None = None) -> StockQuote:
        qualified = self.ib.qualifyContracts(contract)
        if not qualified:
            raise ProviderError(f"IBKR could not qualify stock contract for {symbol}")
        qualified_contract = qualified[0]
        ticker = self.ib.reqMktData(qualified_contract, "", False, False)
        self.ib.sleep(1.0)
        bid = _clean_number(ticker.bid)
        ask = _clean_number(ticker.ask)
        provider_last = _clean_number(ticker.last)
        provider_close = _clean_number(ticker.close)
        fallback_used = False
        if provider_last is not None:
            last = provider_last
            price_source = "PROVIDER_LAST"
        elif provider_close is not None:
            last = provider_close
            price_source = "PROVIDER_CLOSE_FALLBACK"
            fallback_used = True
        else:
            last = fallback_price
            price_source = "SIGNAL_PRICE_FALLBACK"
            fallback_used = last is not None
        if last is None:
            raise ProviderError(f"IBKR stock quote has no usable price for {symbol}")
        now = self._now()
        market_data_type = _market_data_type_name(getattr(ticker, "marketDataType", None))
        self._last_market_data_type = market_data_type
        source_timestamp, quote_age_seconds = _quote_timing(ticker, now)
        quote_is_live = bool(not fallback_used and market_data_type == "live")
        if fallback_used:
            quote_status = "FALLBACK"
        elif market_data_type == "live":
            quote_status = "LIVE"
        elif market_data_type in {"frozen", "delayed", "delayed_frozen"}:
            quote_status = market_data_type.upper()
        else:
            quote_status = "UNKNOWN"
        return StockQuote(
            timestamp_local=now,
            symbol=(getattr(qualified_contract, "symbol", None) or symbol).upper(),
            bid=bid,
            ask=ask,
            last=last,
            volume=_clean_int(ticker.volume),
            provider=self.name,
            quote_timestamp=source_timestamp,
            stock_price_source=price_source,
            stock_quote_status=quote_status,
            fallback_used=fallback_used,
            quote_is_live=quote_is_live,
            market_data_type=market_data_type,
            quote_source_timestamp=source_timestamp,
            quote_age_seconds=quote_age_seconds,
        )

    def get_option_chain(
        self,
        symbol: str,
        expiry: str,
        option_type: str,
        stock_price: float | None = None,
    ) -> list[float]:
        self.connect()
        stock = self._stock_contracts.get(f"symbol:{symbol.upper()}") or self._make_stock_contract(symbol.upper())
        return self._request_option_chain(stock, symbol.upper(), expiry)

    def get_option_chain_for_signal(
        self,
        signal: TradeSignal,
        option_type: str,
        stock_price: float | None = None,
    ) -> list[float]:
        self.connect()
        stock = self._stock_contract_for_signal(signal)
        return self._request_option_chain(stock, signal.symbol, signal.expiry.isoformat())

    def _request_option_chain(self, stock, symbol: str, expiry: str) -> list[float]:
        qualified = self.ib.qualifyContracts(stock)
        if not qualified:
            raise ProviderError(f"IBKR could not qualify stock contract for {symbol}")
        underlying = qualified[0]
        params = self.ib.reqSecDefOptParams(underlying.symbol, "", "STK", underlying.conId)
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
        qualified_contract = self._qualified_option_contract(contract)
        ticker = self.ib.reqMktData(qualified_contract, "100,101,106", False, False)
        self.ib.sleep(1.0)
        bid = _clean_number(ticker.bid)
        ask = _clean_number(ticker.ask)
        last = _clean_number(ticker.last)
        mid = (bid + ask) / 2 if bid is not None and ask is not None else None
        greeks = ticker.modelGreeks or ticker.bidGreeks or ticker.askGreeks
        now = self._now()
        market_data_type = _market_data_type_name(getattr(ticker, "marketDataType", None))
        self._last_market_data_type = market_data_type
        source_timestamp, quote_age_seconds = _quote_timing(ticker, now)
        volume_field = "callVolume" if contract.option_type.value == "CALL" else "putVolume"
        open_interest_field = "callOpenInterest" if contract.option_type.value == "CALL" else "putOpenInterest"
        volume = _clean_int(getattr(ticker, volume_field, None))
        if volume is None:
            volume = _clean_int(ticker.volume)
        return OptionQuote(
            timestamp_local=now,
            option_symbol=contract.storage_symbol,
            bid=bid,
            ask=ask,
            mid=mid,
            last=last,
            volume=volume,
            open_interest=_clean_int(getattr(ticker, open_interest_field, None)),
            implied_volatility=_clean_number(getattr(greeks, "impliedVol", None)) if greeks else None,
            delta=_clean_number(getattr(greeks, "delta", None)) if greeks else None,
            gamma=_clean_number(getattr(greeks, "gamma", None)) if greeks else None,
            theta=_clean_number(getattr(greeks, "theta", None)) if greeks else None,
            vega=_clean_number(getattr(greeks, "vega", None)) if greeks else None,
            bid_size=_clean_int(ticker.bidSize),
            ask_size=_clean_int(ticker.askSize),
            quote_timestamp=source_timestamp,
            quote_age_seconds=quote_age_seconds,
            market_data_type=market_data_type,
            quote_source_timestamp=source_timestamp,
            provider=self.name,
        )

    def _now(self) -> datetime:
        return datetime.now(ZoneInfo(self.timezone))

    def _on_error(self, _req_id, error_code, error_message, contract) -> None:
        option_symbol = getattr(contract, "localSymbol", None) or getattr(contract, "symbol", None) or ""
        self._diagnostics.append(
            {
                "provider_error_code": str(error_code),
                "provider_error_message": str(error_message).replace("\r", " ").replace("\n", " "),
                "market_data_type": self._last_market_data_type,
                "option_symbol": str(option_symbol),
            }
        )

    def _make_stock_contract(self, symbol: str, exchange: str = "SMART", currency: str = "USD"):
        from ib_insync import Stock

        return Stock(symbol.upper(), exchange, currency)

    def _resolve_stock_contract(self, signal: TradeSignal):
        from ib_insync import Contract

        if signal.ibkr_con_id:
            contract = Contract(
                conId=signal.ibkr_con_id,
                exchange=signal.underlying_exchange or "SMART",
                currency=signal.currency or "USD",
            )
            qualified = self.ib.qualifyContracts(contract)
            if not qualified:
                raise ProviderError(f"IBKR could not qualify conId={signal.ibkr_con_id} for {signal.symbol}")
            return qualified[0], 1

        stock = self._make_stock_contract(signal.symbol, signal.underlying_exchange, signal.currency)
        if signal.primary_exchange:
            stock.primaryExchange = signal.primary_exchange
        details = self.ib.reqContractDetails(stock)
        if details:
            selected = _select_stock_detail(details, signal)
            return selected.contract, len(details)
        qualified = self.ib.qualifyContracts(stock)
        if not qualified:
            raise ProviderError(f"IBKR could not resolve stock contract for {signal.symbol}")
        return qualified[0], 1

    def _stock_contract_for_signal(self, signal: TradeSignal):
        cached = self._stock_contracts.get(_stock_cache_key(signal))
        if cached is not None:
            return cached
        contract, _match_count = self._resolve_stock_contract(signal)
        self._cache_stock_contract(signal, contract)
        return contract

    def _cache_stock_contract(self, signal: TradeSignal, contract) -> None:
        self._stock_contracts[_stock_cache_key(signal)] = contract
        self._stock_contracts[f"symbol:{signal.symbol.upper()}"] = contract

    def _qualified_option_contract(self, contract: OptionContract):
        key = _option_cache_key(contract)
        cached = self._option_contracts.get(key)
        if cached is not None:
            return cached

        from ib_insync import Contract, Option

        right = "C" if contract.option_type.value == "CALL" else "P"
        if contract.con_id:
            ib_contract = Contract(conId=contract.con_id, exchange=contract.exchange or "SMART", currency=contract.currency)
        else:
            ib_contract = Option(
                contract.underlying_symbol,
                contract.expiry.strftime("%Y%m%d"),
                contract.strike,
                right,
                contract.exchange or "SMART",
                currency=contract.currency,
            )
            if contract.trading_class:
                ib_contract.tradingClass = contract.trading_class
        qualified = self.ib.qualifyContracts(ib_contract)
        if not qualified:
            raise ProviderError(f"IBKR could not qualify option {contract.display}")
        qualified_contract = qualified[0]
        contract.con_id = getattr(qualified_contract, "conId", None) or contract.con_id
        contract.local_symbol = getattr(qualified_contract, "localSymbol", None) or contract.local_symbol
        contract.trading_class = getattr(qualified_contract, "tradingClass", None) or contract.trading_class
        contract.exchange = getattr(qualified_contract, "exchange", None) or contract.exchange
        contract.primary_exchange = getattr(qualified_contract, "primaryExchange", None) or contract.primary_exchange
        contract.currency = getattr(qualified_contract, "currency", None) or contract.currency
        self._option_contracts[key] = qualified_contract
        self._option_contracts[_option_cache_key(contract)] = qualified_contract
        return qualified_contract


def _select_stock_detail(details, signal: TradeSignal):
    preferred_primary = [
        signal.primary_exchange,
        "NASDAQ",
        "NYSE",
        "ARCA",
        "AMEX",
        "BATS",
        "IEX",
    ]
    preferred_primary = [item for item in preferred_primary if item]

    def score(detail) -> tuple[int, int, int, int]:
        contract = detail.contract
        symbol_score = 1 if getattr(contract, "symbol", "").upper() == signal.symbol else 0
        sec_type_score = 1 if getattr(contract, "secType", "") == "STK" else 0
        currency_score = 1 if getattr(contract, "currency", "").upper() == signal.currency else 0
        primary = (getattr(contract, "primaryExchange", "") or "").upper()
        try:
            primary_score = len(preferred_primary) - preferred_primary.index(primary)
        except ValueError:
            primary_score = 0
        return symbol_score, sec_type_score, currency_score, primary_score

    return max(details, key=score)


def _stock_cache_key(signal: TradeSignal) -> str:
    if signal.ibkr_con_id:
        return f"conid:{signal.ibkr_con_id}"
    parts = [
        signal.symbol,
        signal.underlying_exchange or "SMART",
        signal.primary_exchange or "",
        signal.currency or "USD",
    ]
    return "signal:" + "|".join(part.upper() for part in parts)


def _option_cache_key(contract: OptionContract) -> str:
    if contract.con_id:
        return f"conid:{contract.con_id}"
    parts = [
        contract.underlying_symbol,
        contract.expiry.isoformat(),
        str(contract.strike),
        contract.option_type.value,
        contract.exchange or "SMART",
        contract.currency or "USD",
        contract.trading_class or "",
    ]
    return "option:" + "|".join(part.upper() for part in parts)


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


def _market_data_type_name(value) -> str:
    try:
        key = int(value)
    except (TypeError, ValueError):
        return "unknown"
    return {1: "live", 2: "frozen", 3: "delayed", 4: "delayed_frozen"}.get(key, "unknown")


def _quote_timing(ticker, now: datetime) -> tuple[datetime | None, float | None]:
    source = getattr(ticker, "rtTime", None) or getattr(ticker, "time", None)
    if source is None:
        return None, None
    if source.tzinfo is None:
        source = source.replace(tzinfo=timezone.utc)
    source_local = source.astimezone(now.tzinfo)
    age = max(0.0, (now - source_local).total_seconds())
    return source_local, age
