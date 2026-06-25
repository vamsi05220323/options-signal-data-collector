from __future__ import annotations

from datetime import datetime

from src.models import NewsArticle, TradeSignal
from src.news_providers.base import BaseNewsProvider, NewsProviderError


class YahooNewsProvider(BaseNewsProvider):
    name = "yahoo_unofficial"

    def fetch(self, signal: TradeSignal, collected_at: datetime) -> list[NewsArticle]:
        raise NewsProviderError("Yahoo/yfinance news is an unofficial fallback and is not enabled by default.")
