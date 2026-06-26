from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from src.config import AppConfig
from src.engine.metrics import (
    compute_mid,
    compute_spread_abs,
    compute_spread_pct,
    extrinsic_value,
    intrinsic_value,
    percent_change,
    premium_compression_pct,
    rebound_from_low_pct,
)
from src.engine.quote_validation import validate_quote
from src.engine.strike_selector import select_contracts_for_signal
from src.engine.summarizer import summarize_run
from src.models import ContractRole, OptionContract, OptionTick, StockQuote, StockTick, TradeSignal
from src.news_providers import (
    AlphaVantageNewsProvider,
    BaseNewsProvider,
    FinnhubNewsProvider,
    MockNewsProvider,
    NewsProviderError,
)
from src.news_providers.base import summarize_news
from src.providers.base import BaseDataProvider, ProviderError
from src.storage import RunStorage
from src.ui import LiveConsole


@dataclass(slots=True)
class ContractRuntime:
    contract: OptionContract
    initial_mid: float | None = None
    min_mid: float | None = None
    max_mid: float | None = None
    min_ask: float | None = None
    max_bid: float | None = None
    active: bool = True


@dataclass(slots=True)
class SignalRuntime:
    signal: TradeSignal
    contracts: list[ContractRuntime]
    post_signal_high: float
    post_signal_low: float


def collect_signals(
    *,
    signals: list[TradeSignal],
    provider: BaseDataProvider,
    config: AppConfig,
    duration_seconds: int | None,
    capture_start_time: datetime | None = None,
    capture_end_time: datetime | None = None,
    run_folder: Path | None = None,
    quiet: bool = False,
    summarize: bool = True,
) -> Path:
    if not signals:
        raise ValueError("No signals to collect.")
    tz = ZoneInfo(config.timezone)
    active_run_folder = run_folder or config.data_dir / "runs" / datetime.now(tz).strftime("%Y-%m-%d")
    storage = RunStorage(active_run_folder)
    console = LiveConsole(quiet=quiet)
    _wait_until_capture_start(capture_start_time, capture_end_time, tz, console)
    provider.connect()
    runtimes: list[SignalRuntime] = []
    try:
        for signal in signals:
            signal = provider.resolve_signal(signal)
            storage.append_signal(signal)
            contracts = _resolve_contracts(signal, provider, config, console)
            runtimes.append(
                SignalRuntime(
                    signal=signal,
                    contracts=[ContractRuntime(contract=contract) for contract in contracts],
                    post_signal_high=signal.stock_price_at_signal,
                    post_signal_low=signal.stock_price_at_signal,
                )
            )
            _collect_initial_news(signal, config, storage, console)

        latest_stock_ticks: dict[str, StockTick] = {}
        latest_option_ticks: dict[str, OptionTick] = {}
        start = time.monotonic()
        loops = 0
        while True:
            if _capture_end_reached(capture_end_time, tz):
                break
            if _duration_reached(start, duration_seconds):
                break
            for runtime in runtimes:
                if _capture_end_reached(capture_end_time, tz) or _duration_reached(start, duration_seconds):
                    break
                stock = provider.get_stock_quote_for_signal(
                    runtime.signal,
                    fallback_price=runtime.signal.stock_price_at_signal,
                )
                stock_tick = _build_stock_tick(runtime, stock)
                storage.append_stock_tick(stock_tick)
                latest_stock_ticks[runtime.signal.signal_id] = stock_tick
                for contract_runtime in runtime.contracts:
                    if _capture_end_reached(capture_end_time, tz) or _duration_reached(start, duration_seconds):
                        break
                    if not contract_runtime.active:
                        continue
                    try:
                        quote = provider.get_option_quote(contract_runtime.contract, stock.last)
                    except ProviderError as exc:
                        console.status(f"Quote skipped for {contract_runtime.contract.display}: {exc}")
                        contract_runtime.active = False
                        continue
                    option_tick = _build_option_tick(runtime, contract_runtime, stock, quote)
                    storage.append_option_tick(option_tick)
                    latest_option_ticks[f"{option_tick.signal_id}:{option_tick.option_symbol}"] = option_tick
            if loops % 5 == 0:
                console.render([runtime.signal for runtime in runtimes], latest_stock_ticks, latest_option_ticks)
            loops += 1
            if _duration_reached(start, duration_seconds):
                break
            if _capture_end_reached(capture_end_time, tz):
                break
            time.sleep(config.snapshot_interval_seconds)
    finally:
        provider.close()
        storage.close()

    if summarize:
        summarize_run(storage.run_folder, config)
    return storage.run_folder


