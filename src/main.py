from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from src.config import AppConfig, load_config
from src.engine.capture_manager import collect_signals
from src.engine.signal_parser import parse_expiry, read_signals_csv
from src.engine.summarizer import summarize_run
from src.models import OptionType, TradeSignal
from src.preflight import run_preflight
from src.providers import IBKRProvider, MockProvider, ProviderError, ReplayProvider, WebullProvider


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Options signal data collector. Data collection only; no trading.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    preflight = subparsers.add_parser("preflight", help="Check provider access and quote availability.")
    preflight.add_argument("--mock", action="store_true", help="Run mock preflight without prompting.")
    preflight.add_argument("--provider", choices=["ibkr", "webull", "mock"], help="Provider to test.")

    collect_signal = subparsers.add_parser("collect-signal", help="Collect one signal.")
    collect_signal.add_argument("--symbol", required=True)
    collect_signal.add_argument("--direction", choices=["CALL", "PUT"], required=True)
    collect_signal.add_argument("--strike", type=float, required=True)
    collect_signal.add_argument("--expiry", required=True)
    collect_signal.add_argument("--signal-premium", type=float)
    collect_signal.add_argument("--stock-price", type=float, required=True)
    collect_signal.add_argument("--provider", choices=["ibkr", "webull", "mock"])
    collect_signal.add_argument("--duration-seconds", type=int)
    collect_signal.add_argument("--run-folder", type=Path)
    collect_signal.add_argument("--quiet", action="store_true")

    collect_file = subparsers.add_parser("collect-file", help="Collect all signals in a CSV.")
    collect_file.add_argument("--signals-file", type=Path, required=True)
    collect_file.add_argument("--provider", choices=["ibkr", "webull", "mock"])
    collect_file.add_argument("--duration-seconds", type=int)
    collect_file.add_argument("--run-folder", type=Path)
    collect_file.add_argument("--quiet", action="store_true")

    replay = subparsers.add_parser("replay", help="Replay/summarize a previous run folder.")
    replay.add_argument("--run-folder", type=Path, required=True)

    summarize = subparsers.add_parser("summarize", help="Summarize a run folder.")
    summarize.add_argument("--run-folder", type=Path, required=True)

    return parser


def provider_from_config(config: AppConfig, override: str | None = None, replay_folder: Path | None = None):
    name = config.provider_name(override)
    if name == "mock":
        return MockProvider(timezone=config.timezone)
    if name == "ibkr":
        return IBKRProvider(
            host=config.ibkr_host,
            port=config.ibkr_port,
            client_id=config.ibkr_client_id,
            timezone=config.timezone,
        )
    if name == "webull":
        return WebullProvider()
    if name == "replay" and replay_folder is not None:
        return ReplayProvider(replay_folder)
    raise ProviderError(f"Unknown provider: {name}")


def run_collect_signal(args: argparse.Namespace, config: AppConfig) -> int:
    provider_name = config.provider_name(args.provider)
    signal = TradeSignal(
        signal_id=make_cli_signal_id(args.symbol, config.timezone),
        timestamp_local=datetime.now(ZoneInfo(config.timezone)),
        symbol=args.symbol,
        direction=OptionType.from_text(args.direction),
        signal_strike=args.strike,
        expiry=parse_expiry(args.expiry),
        signal_premium=args.signal_premium,
        stock_price_at_signal=args.stock_price,
        provider=provider_name,
    )
    provider = provider_from_config(config, provider_name)
    run_folder = collect_signals(
        signals=[signal],
        provider=provider,
        config=config,
        duration_seconds=args.duration_seconds,
        run_folder=args.run_folder,
        quiet=args.quiet,
    )
    print(f"run_folder={run_folder}")
    return 0


def run_collect_file(args: argparse.Namespace, config: AppConfig) -> int:
    provider_name = config.provider_name(args.provider)
    signals = read_signals_csv(args.signals_file, timezone=config.timezone, provider=provider_name)
    provider = provider_from_config(config, provider_name)
    run_folder = collect_signals(
        signals=signals,
        provider=provider,
        config=config,
        duration_seconds=args.duration_seconds,
        run_folder=args.run_folder,
        quiet=args.quiet,
    )
    print(f"run_folder={run_folder}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    config = load_config()
    if args.command == "preflight":
        provider = "mock" if args.mock else (args.provider or config.data_provider)
        return run_preflight(config, provider)
    if args.command == "collect-signal":
        return run_collect_signal(args, config)
    if args.command == "collect-file":
        return run_collect_file(args, config)
    if args.command == "replay":
        summarize_run(args.run_folder, config)
        print(f"replay_summary={args.run_folder}")
        return 0
    if args.command == "summarize":
        outputs = summarize_run(args.run_folder, config)
        for name, path in outputs.items():
            print(f"{name}={path}")
        return 0
    parser.error("Unknown command")
    return 2


def make_cli_signal_id(symbol: str, timezone: str) -> str:
    now = datetime.now(ZoneInfo(timezone))
    return f"{symbol.upper().lstrip('$')}_{now.strftime('%Y%m%d_%H%M%S')}"


if __name__ == "__main__":
    raise SystemExit(main())
