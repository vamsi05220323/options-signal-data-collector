from __future__ import annotations

import math

from src.config import AppConfig
from src.models import ContractRole, OptionContract, OptionType, TradeSignal


ROLE_RANK = {
    ContractRole.SIGNAL_CONTRACT: 0,
    ContractRole.EXACT_OPPOSITE: 10,
    ContractRole.ITM_OPPOSITE: 20,
    ContractRole.ATM_OPPOSITE: 30,
    ContractRole.OTM_OPPOSITE: 40,
    ContractRole.LOTTO_OBSERVATION_ONLY: 90,
}


def select_contracts_for_signal(
    signal: TradeSignal,
    current_stock_price: float,
    available_strikes: list[float] | None,
    config: AppConfig,
) -> list[OptionContract]:
    strikes = sorted(set(float(strike) for strike in (available_strikes or [])))
    if not strikes:
        strikes = _synthetic_strikes(signal.signal_strike, current_stock_price)
    contracts: list[OptionContract] = []
    seen: set[tuple[float, OptionType]] = set()

    if config.track_signal_contract:
        _append_contract(
            contracts,
            seen,
            signal,
            signal.signal_strike,
            signal.direction,
            ContractRole.SIGNAL_CONTRACT,
        )

    opposite = signal.opposite_direction
    if config.track_exact_opposite:
        exact = _closest(strikes, signal.signal_strike)
        _append_contract(contracts, seen, signal, exact, opposite, ContractRole.EXACT_OPPOSITE)

    atm = _closest(strikes, current_stock_price)
    _append_contract(contracts, seen, signal, atm, opposite, ContractRole.ATM_OPPOSITE)

    if opposite is OptionType.PUT:
        itm_candidates = [strike for strike in strikes if strike > current_stock_price]
        otm_candidates = [strike for strike in reversed(strikes) if strike < current_stock_price]
    else:
        itm_candidates = [strike for strike in reversed(strikes) if strike < current_stock_price]
        otm_candidates = [strike for strike in strikes if strike > current_stock_price]

    for strike in _take_unseen(itm_candidates, seen, opposite, config.itm_strikes_to_track):
        _append_contract(contracts, seen, signal, strike, opposite, ContractRole.ITM_OPPOSITE)

    for strike in _take_unseen(otm_candidates, seen, opposite, config.otm_strikes_to_track):
        _append_contract(contracts, seen, signal, strike, opposite, ContractRole.OTM_OPPOSITE)

    for strike in _take_unseen(otm_candidates, seen, opposite, config.lotto_strikes_to_track):
        _append_contract(contracts, seen, signal, strike, opposite, ContractRole.LOTTO_OBSERVATION_ONLY)

    return sorted(contracts, key=lambda contract: (contract.rank, contract.strike))


def _append_contract(
    contracts: list[OptionContract],
    seen: set[tuple[float, OptionType]],
    signal: TradeSignal,
    strike: float,
    option_type: OptionType,
    role: ContractRole,
) -> None:
    key = (round(strike, 4), option_type)
    if key in seen:
        return
    seen.add(key)
    contracts.append(
        OptionContract(
            underlying_symbol=signal.symbol,
            expiry=signal.expiry,
            strike=strike,
            option_type=option_type,
            role=role,
            rank=ROLE_RANK[role],
        )
    )


def _take_unseen(
    candidates: list[float],
    seen: set[tuple[float, OptionType]],
    option_type: OptionType,
    count: int,
) -> list[float]:
    selected: list[float] = []
    for strike in candidates:
        if (round(strike, 4), option_type) in seen:
            continue
        selected.append(strike)
        if len(selected) >= count:
            break
    return selected


def _closest(strikes: list[float], target: float) -> float:
    return min(strikes, key=lambda strike: (abs(strike - target), strike))


def _synthetic_strikes(signal_strike: float, stock_price: float) -> list[float]:
    step = _default_step(max(signal_strike, stock_price))
    low_anchor = math.floor((min(signal_strike, stock_price) - step * 8) / step) * step
    high_anchor = math.ceil((max(signal_strike, stock_price) + step * 8) / step) * step
    strikes: list[float] = []
    current = max(step, low_anchor)
    while current <= high_anchor + 0.0001:
        strikes.append(round(current, 4))
        current += step
    return sorted(set(strikes))


def _default_step(reference: float) -> float:
    if reference < 10:
        return 1.0
    if reference < 30:
        return 2.5
    return 1.0
