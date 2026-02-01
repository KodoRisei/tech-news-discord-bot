# =============================================================
# src/providers/claude.py
# Anthropic Claude プロバイダー
# =============================================================
from __future__ import annotations

import logging
import os
import time

import anthropic

from src.providers.base import BaseLLMProvider

logger = logging.getLogger(__name__)

_RETRY_MAX = 3
_RETRY_DELAY_SEC = 2.0


class ClaudeProvider(BaseLLMProvider):
    """Anthropic Claude API を使用するプロバイダー"""

    def __init__(self, ai_config: dict) -> None:
        super().__init__(ai_config)
        # デフォルトモデル
        if not self.model:
            self.model = "claude-sonnet-4-20250514"

        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            raise EnvironmentError(
                "ANTHROPIC_API_KEY が設定されていません。"
                "GitHub Secrets または環境変数で設定してください。"
            )
        self.client = anthropic.Anthropic(api_key=api_key)
        logger.info(f"[Claude] プロバイダー初期化 | model={self.model}")

    def call(self, prompt: str) -> str:
        for attempt in range(1, _RETRY_MAX + 1):
            try:
                message = self.client.messages.create(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    messages=[{"role": "user", "content": prompt}],
                )
                return message.content[0].text.strip()

            except anthropic.RateLimitError:
                logger.warning(f"[Claude] レートリミット (attempt {attempt}/{_RETRY_MAX})")
                time.sleep(_RETRY_DELAY_SEC * attempt)

            except anthropic.APIError as exc:
                logger.error(f"[Claude] API エラー: {exc}")
                return ""

        logger.error("[Claude] 最大再試行超過で失敗")
        return ""
