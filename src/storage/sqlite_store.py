from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from src.models import NewsArticle, NewsSummary, StockTick, OptionTick, TradeSignal, serialize_row
from src.storage.csv_writer import (
    CONTRACT_SUMMARY_FIELDS,
    NEWS_ARTICLE_FIELDS,
    NEWS_SUMMARY_FIELDS,
    OPTION_BAR_FIELDS,
    OPTION_TICK_FIELDS,
    SIGNAL_FIELDS,
    SIGNAL_SUMMARY_FIELDS,
    STOCK_TICK_FIELDS,
    CsvTable,
)


TABLE_FIELDS = {
    "signals": SIGNAL_FIELDS,
    "stock_ticks": STOCK_TICK_FIELDS,
    "option_ticks": OPTION_TICK_FIELDS,
    "option_bars_5sec": OPTION_BAR_FIELDS,
    "option_bars_1m": OPTION_BAR_FIELDS,
    "option_bars_5m": OPTION_BAR_FIELDS,
    "contract_summary": CONTRACT_SUMMARY_FIELDS,
    "signal_summary": SIGNAL_SUMMARY_FIELDS,
    "news_articles": NEWS_ARTICLE_FIELDS,
    "news_summary_by_signal": NEWS_SUMMARY_FIELDS,
}


class RunStorage:
    def __init__(self, run_folder: Path) -> None:
        self.run_folder = run_folder
        self.run_folder.mkdir(parents=True, exist_ok=True)
        self.db_path = self.run_folder / "market_capture.sqlite"
        self.conn = sqlite3.connect(self.db_path)
        self._create_tables()
        self.csv_tables = {
            "signals": CsvTable(self.run_folder / "signals.csv", SIGNAL_FIELDS),
            "stock_ticks": CsvTable(self.run_folder / "stock_ticks.csv", STOCK_TICK_FIELDS),
            "option_ticks": CsvTable(self.run_folder / "option_ticks.csv", OPTION_TICK_FIELDS),
            "option_bars_5sec": CsvTable(self.run_folder / "option_5sec_bars.csv", OPTION_BAR_FIELDS),
            "option_bars_1m": CsvTable(self.run_folder / "option_1min_bars.csv", OPTION_BAR_FIELDS),
            "option_bars_5m": CsvTable(self.run_folder / "option_5min_bars.csv", OPTION_BAR_FIELDS),
            "contract_summary": CsvTable(self.run_folder / "summary_by_contract.csv", CONTRACT_SUMMARY_FIELDS),
            "signal_summary": CsvTable(self.run_folder / "summary_by_signal.csv", SIGNAL_SUMMARY_FIELDS),
            "news_articles": CsvTable(self.run_folder / "news_articles.csv", NEWS_ARTICLE_FIELDS),
            "news_summary_by_signal": CsvTable(self.run_folder / "news_summary_by_signal.csv", NEWS_SUMMARY_FIELDS),
        }

    @classmethod
    def create_daily(cls, data_dir: Path, now: datetime) -> "RunStorage":
        return cls(data_dir / "runs" / now.strftime("%Y-%m-%d"))

    def close(self) -> None:
        self.conn.commit()
        self.conn.close()

    def append_signal(self, signal: TradeSignal) -> None:
        row = serialize_row(signal)
        row["direction"] = signal.direction.value
        row["opposite_direction"] = signal.opposite_direction.value
        row["status"] = signal.status.value
        self.append_row("signals", row)

    def append_stock_tick(self, tick: StockTick) -> None:
        self.append_row("stock_ticks", serialize_row(tick))

    def append_option_tick(self, tick: OptionTick) -> None:
        self.append_row("option_ticks", serialize_row(tick))

    def append_news_article(self, article: NewsArticle) -> None:
        self.append_row("news_articles", serialize_row(article))

    def append_news_summary(self, summary: NewsSummary) -> None:
        self.append_row("news_summary_by_signal", serialize_row(summary))

    def rewrite_table(self, table: str, rows: list[dict[str, Any]]) -> None:
        self.csv_tables[table].rewrite(rows)
        cursor = self.conn.cursor()
        cursor.execute(f"DELETE FROM {table}")
        self.conn.commit()
        for row in rows:
            self._insert_sqlite(table, row)
        self.conn.commit()

    def append_row(self, table: str, row: dict[str, Any]) -> None:
        self.csv_tables[table].append(row)
        self._insert_sqlite(table, row)
        self.conn.commit()

    def _create_tables(self) -> None:
        cursor = self.conn.cursor()
        for table, fields in TABLE_FIELDS.items():
            columns = ", ".join(f'"{field}" TEXT' for field in fields)
            cursor.execute(f"CREATE TABLE IF NOT EXISTS {table} ({columns})")
        self.conn.commit()

    def _insert_sqlite(self, table: str, row: dict[str, Any]) -> None:
        fields = TABLE_FIELDS[table]
        placeholders = ", ".join("?" for _ in fields)
        columns = ", ".join(f'"{field}"' for field in fields)
        values = [_sqlite_value(row.get(field)) for field in fields]
        self.conn.execute(f"INSERT INTO {table} ({columns}) VALUES ({placeholders})", values)


def _sqlite_value(value: Any) -> Any:
    if value is None:
        return None
    return str(value)
