# =============================================================
# src/summarizer.py
# プロバイダー非依存の AI 要約モジュール
# =============================================================
from __future__ import annotations

import logging
import re
import time

from src.fetcher import Article
from src.providers import get_provider
from src.providers.base import BaseLLMProvider

logger = logging.getLogger(__name__)


def _clean_html(text: str) -> str:
    """HTML タグを除去する"""
    return re.sub(r"<[^>]+>", "", text).strip()


def _build_prompt(article: Article, template: str) -> str:
    """プロンプトテンプレートに記事情報を埋め込む"""
    desc = _clean_html(article.description) or "説明なし"
    return template.format(title=article.title, description=desc)


def summarize_article(article: Article, provider: BaseLLMProvider, prompt_template: str) -> str:
    """
    単一記事の AI 要約を生成する

    Args:
        article: 要約対象の記事
        provider: LLM プロバイダーインスタンス
        prompt_template: プロンプトテンプレート

    Returns:
        要約文字列。失敗した場合は空文字列。
    """
    prompt = _build_prompt(article, prompt_template)
    result = provider.call(prompt)

    if result:
        logger.info(f"  要約成功: {article.title[:50]}...")
    else:
        logger.warning(f"  要約失敗: {article.title[:50]}...")

    return result


def summarize_all(articles: list[Article], ai_config: dict) -> list[Article]:
    """
    全記事に AI 要約を付与する

    ai_config から プロバイダーを動的に生成し、全記事に適用する。

    Args:
        articles: 要約対象の記事リスト
        ai_config: settings.yaml の `ai` セクション全体

    Returns:
        summary フィールドが埋まった Article リスト
    """
    provider = get_provider(ai_config)
    prompt_template = ai_config.get("summary_prompt", "")

    # プロバイダー別の記事間隔 (秒)
    # Gemini Free tier は約1分に2リクエスト制限なので長めに設定
    _INTER_CALL_DELAY: dict[str, float] = {
        "claude": 0.5,
        "chatgpt": 0.5,
        "gemini": 5.0,
    }
    provider_name = ai_config.get("provider", "claude").lower()
    delay = _INTER_CALL_DELAY.get(provider_name, 1.0)

    logger.info(f"AI 要約を開始 ({len(articles)} 件) | 記事間隔: {delay}s ...")

    for article in articles:
        article.summary = summarize_article(article, provider, prompt_template)
        time.sleep(delay)

    return articles
