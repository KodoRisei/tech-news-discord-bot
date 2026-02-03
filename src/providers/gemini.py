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
        
        # google-genai SDK はモデル名に "models/" プレフィックスが必要
        if not self.model.startswith("models/"):
            self.model = f"models/{self.model}"

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
                error_str = str(exc)
                
                # 404エラー = モデル名が間違っている（リトライ不要）
                if "404" in error_str:
                    logger.error(f"[Gemini] モデルが見つかりません: {self.model}")
                    logger.error(f"  エラー詳細: {exc}")
                    return ""
                
                # 429エラー = レート制限（リトライ）
                if "429" in error_str or "rate" in error_str.lower() or "quota" in error_str.lower():
                    wait = min(_RETRY_DELAY_BASE_SEC * (2 ** (attempt - 1)), _RETRY_DELAY_MAX_SEC)
                    logger.warning(
                        f"[Gemini] レートリミット (attempt {attempt}/{_RETRY_MAX}) "
                        f"— {wait:.0f}s 待機中..."
                    )
                    time.sleep(wait)
                    continue

                # その他のエラー
                logger.error(f"[Gemini] API エラー: {exc}")
                return ""

        logger.error("[Gemini] 最大再試行超過で失敗")
        return ""
