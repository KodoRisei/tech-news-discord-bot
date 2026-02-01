# =============================================================
# src/main.py
# エントリポイント: 収集 → フィルタリング → AI要約 → Discord通知
# =============================================================
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

import yaml

from src.fetcher import fetch_all
from src.filter import filter_articles
from src.notifier import send_notification
from src.summarizer import summarize_all

# ---- ログ設定 ----
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---- プロジェクトルートの特定 ----
# `python -m src.main` で実行されるため、プロジェクトルートは CWD
PROJECT_ROOT = Path.cwd()
SETTINGS_PATH = PROJECT_ROOT / "config" / "settings.yaml"


def load_settings() -> dict:
    """settings.yaml を読み込む"""
    if not SETTINGS_PATH.exists():
        logger.error(f"設定ファイルが見つかりません: {SETTINGS_PATH}")
        sys.exit(1)
    with open(SETTINGS_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def main() -> None:
    """メインパイプラインの実行"""
    settings = load_settings()

    # ---- 環境変数の読み込み ----
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL", "")
    dry_run = os.environ.get("DRY_RUN", "false").lower() == "true"

    keywords: list[str] = settings.get("keywords", [])
    sources: list[dict] = settings.get("sources", [])
    discord_cfg: dict = settings.get("discord", {})
    ai_cfg: dict = settings.get("ai", {})
    max_articles: int = discord_cfg.get("max_articles", 10)

    logger.info("=" * 60)
    logger.info("Tech News Discord Bot 開始")
    logger.info(f"  キーワード: {keywords}")
    logger.info(f"  ソース数: {len(sources)}")
    logger.info(f"  AI要約: {'有効' if ai_cfg.get('enabled') else '無効'}")
    logger.info(f"  DRY RUN: {dry_run}")
    logger.info("=" * 60)

    # ------------------------------------------------------------
    # Step 1: RSS から記事を収集
    # ------------------------------------------------------------
    logger.info("\n[Step 1] 記事収集を開始...")
    all_articles = fetch_all(sources)

    if not all_articles:
        logger.warning("記事が収集できませんでした。終了。")
        return

    # ------------------------------------------------------------
    # Step 2: キーワードによるフィルタリング・スコアリング
    # ------------------------------------------------------------
    logger.info("\n[Step 2] キーワードフィルタリング...")
    filtered = filter_articles(all_articles, keywords, max_articles)

    if not filtered:
        logger.warning("キーワードにマッチする記事がありませんでした。終了。")
        # マッチ無しでも通知する場合はコメント出しにする
        return

    # ------------------------------------------------------------
    # Step 3: AI による要約（有効な場合のみ）
    # ------------------------------------------------------------
    if ai_cfg.get("enabled", False):
        logger.info("\n[Step 3] AI 要約を開始...")
        filtered = summarize_all(filtered, ai_cfg)
    else:
        logger.info("\n[Step 3] AI 要約はスキップ")

    # ------------------------------------------------------------
    # Step 4: Discord 通知
    # ------------------------------------------------------------
    logger.info("\n[Step 4] Discord 通知を送信...")
    success = send_notification(
        articles=filtered,
        webhook_url=webhook_url,
        username=discord_cfg.get("username", "📰 Tech News Bot"),
        avatar_url=discord_cfg.get("avatar_url", ""),
        dry_run=dry_run,
    )

    if success:
        logger.info("\n✅ 完了: Discord に通知を送信しました")
    else:
        logger.error("\n❌ 通知の送信に失敗しました")
        sys.exit(1)


if __name__ == "__main__":
    main()