def _resolve_contracts(
    signal: TradeSignal,
    provider: BaseDataProvider,
    config: AppConfig,
    console: LiveConsole,
) -> list[OptionContract]:
    try:
        strikes = provider.get_option_chain_for_signal(
            signal,
            signal.opposite_direction.value,
            stock_price=signal.stock_price_at_signal,
        )
    except ProviderError as exc:
        console.status(f"Option chain lookup failed for {signal.symbol}; using synthetic grid: {exc}")
        strikes = []
    contracts = select_contracts_for_signal(signal, signal.stock_price_at_signal, strikes, config)
    console.status(f"{signal.signal_id}: tracking {len(contracts)} contracts")
    return contracts


def _build_stock_tick(runtime: SignalRuntime, stock: StockQuote) -> StockTick:
    if stock.last is not None:
        runtime.post_signal_high = max(runtime.post_signal_high, stock.last)
        runtime.post_signal_low = min(runtime.post_signal_low, stock.last)
    stock_mid = compute_mid(stock.bid, stock.ask)
    high = runtime.post_signal_high
    pullback = None
    if stock.last is not None and high > 0:
        pullback = (high - stock.last) / high * 100.0
    return StockTick(
        timestamp_local=stock.timestamp_local,
        signal_id=runtime.signal.signal_id,
        symbol=runtime.signal.symbol,
        stock_bid=stock.bid,
        stock_ask=stock.ask,
        stock_last=stock.last,
        stock_mid=stock_mid,
        stock_volume=stock.volume,
        seconds_since_signal=max(0.0, (stock.timestamp_local - runtime.signal.timestamp_local).total_seconds()),
        stock_price_at_signal=runtime.signal.stock_price_at_signal,
        post_signal_high=runtime.post_signal_high,
        post_signal_low=runtime.post_signal_low,
        stock_change_from_signal_pct=percent_change(stock.last, runtime.signal.stock_price_at_signal),
        pump_from_signal_pct=percent_change(runtime.post_signal_high, runtime.signal.stock_price_at_signal),
        pullback_from_high_pct=pullback,
    )


def _build_option_tick(runtime: SignalRuntime, contract_runtime: ContractRuntime, stock: StockQuote, quote) -> OptionTick:
    contract = contract_runtime.contract
    mid = quote.mid if quote.mid is not None else compute_mid(quote.bid, quote.ask)
    spread_abs = compute_spread_abs(quote.bid, quote.ask)
    spread_pct = compute_spread_pct(quote.bid, quote.ask, mid)
    intrinsic = intrinsic_value(contract.option_type, contract.strike, stock.last)
    extrinsic = extrinsic_value(mid, intrinsic)

    if mid is not None:
        if contract_runtime.initial_mid is None:
            contract_runtime.initial_mid = mid
        contract_runtime.min_mid = mid if contract_runtime.min_mid is None else min(contract_runtime.min_mid, mid)
        contract_runtime.max_mid = mid if contract_runtime.max_mid is None else max(contract_runtime.max_mid, mid)
    if quote.ask is not None:
        contract_runtime.min_ask = quote.ask if contract_runtime.min_ask is None else min(contract_runtime.min_ask, quote.ask)
    if quote.bid is not None:
        contract_runtime.max_bid = quote.bid if contract_runtime.max_bid is None else max(contract_runtime.max_bid, quote.bid)

    validation = validate_quote(
        bid=quote.bid,
        ask=quote.ask,
        mid=mid,
        spread_pct=spread_pct,
        spread_max_pct=_spread_limit(contract.role),
        role=contract.role,
        volume=quote.volume,
        open_interest=quote.open_interest,
        quote_age_seconds=quote.quote_age_seconds,
    )
    return OptionTick(
        timestamp_local=quote.timestamp_local,
        signal_id=runtime.signal.signal_id,
        underlying_symbol=runtime.signal.symbol,
        option_symbol=quote.option_symbol or contract.storage_symbol,
        option_con_id=contract.con_id,
        option_local_symbol=contract.local_symbol,
        option_trading_class=contract.trading_class,
        option_exchange=contract.exchange,
        contract_role=contract.role,
        expiry=contract.expiry,
        strike=contract.strike,
        option_type=contract.option_type,
        bid=quote.bid,
        ask=quote.ask,
        mid=mid,
        last=quote.last,
        volume=quote.volume,
        open_interest=quote.open_interest,
        implied_volatility=quote.implied_volatility,
        delta=quote.delta,
        gamma=quote.gamma,
        theta=quote.theta,
        vega=quote.vega,
        bid_size=quote.bid_size,
        ask_size=quote.ask_size,
        spread_abs=spread_abs,
        spread_pct=spread_pct,
        intrinsic_value=intrinsic,
        extrinsic_value=extrinsic,
        quote_timestamp=quote.quote_timestamp,
        quote_age_seconds=quote.quote_age_seconds,
        quote_is_valid=validation.is_valid,
        reason_invalid=validation.reason_invalid,
        seconds_since_signal=max(0.0, (quote.timestamp_local - runtime.signal.timestamp_local).total_seconds()),
        option_initial_mid=contract_runtime.initial_mid,
        option_min_mid_since_signal=contract_runtime.min_mid,
        option_max_mid_since_signal=contract_runtime.max_mid,
        option_min_ask_since_signal=contract_runtime.min_ask,
        option_max_bid_since_signal=contract_runtime.max_bid,
        compression_from_initial_pct=premium_compression_pct(contract_runtime.initial_mid, contract_runtime.min_mid),
        rebound_from_low_pct=rebound_from_low_pct(mid, contract_runtime.min_mid),
    )


