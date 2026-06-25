from __future__ import annotations

from dataclasses import dataclass

from src.models import OptionTick, StockTick, TradeSignal


@dataclass(slots=True)
class LiveRow:
    signal_id: str
    symbol: str
    stock_last: float | None
    option_symbol: str
    role: str
    bid: float | None
    ask: float | None
    mid: float | None
    spread_pct: float | None
    compression_pct: float | None
    rebound_pct: float | None
    valid: bool
    score_hint: str


class LiveConsole:
    def __init__(self, quiet: bool = False) -> None:
        self.quiet = quiet
        try:
            from rich.console import Console
            from rich.table import Table
        except ImportError:  # pragma: no cover
            self.console = None
            self.table_cls = None
        else:
            self.console = Console()
            self.table_cls = Table

    def status(self, message: str) -> None:
        if not self.quiet:
            print(message)

    def render(
        self,
        signals: list[TradeSignal],
        stock_ticks: dict[str, StockTick],
        option_ticks: dict[str, OptionTick],
    ) -> None:
        if self.quiet:
            return
        rows = []
        for key, tick in option_ticks.items():
            stock = stock_ticks.get(tick.signal_id)
            rows.append(
                LiveRow(
                    signal_id=tick.signal_id,
                    symbol=tick.underlying_symbol,
                    stock_last=stock.stock_last if stock else None,
                    option_symbol=tick.option_symbol,
                    role=tick.contract_role.value,
                    bid=tick.bid,
                    ask=tick.ask,
                    mid=tick.mid,
                    spread_pct=tick.spread_pct,
                    compression_pct=tick.compression_from_initial_pct,
                    rebound_pct=tick.rebound_from_low_pct,
                    valid=tick.quote_is_valid,
                    score_hint="WATCH" if tick.quote_is_valid and (tick.rebound_from_low_pct or 0) >= 20 else "COLLECTING",
                )
            )
        if self.console is None or self.table_cls is None:
            self._plain(rows[:12])
            return
        table = self.table_cls(title="Options Signal Data Collector")
        for column in ["Symbol", "Stock", "Contract", "Role", "Bid", "Ask", "Mid", "Spread%", "Comp%", "Rebound%", "Valid", "Status"]:
            table.add_column(column)
        for row in rows[:16]:
            table.add_row(
                row.symbol,
                _fmt(row.stock_last),
                row.option_symbol,
                row.role,
                _fmt(row.bid),
                _fmt(row.ask),
                _fmt(row.mid),
                _fmt(row.spread_pct),
                _fmt(row.compression_pct),
                _fmt(row.rebound_pct),
                "yes" if row.valid else "no",
                row.score_hint,
            )
        self.console.print(table)

    def _plain(self, rows: list[LiveRow]) -> None:
        for row in rows:
            print(
                f"{row.symbol} {row.option_symbol} {row.role} "
                f"bid={_fmt(row.bid)} ask={_fmt(row.ask)} mid={_fmt(row.mid)} "
                f"spread={_fmt(row.spread_pct)} valid={row.valid}"
            )


def _fmt(value: float | None) -> str:
    return "" if value is None else f"{value:.2f}"
