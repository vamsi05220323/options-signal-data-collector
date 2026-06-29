from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    def load_dotenv(*_args, **_kwargs) -> bool:
        return False


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_LOCAL = PROJECT_ROOT / ".env.local"


@dataclass(slots=True)
class AppConfig:
    data_provider: str = "mock"
    enable_alerts: bool = False
    enable_trading: bool = False
    track_signal_contract: bool = True
    track_exact_opposite: bool = True
    itm_strikes_to_track: int = 1
    otm_strikes_to_track: int = 5
    lotto_strikes_to_track: int = 1
    snapshot_interval_seconds: float = 1.0
    aggressive_capture_minutes: int = 30
    normal_capture_seconds: float = 5.0
    spread_max_pct: float = 35.0
    wide_spread_max_pct: float = 60.0
    min_compression_pct: float = 30.0
    min_rebound_pct: float = 20.0
    stale_quote_seconds: int = 900
    intrinsic_violation_tolerance_abs: float = 0.05
    intrinsic_violation_tolerance_pct: float = 2.0
    allow_locked_market: bool = False
    timezone: str = "America/Chicago"
    data_dir: Path = PROJECT_ROOT / "data"
    ibkr_host: str = "127.0.0.1"
    ibkr_port: int = 7497
    ibkr_client_id: int = 12
    enable_news: bool = True
    news_provider: str = "mock"
    news_lookback_hours: int = 24
    news_context_days: int = 7
    news_refresh_minutes: int = 10
    news_max_articles_per_symbol: int = 50
    alpha_vantage_api_key: str = ""
    finnhub_api_key: str = ""

    def provider_name(self, override: str | None = None) -> str:
        return (override or self.data_provider or "mock").strip().lower()


def load_config(env_file: Path | None = None) -> AppConfig:
    load_dotenv(PROJECT_ROOT / ".env")
    load_dotenv(env_file or ENV_LOCAL, override=True)
    return AppConfig(
        data_provider=_env_str("DATA_PROVIDER", "mock"),
        enable_alerts=_env_bool("ENABLE_ALERTS", False),
        enable_trading=_env_bool("ENABLE_TRADING", False),
        track_signal_contract=_env_bool("TRACK_SIGNAL_CONTRACT", True),
        track_exact_opposite=_env_bool("TRACK_EXACT_OPPOSITE", True),
        itm_strikes_to_track=_env_int("ITM_STRIKES_TO_TRACK", 1),
        otm_strikes_to_track=_env_int("OTM_STRIKES_TO_TRACK", 5),
        lotto_strikes_to_track=_env_int("LOTTO_STRIKES_TO_TRACK", 1),
        snapshot_interval_seconds=_env_float("SNAPSHOT_INTERVAL_SECONDS", 1.0),
        aggressive_capture_minutes=_env_int("AGGRESSIVE_CAPTURE_MINUTES", 30),
        normal_capture_seconds=_env_float("NORMAL_CAPTURE_SECONDS", 5.0),
        spread_max_pct=_env_float("SPREAD_MAX_PCT", 35.0),
        wide_spread_max_pct=_env_float("WIDE_SPREAD_MAX_PCT", 60.0),
        min_compression_pct=_env_float("MIN_COMPRESSION_PCT", 30.0),
        min_rebound_pct=_env_float("MIN_REBOUND_PCT", 20.0),
        stale_quote_seconds=_env_int("STALE_QUOTE_SECONDS", 900),
        intrinsic_violation_tolerance_abs=_env_float("INTRINSIC_VIOLATION_TOLERANCE_ABS", 0.05),
        intrinsic_violation_tolerance_pct=_env_float("INTRINSIC_VIOLATION_TOLERANCE_PCT", 2.0),
        allow_locked_market=_env_bool("ALLOW_LOCKED_MARKET", False),
        timezone=_env_str("TIMEZONE", "America/Chicago"),
        data_dir=Path(_env_str("DATA_DIR", str(PROJECT_ROOT / "data"))),
        ibkr_host=_env_str("IBKR_HOST", "127.0.0.1"),
        ibkr_port=_env_int("IBKR_PORT", 7497),
        ibkr_client_id=_env_int("IBKR_CLIENT_ID", 12),
        enable_news=_env_bool("ENABLE_NEWS", True),
        news_provider=_env_str("NEWS_PROVIDER", "mock"),
        news_lookback_hours=_env_int("NEWS_LOOKBACK_HOURS", 24),
        news_context_days=_env_int("NEWS_CONTEXT_DAYS", 7),
        news_refresh_minutes=_env_int("NEWS_REFRESH_MINUTES", 10),
        news_max_articles_per_symbol=_env_int("NEWS_MAX_ARTICLES_PER_SYMBOL", 50),
        alpha_vantage_api_key=_env_str("ALPHA_VANTAGE_API_KEY", ""),
        finnhub_api_key=_env_str("FINNHUB_API_KEY", ""),
    )


def write_non_secret_env(config: AppConfig, provider: str | None = None) -> None:
    existing = _read_env_file(ENV_LOCAL)
    updates = {
        "DATA_PROVIDER": provider or config.data_provider,
        "ENABLE_ALERTS": "false",
        "ENABLE_TRADING": "false",
        "TIMEZONE": config.timezone,
        "IBKR_HOST": config.ibkr_host,
        "IBKR_PORT": str(config.ibkr_port),
        "IBKR_CLIENT_ID": str(config.ibkr_client_id),
        "ENABLE_NEWS": str(config.enable_news).lower(),
        "NEWS_PROVIDER": config.news_provider,
    }
    existing.update(updates)
    lines = [f"{key}={value}" for key, value in existing.items()]
    ENV_LOCAL.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _read_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def _env_str(name: str, default: str) -> str:
    value = os.getenv(name)
    return default if value in (None, "") else value


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value in (None, ""):
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    return default if value in (None, "") else int(value)


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    return default if value in (None, "") else float(value)
