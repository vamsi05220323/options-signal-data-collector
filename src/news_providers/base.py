from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from src.models import NewsArticle, NewsSummary, OptionType, TradeSignal


CATALYST_TYPES = [
    "EARNINGS",
    "GUIDANCE",
    "ANALYST_UPGRADE",
    "ANALYST_DOWNGRADE",
    "FDA_CLINICAL",
    "OFFERING_DILUTION",
    "M_AND_A",
    "PARTNERSHIP",
    "LEGAL_REGULATORY",
    "MANAGEMENT_CHANGE",
    "SHORT_REPORT",
    "PRODUCT_LAUNCH",
    "MACRO_SECTOR",
    "UNKNOWN",
]


class NewsProviderError(RuntimeError):
    """Raised when a news provider is unavailable."""


class BaseNewsProvider(ABC):
    name: str

    @abstractmethod
    def fetch(self, signal: TradeSignal, collected_at: datetime) -> list[NewsArticle]:
        raise NotImplementedError


def classify_catalyst(text: str) -> str:
    lower = text.lower()
    if any(word in lower for word in ["earnings", "eps", "revenue", "profit"]):
        return "EARNINGS"
    if any(word in lower for word in ["guidance", "outlook", "forecast"]):
        return "GUIDANCE"
    if any(word in lower for word in ["upgrade", "raises price target", "boosts target"]):
        return "ANALYST_UPGRADE"
    if any(word in lower for word in ["downgrade", "cuts price target", "lowers target"]):
        return "ANALYST_DOWNGRADE"
    if any(word in lower for word in ["fda", "clinical", "trial", "phase 2", "phase 3"]):
        return "FDA_CLINICAL"
    if any(word in lower for word in ["offering", "dilution", "secondary"]):
        return "OFFERING_DILUTION"
    if any(word in lower for word in ["acquire", "merger", "buyout", "m&a", "takeover"]):
        return "M_AND_A"
    if any(word in lower for word in ["partnership", "collaboration", "alliance"]):
        return "PARTNERSHIP"
    if any(word in lower for word in ["lawsuit", "sec", "regulatory", "investigation"]):
        return "LEGAL_REGULATORY"
    if any(word in lower for word in ["ceo", "cfo", "management", "resigns", "appoints"]):
        return "MANAGEMENT_CHANGE"
    if any(word in lower for word in ["short report", "short seller"]):
        return "SHORT_REPORT"
    if any(word in lower for word in ["launch", "product", "commercializes"]):
        return "PRODUCT_LAUNCH"
    if any(word in lower for word in ["sector", "macro", "rates", "fed", "inflation"]):
        return "MACRO_SECTOR"
    return "UNKNOWN"


def summarize_news(signal: TradeSignal, provider_name: str, articles: list[NewsArticle]) -> NewsSummary:
    within_24h = [article for article in articles if article.is_within_24h]
    within_7d = [article for article in articles if article.is_within_7d]
    positives = [article for article in within_24h if article.sentiment_score is not None and article.sentiment_score > 0.15]
    negatives = [article for article in within_24h if article.sentiment_score is not None and article.sentiment_score < -0.15]
    neutrals = [article for article in within_24h if article not in positives and article not in negatives]
    latest_age = min(
        [article.article_age_minutes_at_signal for article in articles if article.article_age_minutes_at_signal is not None],
        default=None,
    )
    sentiment_values = [article.sentiment_score for article in within_24h if article.sentiment_score is not None]
    relevance_values = [article.relevance_score for article in within_24h if article.relevance_score is not None]
    catalyst = next((article.catalyst_type for article in within_24h if article.catalyst_type != "UNKNOWN"), "UNKNOWN")
    bias = infer_news_bias(signal.direction, len(positives), len(negatives), len(within_24h))
    score = score_news_context(bias)
    provider_key = provider_name.strip().lower()
    affects_score = provider_key in {"alpha_vantage", "finnhub"}
    source_confidence = "EXTERNAL" if affects_score else ("MOCK" if provider_key == "mock" else "UNAVAILABLE")
    warning = ""
    if signal.direction is OptionType.CALL and bias == "POSITIVE_FOR_CALL":
        warning = "positive_recent_news_supports_call_signal"
    elif signal.direction is OptionType.PUT and bias == "NEGATIVE_FOR_CALL":
        warning = "negative_recent_news_supports_put_signal"
    top_sources = "; ".join(dict.fromkeys(article.source for article in within_24h if article.source))
    top_headlines = " | ".join(article.headline for article in within_24h[:3])
    return NewsSummary(
        signal_id=signal.signal_id,
        symbol=signal.symbol,
        signal_timestamp_local=signal.timestamp_local,
        news_provider=provider_name,
        news_count_24h=len(within_24h),
        news_count_7d=len(within_7d),
        latest_news_age_minutes=latest_age,
        positive_news_count_24h=len(positives),
        negative_news_count_24h=len(negatives),
        neutral_news_count_24h=len(neutrals),
        avg_sentiment_24h=sum(sentiment_values) / len(sentiment_values) if sentiment_values else None,
        avg_relevance_24h=sum(relevance_values) / len(relevance_values) if relevance_values else None,
        top_sources_24h=top_sources,
        top_headlines_24h=top_headlines,
        catalyst_detected=catalyst != "UNKNOWN",
        catalyst_type=catalyst,
        news_bias=bias,
        news_score=score,
        news_score_effective=score if affects_score else None,
        news_source_confidence=source_confidence,
        news_affects_score=affects_score,
        news_skip_warning=warning,
        news_notes="News is context only; bid/ask execution data remains primary.",
    )


