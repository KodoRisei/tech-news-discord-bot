# =============================================================
# src/providers/gemini.py
# Google Gemini プロバイダー
# =============================================================
from __future__ import annotations

import logging
import os
import time

import google.generativeai as genai

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
        
        # google-generativeai SDK の設定
        genai.configure(api_key=api_key)
        self.model_instance = genai.GenerativeModel(self.model)
        
        logger.info(f"[Gemini] プロバイダー初期化 | model={self.model}")

    def call(self, prompt: str) -> str:
        for attempt in range(1, _RETRY_MAX + 1):
            try:
                # GenerationConfig で max_output_tokens を設定
                generation_config = genai.types.GenerationConfig(
                    max_output_tokens=self.max_tokens,
                )
                
                response = self.model_instance.generate_content(
                    prompt,
                    generation_config=generation_config,
                )
                return response.text.strip()

            except Exception as exc:
                error_str = str(exc)
                
                # 404エラー = モデル名が間違っている（リトライ不要）
                if "404" in error_str or "not found" in error_str.lower():
                    logger.error(f"[Gemini] モデルが見つかりません: {self.model}")
                    logger.error(
                        f"  利用可能なモデル: gemini-1.5-flash, gemini-1.5-pro, gemini-pro\n"
                        f"  詳細: https://ai.google.dev/gemini-api/docs/models/gemini"
                    )
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
