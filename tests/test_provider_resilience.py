import math
from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pandas as pd

from src.config import AppConfig
from src.engine.capture_manager import collect_signals
from src.engine.signal_parser import read_signals_csv
from src.models import ContractRole, OptionType, TradeSignal
from src.providers import IBKRProvider, MockProvider, ProviderError


TZ = ZoneInfo("America/Chicago")


class BadSignalProvider(MockProvider):
    def resolve_signal(self, signal):
        if signal.symbol == "BAD":
            raise ProviderError("intentional signal failure", code=999)
        return signal


class BadContractProvider(MockProvider):
    def get_option_quote(self, contract, stock_last=None):
        if contract.role is ContractRole.EXACT_OPPOSITE:
            raise ProviderError("intentional contract failure", code=998)
        return super().get_option_quote(contract, stock_last)


def test_one_bad_signal_does_not_abort_multi_signal_file(tmp_path: Path):
    signals_file = tmp_path / "signals.csv"
    signals_file.write_text(
        "timestamp_local,symbol,direction,signal_strike,expiry,signal_premium,stock_price_at_signal\n"
        "2026-06-28T10:00:00-05:00,GOOD,CALL,40,2026-07-17,0.40,36.50\n"
        "2026-06-28T10:01:00-05:00,BAD,CALL,40,2026-07-17,0.40,36.50\n",
        encoding="utf-8",
    )
    config = _config(tmp_path)
    signals = read_signals_csv(signals_file, timezone=config.timezone, provider="mock")

    run_folder = collect_signals(
        signals=signals,
        provider=BadSignalProvider(config.timezone),
        config=config,
        duration_seconds=0.05,
        quiet=True,
    )

    signal_rows = pd.read_csv(run_folder / "signals.csv")
    errors = pd.read_csv(run_folder / "provider_errors.csv")
    stock_rows = pd.read_csv(run_folder / "stock_ticks.csv")
    assert set(signal_rows["symbol"]) == {"GOOD", "BAD"}
    assert signal_rows.loc[signal_rows["symbol"] == "BAD", "status"].iloc[0] == "FAILED"
    assert set(stock_rows["symbol"]) == {"GOOD"}
    assert "resolve_signal" in set(errors["failure_stage"])


def test_one_bad_contract_does_not_abort_other_contracts(tmp_path: Path):
    config = _config(tmp_path)
    signal = _signal("GOOD")

    run_folder = collect_signals(
        signals=[signal],
        provider=BadContractProvider(config.timezone),
        config=config,
        duration_seconds=0.05,
        quiet=True,
    )

    errors = pd.read_csv(run_folder / "provider_errors.csv")
    option_rows = pd.read_csv(run_folder / "option_ticks.csv")
    assert "option_quote" in set(errors["failure_stage"])
    assert "EXACT_OPPOSITE" in set(errors["contract_role"])
    assert not option_rows.empty
    assert "SIGNAL_CONTRACT" in set(option_rows["contract_role"])


def test_ibkr_missing_last_marks_stock_fallback_and_unknown_age():
    contract = SimpleNamespace(symbol="XYZ")
    ticker = SimpleNamespace(
        bid=44.50,
        ask=44.70,
        last=math.nan,
        close=44.40,
        volume=1000,
        marketDataType=1,
        rtTime=None,
        time=None,
    )
    fake_ib = SimpleNamespace(
        qualifyContracts=lambda _contract: [contract],
        reqMktData=lambda *_args: ticker,
        sleep=lambda _seconds: None,
    )
    provider = IBKRProvider(timezone="America/Chicago")
    provider.ib = fake_ib

    quote = provider._request_stock_quote(contract, "XYZ", fallback_price=44.64)

    assert quote.last == 44.40
    assert quote.fallback_used is True
    assert quote.quote_is_live is False
    assert quote.stock_price_source == "PROVIDER_CLOSE_FALLBACK"
    assert quote.stock_quote_status == "FALLBACK"
    assert quote.quote_source_timestamp is None
    assert quote.quote_age_seconds is None


def _config(tmp_path: Path) -> AppConfig:
    return AppConfig(
        data_dir=tmp_path,
        enable_news=False,
        snapshot_interval_seconds=0.001,
        itm_strikes_to_track=1,
        otm_strikes_to_track=1,
        lotto_strikes_to_track=0,
    )


def _signal(symbol: str) -> TradeSignal:
    return TradeSignal(
        signal_id=f"{symbol}_TEST",
        timestamp_local=datetime(2026, 6, 28, 10, 0, tzinfo=TZ),
        symbol=symbol,
        direction=OptionType.CALL,
        signal_strike=40,
        expiry=date(2026, 7, 17),
        signal_premium=0.40,
        stock_price_at_signal=36.50,
        provider="mock",
    )
