# =============================================================
# src/filter.py
# キーワード検索・スコアリングによる記事フィルタリング
# =============================================================
from __future__ import annotations

import logging
import re
from collections import Counter

from src.fetcher import Article

logger = logging.getLogger(__name__)


def _normalize(text: str) -> str:
    """テキストを正規化する（小文字化・記号除去）"""
    return re.sub(r"[^\w\s]", "", text.lower())


def _count_keyword_hits(text: str, keywords: list[str]) -> Counter[str]:
    """
    テキスト中のキーワード出現回数をカウントする

    マッチは大文字小文字を区別しない。
    キーワードが複数語の場合もそのまま検索できる。
    """
    normalized = _normalize(text)
    hits: Counter[str] = Counter()
    for kw in keywords:
        pattern = re.escape(_normalize(kw))
        count = len(re.findall(pattern, normalized))
        if count > 0:
            hits[kw] = count
    return hits


def score_article(article: Article, keywords: list[str]) -> tuple[float, list[str]]:
    """
    記事のキーワード適合スコアを計算する

    スコア計算の重み:
        1. キーワードマッチ:
           - タイトル中のキーワード: ×3
           - 説明文中のキーワード: ×1
        2. 新鮮度ブースト（ホットな話題を優先）:
           - 24時間以内: +5.0
           - 1週間以内: +2.0
           - 1ヶ月以内: +0.5
        3. ソースの信頼性:
           - 公式ソース（AWS, Databricks）: ×1.3
           - 大手メディア（Medium, dev.to）: ×1.0

    Returns:
        (スコア, マッチしたキーワードのリスト)
    """
    from datetime import datetime, timezone, timedelta

    title_hits = _count_keyword_hits(article.title, keywords)
    desc_hits = _count_keyword_hits(article.description, keywords)

    # ---- 1. キーワードマッチスコア ----
    keyword_score = 0.0
    matched: set[str] = set()

    for kw, count in title_hits.items():
        keyword_score += count * 3.0
        matched.add(kw)

    for kw, count in desc_hits.items():
        keyword_score += count * 1.0
        matched.add(kw)

    # ---- 2. 新鮮度ブースト（ホットな話題）----
    now = datetime.now(timezone.utc)
    age = now - article.published
    
    if age < timedelta(hours=24):
        recency_boost = 5.0  # 24時間以内の記事は大幅ブースト
    elif age < timedelta(days=7):
        recency_boost = 2.0  # 1週間以内
    elif age < timedelta(days=30):
        recency_boost = 0.5  # 1ヶ月以内
    else:
        recency_boost = 0.0

    # ---- 3. ソースの信頼性重み ----
    # 公式ソース（AWS, Databricks）は1.3倍、その他は1.0倍
    source_weight = 1.3 if article.source_id.startswith(('aws_', 'databricks_')) else 1.0

    # ---- 最終スコア ----
    final_score = (keyword_score + recency_boost) * source_weight

    return final_score, sorted(matched)


def filter_articles(
    articles: list[Article],
    keywords: list[str],
    max_articles: int = 10,
) -> list[Article]:
    """
    キーワードに基づいて記事をフィルタリングし、スコアの高い順にソートする

    Args:
        articles: 収集した全記事リスト
        keywords: 検索キーワード一覧
        max_articles: 返すArticle数の上限

    Returns:
        スコアソート済みの Article リスト
    """
    scored: list[tuple[float, Article]] = []

    for article in articles:
        score, matched_kws = score_article(article, keywords)
        if score > 0:
            article.matched_keywords = matched_kws
            scored.append((score, article))

    # スコア降順でソート（同スコアの場合は新しい順）
    # これによりホットな話題が最優先される
    scored.sort(key=lambda x: (x[0], x[1].published), reverse=True)

    selected = [article for _, article in scored[:max_articles]]

    logger.info(
        f"キーワードフィルタリング: {len(articles)} 件 → {len(selected)} 件に絞り込み"
    )
    if selected:
        logger.info(f"  トップ記事スコア: {scored[0][0]:.1f} | {selected[0].title[:60]}...")
    for art in selected:
        logger.debug(f"  [{art.source_name}] {art.title} | keywords={art.matched_keywords}")

    return selected
