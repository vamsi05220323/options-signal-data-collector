from pathlib import Path

from src.config import AppConfig
from src.engine.capture_manager import collect_signals
from src.engine.signal_parser import read_signals_csv
from src.providers import MockProvider


def test_mock_collects_multiple_signals(tmp_path: Path):
    csv_path = tmp_path / "signals.csv"
    csv_path.write_text(
        "\n".join(
            [
                "timestamp_local,symbol,direction,signal_strike,expiry,signal_premium,stock_price_at_signal",
                "2026-06-25T10:05:00-05:00,BEAM,CALL,40,2026-07-17,0.40,36.50",
                "2026-06-25T10:07:00-05:00,VRNS,CALL,40,2026-07-17,0.40,35.60",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    config = AppConfig(data_dir=tmp_path, snapshot_interval_seconds=0.01)
    signals = read_signals_csv(csv_path, timezone=config.timezone, provider="mock")
    run_folder = collect_signals(
        signals=signals,
        provider=MockProvider(config.timezone),
        config=config,
        duration_seconds=1,
        quiet=True,
    )
    assert (run_folder / "option_ticks.csv").exists()
    assert (run_folder / "summary_by_signal.csv").read_text(encoding="utf-8").count("\n") >= 3
