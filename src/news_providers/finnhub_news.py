from __future__ import annotations

from datetime import datetime, timedelta, timezone

import requests

from src.models import NewsArticle, TradeSignal
from src.news_providers.base import BaseNewsProvider, NewsProviderError, make_article


class FinnhubNewsProvider(BaseNewsProvider):
    name = "finnhub"

    def __init__(self, api_key: str, max_articles: int = 50) -> None:
        self.api_key = api_key
        self.max_articles = max_articles

    def fetch(self, signal: TradeSignal, collected_at: datetime) -> list[NewsArticle]:
        if not self.api_key:
            raise NewsProviderError("FINNHUB_API_KEY is not configured.")
        signal_utc = signal.timestamp_local.astimezone(timezone.utc)
        start = signal_utc - timedelta(days=7)
        params = {
            "symbol": signal.symbol,
            "from": start.date().isoformat(),
            "to": signal_utc.date().isoformat(),
            "token": self.api_key,
        }
        response = requests.get("https://finnhub.io/api/v1/company-news", params=params, timeout=10)
        response.raise_for_status()
        articles: list[NewsArticle] = []
        for item in response.json()[: self.max_articles]:
            published = datetime.fromtimestamp(item.get("datetime", 0), tz=timezone.utc) if item.get("datetime") else None
            articles.append(
                make_article(
                    signal=signal,
                    provider=self.name,
                    collected_at=collected_at,
                    published_at=published,
                    source=str(item.get("source", "")),
                    headline=str(item.get("headline", "")),
                    summary=str(item.get("summary", "")),
                    url=str(item.get("url", "")),
                    sentiment_label="unknown",
                    sentiment_score=None,
                    relevance_score=None,
                )
            )
        return articles
