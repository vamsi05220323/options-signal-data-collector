from datetime import date, datetime
from zoneinfo import ZoneInfo

from src.engine.signal_parser import parse_expiry, parse_signal_text
from src.engine.signal_parser import read_signals_csv
from src.models import OptionType


def test_parse_standard_signal_text():
    ts = datetime(2026, 6, 25, 10, 0, tzinfo=ZoneInfo("America/Chicago"))
    signal = parse_signal_text("VRNS 40 CALL 7/17 @0.40", stock_price=35.60, timestamp_local=ts, today=date(2026, 6, 25))
    assert signal.symbol == "VRNS"
    assert signal.direction is OptionType.CALL
    assert signal.expiry.isoformat() == "2026-07-17"
    assert signal.signal_premium == 0.40
    assert signal.stock_price_at_signal == 35.60


def test_parse_compact_signal_text():
    ts = datetime(2026, 6, 25, 10, 0, tzinfo=ZoneInfo("America/Chicago"))
    signal = parse_signal_text("BEAM 40C 07/17 0.40", stock_price=36.5, timestamp_local=ts, today=date(2026, 6, 25))
    assert signal.direction is OptionType.CALL
    assert signal.signal_strike == 40


def test_missing_year_rolls_forward():
    assert parse_expiry("7/17", today=date(2026, 8, 1)).isoformat() == "2027-07-17"


def test_signal_csv_accepts_optional_ibkr_identity_columns(tmp_path):
    path = tmp_path / "signals.csv"
    path.write_text(
        "\n".join(
            [
                "timestamp_local,symbol,direction,signal_strike,expiry,signal_premium,stock_price_at_signal,primary_exchange,currency,ibkr_con_id",
                "2026-06-25T10:05:00-05:00,PEP,CALL,145,2026-07-17,1.25,144.50,NASDAQ,USD,11054",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    signal = read_signals_csv(path, timezone="America/Chicago", provider="mock")[0]
    assert signal.symbol == "PEP"
    assert signal.primary_exchange == "NASDAQ"
    assert signal.currency == "USD"
    assert signal.ibkr_con_id == 11054