def _spread_limit(role: ContractRole) -> float:
    if role is ContractRole.LOTTO_OBSERVATION_ONLY:
        return 60.0
    return 35.0


def _wait_until_capture_start(
    capture_start_time: datetime | None,
    capture_end_time: datetime | None,
    tz: ZoneInfo,
    console: LiveConsole,
) -> None:
    now = datetime.now(tz)
    if capture_end_time and capture_end_time <= now:
        raise ValueError("--end-time is already in the past for the configured timezone.")
    if not capture_start_time or capture_start_time <= now:
        return
    console.status(f"Waiting until capture start time {capture_start_time.isoformat()}")
    while True:
        now = datetime.now(tz)
        if now >= capture_start_time:
            return
        if capture_end_time and now >= capture_end_time:
            raise ValueError("Capture end time arrived before capture started.")
        time.sleep(min(5.0, max(0.1, (capture_start_time - now).total_seconds())))


def _capture_end_reached(capture_end_time: datetime | None, tz: ZoneInfo) -> bool:
    return bool(capture_end_time and datetime.now(tz) >= capture_end_time)


def _duration_reached(start: float, duration_seconds: int | None) -> bool:
    return bool(duration_seconds is not None and time.monotonic() - start >= duration_seconds)


def _collect_initial_news(signal: TradeSignal, config: AppConfig, storage: RunStorage, console: LiveConsole) -> None:
    if not config.enable_news:
        return
    provider = _news_provider_from_config(config)
    collected_at = datetime.now(ZoneInfo(config.timezone))
    try:
        articles = provider.fetch(signal, collected_at)
    except NewsProviderError as exc:
        console.status(f"News unavailable for {signal.symbol}: {exc}")
        provider = MockNewsProvider()
        articles = provider.fetch(signal, collected_at)
    for article in articles[: config.news_max_articles_per_symbol]:
        storage.append_news_article(article)
    storage.append_news_summary(summarize_news(signal, provider.name, articles))


def _news_provider_from_config(config: AppConfig) -> BaseNewsProvider:
    provider = (config.news_provider or "mock").lower()
    if provider == "alpha_vantage" and config.alpha_vantage_api_key:
        return AlphaVantageNewsProvider(config.alpha_vantage_api_key, config.news_max_articles_per_symbol)
    if provider == "finnhub" and config.finnhub_api_key:
        return FinnhubNewsProvider(config.finnhub_api_key, config.news_max_articles_per_symbol)
    return MockNewsProvider()
