from datetime import date, datetime
from zoneinfo import ZoneInfo

from src.config import AppConfig
from src.engine.strike_selector import select_contracts_for_signal
from src.models import OptionType, TradeSignal


def test_selected_contracts_carry_underlying_identity():
    signal = TradeSignal(
        signal_id="PEP_TEST",
        timestamp_local=datetime(2026, 6, 25, 10, 0, tzinfo=ZoneInfo("America/Chicago")),
        symbol="PEP",
        direction=OptionType.CALL,
        signal_strike=145,
        expiry=date(2026, 7, 17),
        signal_premium=1.25,
        stock_price_at_signal=144.50,
        primary_exchange="NASDAQ",
        currency="USD",
        ibkr_con_id=11054,
    )
    contracts = select_contracts_for_signal(signal, 144.50, [140, 142.5, 145, 147.5, 150], AppConfig())
    assert contracts
    assert {contract.currency for contract in contracts} == {"USD"}
    assert {contract.primary_exchange for contract in contracts} == {"NASDAQ"}