def unavailable_news_summary(signal: TradeSignal, notes: str) -> NewsSummary:
    return NewsSummary(
        signal_id=signal.signal_id,
        symbol=signal.symbol,
        signal_timestamp_local=signal.timestamp_local,
        news_provider="NEWS_UNAVAILABLE",
        news_count_24h=0,
        news_count_7d=0,
        latest_news_age_minutes=None,
        positive_news_count_24h=0,
        negative_news_count_24h=0,
        neutral_news_count_24h=0,
        avg_sentiment_24h=None,
        avg_relevance_24h=None,
        top_sources_24h="",
        top_headlines_24h="",
        catalyst_detected=False,
        catalyst_type="UNKNOWN",
        news_bias="NO_NEWS",
        news_score=0.0,
        news_score_effective=None,
        news_source_confidence="UNAVAILABLE",
        news_affects_score=False,
        news_skip_warning="news_unavailable",
        news_notes=notes,
    )


def infer_news_bias(direction: OptionType, positive_count: int, negative_count: int, total_count: int) -> str:
    if total_count == 0:
        return "NO_NEWS"
    if positive_count > negative_count and positive_count >= 1:
        return "POSITIVE_FOR_CALL"
    if negative_count > positive_count and negative_count >= 1:
        return "NEGATIVE_FOR_CALL"
    if positive_count or negative_count:
        return "MIXED"
    return "UNKNOWN"


def score_news_context(news_bias: str) -> float:
    if news_bias == "NEGATIVE_FOR_CALL":
        return 75.0
    if news_bias == "NO_NEWS":
        return 58.0
    if news_bias == "MIXED":
        return 50.0
    if news_bias == "POSITIVE_FOR_CALL":
        return 35.0
    return 45.0


def make_article(
    *,
    signal: TradeSignal,
    provider: str,
    collected_at: datetime,
    published_at: datetime | None,
    source: str,
    headline: str,
    summary: str = "",
    url: str = "",
    related_tickers: str = "",
    sentiment_label: str = "neutral",
    sentiment_score: float | None = 0.0,
    relevance_score: float | None = 0.5,
) -> NewsArticle:
    age_minutes = None
    is_within_24h = False
    is_within_7d = False
    if published_at is not None:
        age_minutes = (signal.timestamp_local - published_at.astimezone(signal.timestamp_local.tzinfo)).total_seconds() / 60.0
        is_within_24h = 0 <= age_minutes <= 24 * 60
        is_within_7d = 0 <= age_minutes <= 7 * 24 * 60
    catalyst = classify_catalyst(f"{headline} {summary}")
    return NewsArticle(
        timestamp_collected=collected_at,
        signal_id=signal.signal_id,
        symbol=signal.symbol,
        provider=provider,
        article_published_at=published_at,
        article_age_minutes_at_signal=age_minutes,
        source=source,
        headline=headline,
        summary=summary,
        url=url,
        related_tickers=related_tickers or signal.symbol,
        sentiment_label=sentiment_label,
        sentiment_score=sentiment_score,
        relevance_score=relevance_score,
        catalyst_type=catalyst,
        is_within_24h=is_within_24h,
        is_within_7d=is_within_7d,
    )
