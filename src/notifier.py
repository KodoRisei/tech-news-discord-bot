# =============================================================
# src/notifier.py
# Discord Webhook via embeds で通知を送信するモジュール
# =============================================================
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone

import requests

from src.fetcher import Article

logger = logging.getLogger(__name__)

# ソース別の絵文字マッピング
_SOURCE_EMOJI: dict[str, str] = {
    "aws_whatsnew": "☁️",
    "aws_blog": "📖",
    "databricks_blog": "🔥",
    "databricks_release_notes": "📋",
    "dev_to": "💻",
    "medium_engineering": "📰",
}

# Discord embed の色コード（ソース別）
_SOURCE_COLOR: dict[str, int] = {
    "aws_whatsnew": 0xFF9900,       # AWS オレンジ
    "aws_blog": 0xFFD100,           # AWS 黄
    "databricks_blog": 0xE8192C,    # Databricks 赤
    "databricks_release_notes": 0xC41230,
    "dev_to": 0x0F0F0F,            # dev.to 黒
    "medium_engineering": 0x02B875,  # Medium グリーン
}

_DEFAULT_COLOR = 0x5865F2  # Discord Blurple


def _get_jst_now() -> datetime:
    """現在時刻を JST で返す"""
    return datetime.now(timezone(timedelta(hours=9)))


def _build_embeds(articles: list[Article], username: str) -> list[dict]:
    """
    記事リストから Discord embed オブジェクトのリストを構築する

    Discord は1メッセージあたり最大10 embed まで。
    11件以上の場合は複数メッセージに分割する必要がある。
    """
    jst_now = _get_jst_now()
    date_str = jst_now.strftime("%Y年%m月%d日")

    # ---- ヘッダー embed ----
    header_embed = {
        "title": f"📰 毎朝テックニュース ― {date_str}",
        "description": (
            f"キーワード検索で収集した **{len(articles)} 件** の記事です。\n"
            "AIによる要約付きで確認できます。"
        ),
        "color": _DEFAULT_COLOR,
        "timestamp": jst_now.isoformat(),
    }

    embeds: list[dict] = [header_embed]

    for article in articles:
        emoji = _SOURCE_EMOJI.get(article.source_id, "📄")
        color = _SOURCE_COLOR.get(article.source_id, _DEFAULT_COLOR)

        # キーワードタグ
        kw_str = " ".join(f"`{kw}`" for kw in article.matched_keywords) if article.matched_keywords else ""

        # 説明欄の組成
        desc_parts: list[str] = []
        if kw_str:
            desc_parts.append(f"🏷️ {kw_str}")
        if article.summary:
            desc_parts.append(f"🤖 **AI要約:** {article.summary}")

        description = "\n".join(desc_parts) if desc_parts else "説明なし"

        embed = {
            "title": f"{emoji} {article.title}",
            "url": article.url,
            "description": description,
            "color": color,
            "footer": {
                "text": f"{article.source_name}  •  {article.published_str}",
            },
        }
        embeds.append(embed)

    return embeds


def send_notification(
    articles: list[Article],
    webhook_url: str,
    username: str = "📰 Tech News Bot",
    avatar_url: str = "",
    dry_run: bool = False,
) -> bool:
    """
    Discord Webhook で通知を送信する

    Discord embed は1メッセージ最大10件なので、
    超える場合は複数リクエストに分割する。

    Args:
        articles: 通知する記事リスト
        webhook_url: Discord Webhook URL
        username: ボット表示名
        avatar_url: アバターURL
        dry_run: Trueの場合は実際には送信しない

    Returns:
        送信成功ならTrue
    """
    if not articles:
        logger.warning("通知する記事がありません")
        return False

    all_embeds = _build_embeds(articles, username)

    if dry_run:
        logger.info("=== DRY RUN: Discord には送信しません ===")
        for embed in all_embeds:
            logger.info(f"  [EMBED] {embed.get('title', 'N/A')}")
        return True

    if not webhook_url:
        raise EnvironmentError("DISCORD_WEBHOOK_URL が設定されていません")

    # 1メッセージ最大10 embed で分割して送信
    chunk_size = 10
    success = True

    for i in range(0, len(all_embeds), chunk_size):
        chunk = all_embeds[i : i + chunk_size]

        payload: dict = {
            "username": username,
            "embeds": chunk,
        }
        if avatar_url:
            payload["avatar_url"] = avatar_url

        try:
            response = requests.post(webhook_url, json=payload, timeout=10)
            response.raise_for_status()
            logger.info(f"Discord 通知送信成功 (embed {i + 1}～{i + len(chunk)})")
        except requests.RequestException as exc:
            logger.error(f"Discord 通知送信に失敗: {exc}")
            success = False

    return success
