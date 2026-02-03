# =============================================================
# src/providers/gemini.py
# Google Gemini プロバイダー
# =============================================================
from __future__ import annotations

import logging
import os
import time

from google.genai import Client as GenAIClient
from google.genai import types as genai_types

from src.providers.base import BaseLLMProvider

logger = logging.getLogger(__name__)

_RETRY_MAX = 5
_RETRY_DELAY_BASE_SEC = 5.0   # 指数バックオフの基値
_RETRY_DELAY_MAX_SEC = 30.0   # バックオフの上限


class GeminiProvider(BaseLLMProvider):
    """Google Gemini API を使用するプロバイダー"""

    def __init__(self, ai_config: dict) -> None:
        super().__init__(ai_config)
        if not self.model:
            self.model = "gemini-1.5-flash"

        api_key = os.environ.get("GEMINI_API_KEY", "")
        if not api_key:
            raise EnvironmentError(
                "GEMINI_API_KEY が設定されていません。"
                "GitHub Secrets または環境変数で設定してください。"
            )
        self.client = GenAIClient(api_key=api_key)
        logger.info(f"[Gemini] プロバイダー初期化 | model={self.model}")

    def call(self, prompt: str) -> str:
        for attempt in range(1, _RETRY_MAX + 1):
            try:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=genai_types.GenerateContentConfig(
                        max_output_tokens=self.max_tokens,
                    ),
                )
                return response.text.strip()

            except Exception as exc:
                # Gemini SDK は共通の RateLimitError を持たないため、
                # メッセージで判定して再試行する
                if "429" in str(exc) or "rate" in str(exc).lower():
                    # 指数バックオフ: 5s → 10s → 20s → 30s → 30s
                    wait = min(_RETRY_DELAY_BASE_SEC * (2 ** (attempt - 1)), _RETRY_DELAY_MAX_SEC)
                    logger.warning(
                        f"[Gemini] レートリミット (attempt {attempt}/{_RETRY_MAX}) "
                        f"— {wait:.0f}s 待機中..."
                    )
                    time.sleep(wait)
                    continue

                logger.error(f"[Gemini] API エラー: {exc}")
                return ""

        logger.error("[Gemini] 最大再試行超過で失敗")
        return ""
