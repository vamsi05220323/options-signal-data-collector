from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from src.config import AppConfig, write_non_secret_env
from src.engine.strike_selector import select_contracts_for_signal
from src.models import OptionType, TradeSignal
from src.providers import IBKRProvider, MockProvider, ProviderError, WebullProvider


def run_preflight(config: AppConfig, provider_name: str, *, assume_yes: bool = False) -> int:
    provider_name = provider_name.lower()
    write_non_secret_env(config, provider=provider_name)
    print("Preflight")
    print(f"provider={provider_name}")
    print("alerts=false")
    print("trading=false")
    if provider_name == "mock":
        return _run_mock_preflight(config)
    if provider_name == "ibkr":
        return _run_ibkr_preflight(config)
    if provider_name == "webull":
        return _run_webull_preflight()
    raise ValueError(f"Unknown provider: {provider_name}")


def _run_mock_preflight(config: AppConfig) -> int:
    provider = MockProvider(timezone=config.timezone)
    signal = _test_signal(config, "mock")
    stock = provider.get_stock_quote(signal.symbol, signal.stock_price_at_signal)
    strikes = provider.get_option_chain(signal.symbol, signal.expiry.isoformat(), signal.opposite_direction.value, stock.last)
    contracts = select_contracts_for_signal(signal, stock.last or signal.stock_price_at_signal, strikes, config)
    quote = provider.get_option_quote(contracts[0], stock.last)
    print(f"stock_quote bid={stock.bid} ask={stock.ask} last={stock.last}")
    print(f"option_chain strikes={len(strikes)}")
    print(f"option_quote {contracts[0].display} bid={quote.bid} ask={quote.ask} last={quote.last}")
    print("mock preflight ok")
    return 0


def _run_ibkr_preflight(config: AppConfig) -> int:
    provider = IBKRProvider(
        host=config.ibkr_host,
        port=config.ibkr_port,
        client_id=config.ibkr_client_id,
        timezone=config.timezone,
    )
    signal = _test_signal(config, "ibkr")
    try:
        provider.connect()
        stock = provider.get_stock_quote(signal.symbol, signal.stock_price_at_signal)
        strikes = provider.get_option_chain(signal.symbol, signal.expiry.isoformat(), signal.opposite_direction.value, stock.last)
        contracts = select_contracts_for_signal(signal, stock.last or signal.stock_price_at_signal, strikes, config)
        quote = provider.get_option_quote(contracts[0], stock.last)
    except ProviderError as exc:
        print(f"IBKR preflight failed: {exc}")
        print("Check that TWS/IB Gateway is running, API is enabled, and the paper/live port is correct.")
        print("For US options, confirm OPRA and underlying stock data entitlements.")
        return 1
    finally:
        provider.close()
    print(f"stock_quote bid={stock.bid} ask={stock.ask} last={stock.last}")
    print(f"option_chain strikes={len(strikes)}")
    print(f"option_quote {contracts[0].display} bid={quote.bid} ask={quote.ask} last={quote.last}")
    missing: list[str] = []
    if stock.bid is None or stock.ask is None:
        missing.append("stock bid/ask")
    if quote.bid is None or quote.ask is None:
        missing.append("option bid/ask")
    if missing:
        print("ibkr connection ok")
        print(f"market_data_incomplete={', '.join(missing)}")
        print("Most likely causes: market is closed, delayed-only data, missing OPRA options data, or missing US stock top-of-book data.")
        return 2
    print("ibkr preflight ok")
    return 0


def _run_webull_preflight() -> int:
    provider = WebullProvider()
    try:
        provider.connect()
    except ProviderError as exc:
        print(f"Webull unavailable: {exc}")
        print("Only official Webull OpenAPI should be used; no unofficial scraping was configured.")
        return 1
    return 0


def _test_signal(config: AppConfig, provider: str) -> TradeSignal:
    timestamp = datetime.now(ZoneInfo(config.timezone))
    return TradeSignal(
        signal_id=f"PREFLIGHT_{timestamp.strftime('%Y%m%d_%H%M%S')}",
        timestamp_local=timestamp,
        symbol="BEAM",
        direction=OptionType.CALL,
        signal_strike=40,
        expiry=datetime(2026, 7, 17).date(),
        signal_premium=0.40,
        stock_price_at_signal=36.50,
        provider=provider,
    )
