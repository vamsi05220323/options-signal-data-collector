from datetime import date, datetime
from zoneinfo import ZoneInfo

from src.config import AppConfig
from src.engine.strike_selector import select_contracts_for_signal
from src.models import ContractRole, OptionType, TradeSignal


def _signal() -> TradeSignal:
    return TradeSignal(
        signal_id="BEAM_TEST",
        timestamp_local=datetime(2026, 6, 25, 10, 0, tzinfo=ZoneInfo("America/Chicago")),
        symbol="BEAM",
        direction=OptionType.CALL,
        signal_strike=40,
        expiry=date(2026, 7, 17),
        signal_premium=0.40,
        stock_price_at_signal=36.50,
    )


def test_tracks_signal_contract_and_opposite_grid():
    config = AppConfig(otm_strikes_to_track=5, lotto_strikes_to_track=1)
    strikes = [30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40]
    contracts = select_contracts_for_signal(_signal(), 36.5, strikes, config)
    roles = [contract.role for contract in contracts]
    assert ContractRole.SIGNAL_CONTRACT in roles
    assert ContractRole.EXACT_OPPOSITE in roles
    assert ContractRole.ATM_OPPOSITE in roles
    assert ContractRole.ITM_OPPOSITE in roles
    assert ContractRole.OTM_OPPOSITE in roles
    assert ContractRole.LOTTO_OBSERVATION_ONLY in roles
    assert contracts[0].option_type is OptionType.CALL
    assert all(contract.option_type is OptionType.PUT for contract in contracts[1:])


def test_uses_chain_grid_not_hard_coded_increment():
    config = AppConfig(otm_strikes_to_track=2, lotto_strikes_to_track=0)
    strikes = [30, 32.5, 35, 37.5, 40]
    contracts = select_contracts_for_signal(_signal(), 36.5, strikes, config)
    selected = {contract.strike for contract in contracts}
    assert 32.5 in selected
    assert 37.5 in selected
