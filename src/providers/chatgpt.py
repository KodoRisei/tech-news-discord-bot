# =============================================================
# src/providers/chatgpt.py
# OpenAI ChatGPT プロバイダー
# =============================================================
from __future__ import annotations

import logging
import os
import time

from openai import OpenAI, RateLimitError, APIError

from src.providers.base import BaseLLMProvider

logger = logging.getLogger(__name__)

_RETRY_MAX = 3
_RETRY_DELAY_SEC = 2.0


class ChatGPTProvider(BaseLLMProvider):
    """OpenAI ChatGPT API を使用するプロバイダー"""

    def __init__(self, ai_config: dict) -> None:
        super().__init__(ai_config)
        if not self.model:
            self.model = "gpt-4o-mini"

        api_key = os.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            raise EnvironmentError(
                "OPENAI_API_KEY が設定されていません。"
                "GitHub Secrets または環境変数で設定してください。"
            )
        self.client = OpenAI(api_key=api_key)
        logger.info(f"[ChatGPT] プロバイダー初期化 | model={self.model}")

    def call(self, prompt: str) -> str:
        for attempt in range(1, _RETRY_MAX + 1):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    messages=[{"role": "user", "content": prompt}],
                )
                return response.choices[0].message.content.strip()

            except RateLimitError:
                logger.warning(f"[ChatGPT] レートリミット (attempt {attempt}/{_RETRY_MAX})")
                time.sleep(_RETRY_DELAY_SEC * attempt)

            except APIError as exc:
                logger.error(f"[ChatGPT] API エラー: {exc}")
                return ""

        logger.error("[ChatGPT] 最大再試行超過で失敗")
        return ""
