from __future__ import annotations

from pathlib import Path

from src.config import AppConfig
from src.engine.summarizer import summarize_run


def replay_run(run_folder: Path, config: AppConfig) -> dict[str, Path]:
    return summarize_run(run_folder, config)
