# =============================================================
# src/providers/base.py
# 全プロバイダーが実装する抽象基底クラス
# =============================================================
from __future__ import annotations

from abc import ABC, abstractmethod


class BaseLLMProvider(ABC):
    """
    LLM プロバイダーの共通インターフェース

    新規プロバイダーを追加する場合はこのクラスを継承し、
    `call()` メソッドを実装してください。
    コンストラクタでは settings.yaml の `ai` セクション全体を受け取ります。
    """

    def __init__(self, ai_config: dict) -> None:
        self.model: str = ai_config.get("model", "")
        self.max_tokens: int = ai_config.get("max_tokens", 500)
        self.ai_config = ai_config  # 設定の丸ごと参照も可能

    @abstractmethod
    def call(self, prompt: str) -> str:
        """
        プロンプトを送信し、生成されたテキストを返す

        Args:
            prompt: 送信するプロンプト文字列

        Returns:
            生成されたテキスト。失敗した場合は空文字列。
        """
        ...
