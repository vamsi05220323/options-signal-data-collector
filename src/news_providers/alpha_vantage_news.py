from __future__ import annotations

from datetime import datetime, timedelta, timezone

import requests

from src.models import NewsArticle, TradeSignal
from src.news_providers.base import BaseNewsProvider, NewsProviderError, make_article


class AlphaVantageNewsProvider(BaseNewsProvider):
    name = "alpha_vantage"

    def __init__(self, api_key: str, max_articles: int = 50) -> None:
        self.api_key = api_key
        self.max_articles = max_articles

    def fetch(self, signal: TradeSignal, collected_at: datetime) -> list[NewsArticle]:
        if not self.api_key:
            raise NewsProviderError("ALPHA_VANTAGE_API_KEY is not configured.")
        signal_utc = signal.timestamp_local.astimezone(timezone.utc)
        start = signal_utc - timedelta(days=7)
        params = {
            "function": "NEWS_SENTIMENT",
            "tickers": signal.symbol,
            "time_from": start.strftime("%Y%m%dT%H%M"),
            "time_to": signal_utc.strftime("%Y%m%dT%H%M"),
            "sort": "LATEST",
            "limit": str(self.max_articles),
            "apikey": self.api_key,
        }
        response = requests.get("https://www.alphavantage.co/query", params=params, timeout=10)
        response.raise_for_status()
        payload = response.json()
        if "feed" not in payload:
            raise NewsProviderError(f"Alpha Vantage returned no feed: {payload}")
        articles: list[NewsArticle] = []
        for item in payload.get("feed", []):
            published = _parse_av_time(item.get("time_published"))
            sentiment_score = _optional_float(item.get("overall_sentiment_score"))
            ticker_sentiment = item.get("ticker_sentiment") or []
            relevance = None
            for ticker_row in ticker_sentiment:
                if str(ticker_row.get("ticker", "")).upper() == signal.symbol:
                    relevance = _optional_float(ticker_row.get("relevance_score"))
                    sentiment_score = _optional_float(ticker_row.get("ticker_sentiment_score")) or sentiment_score
                    break
            articles.append(
                make_article(
                    signal=signal,
                    provider=self.name,
                    collected_at=collected_at,
                    published_at=published,
                    source=str(item.get("source", "")),
                    headline=str(item.get("title", "")),
                    summary=str(item.get("summary", "")),
                    url=str(item.get("url", "")),
                    related_tickers=",".join(t.get("ticker", "") for t in ticker_sentiment),
                    sentiment_label=str(item.get("overall_sentiment_label", "unknown")),
                    sentiment_score=sentiment_score,
                    relevance_score=relevance,
                )
            )
        return articles


def _parse_av_time(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.strptime(value, "%Y%m%dT%H%M%S").replace(tzinfo=timezone.utc)


def _optional_float(value) -> float | None:
    if value in (None, ""):
        return None
    return float(value)
