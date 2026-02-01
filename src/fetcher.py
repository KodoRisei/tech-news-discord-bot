# =============================================================
# src/fetcher.py
# RSS ソースから記事を収集するモジュール
# =============================================================
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import feedparser

logger = logging.getLogger(__name__)


@dataclass
class Article:
    """収集した記事を表すデータクラス"""

    title: str
    url: str
    source_id: str
    source_name: str
    description: str = ""
    published: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    summary: str = ""  # AI 要約結果を後で格納
    matched_keywords: list[str] = field(default_factory=list)

    @property
    def published_str(self) -> str:
        """JST での公開日時文字列を返す"""
        from datetime import timedelta

        jst = timezone(timedelta(hours=9))
        return self.published.astimezone(jst).strftime("%m/%d %H:%M")


def _parse_date(entry: Any) -> datetime:
    """feedparser のエントリーから日時をパースする"""
    time_struct = entry.get("published_parsed") or entry.get("updated_parsed")
    if time_struct:
        return datetime(*time_struct[:6], tzinfo=timezone.utc)
    return datetime.now(timezone.utc)


def fetch_articles(source: dict[str, Any]) -> list[Article]:
    """
    単一ソース設定から記事を収集する

    Args:
        source: settings.yaml の sources エントリー

    Returns:
        Article のリスト
    """
    source_id: str = source["id"]
    source_name: str = source["name"]
    url: str = source["url"]
    max_items: int = source.get("max_items", 20)

    logger.info(f"[{source_name}] RSS を取得中: {url}")

    try:
        feed = feedparser.parse(url)
    except Exception as exc:
        logger.error(f"[{source_name}] RSS 取得に失敗: {exc}")
        return []

    if feed.bozo and not feed.entries:
        logger.warning(f"[{source_name}] RSS パースに問題: {feed.bozo_exception}")
        return []

    articles: list[Article] = []
    for entry in feed.entries[:max_items]:
        title = entry.get("title", "").strip()
        link = entry.get("link", "").strip()
        desc = entry.get("summary", "").strip()
        published = _parse_date(entry)

        if not title or not link:
            continue

        articles.append(
            Article(
                title=title,
                url=link,
                source_id=source_id,
                source_name=source_name,
                description=desc,
                published=published,
            )
        )

    logger.info(f"[{source_name}] {len(articles)} 件の記事を取得")
    return articles


def fetch_all(sources: list[dict[str, Any]]) -> list[Article]:
    """
    全ソースから記事を収集する

    Args:
        sources: settings.yaml の sources リスト

    Returns:
        全ソースの Article リスト
    """
    all_articles: list[Article] = []
    for source in sources:
        articles = fetch_articles(source)
        all_articles.extend(articles)
    logger.info(f"合計 {len(all_articles)} 件の記事を収集completed")
    return all_articles
