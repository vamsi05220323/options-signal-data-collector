from __future__ import annotations

from datetime import datetime, timedelta

from src.models import NewsArticle, TradeSignal
from src.news_providers.base import BaseNewsProvider, make_article


class MockNewsProvider(BaseNewsProvider):
    name = "mock"

    def fetch(self, signal: TradeSignal, collected_at: datetime) -> list[NewsArticle]:
        published = signal.timestamp_local - timedelta(hours=3)
        return [
            make_article(
                signal=signal,
                provider=self.name,
                collected_at=collected_at,
                published_at=published,
                source="MockWire",
                headline=f"{signal.symbol} sees unusual options interest without confirmed company catalyst",
                summary="Synthetic article for local testing; do not use as live market context.",
                sentiment_label="neutral",
                sentiment_score=0.02,
                relevance_score=0.7,
            )
        ]
