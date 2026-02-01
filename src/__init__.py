# =============================================================
# src/providers/__init__.py
# プロバイダーのファクトリ。settings.yaml の provider で動的に選択する。
# =============================================================
from __future__ import annotations

import logging

from src.providers.base import BaseLLMProvider

logger = logging.getLogger(__name__)

# プロバイダー名 → クラスのマッピング
# 新規プロバイダーを追加した場合はここに登録してください。
_PROVIDER_REGISTRY: dict[str, str] = {
    "claude":  "src.providers.claude.ClaudeProvider",
    "chatgpt": "src.providers.chatgpt.ChatGPTProvider",
    "gemini":  "src.providers.gemini.GeminiProvider",
}


def get_provider(ai_config: dict) -> BaseLLMProvider:
    """
    settings.yaml の ai.provider から適切なプロバイダーインスタンスを返す

    Args:
        ai_config: settings.yaml の `ai` セクション全体

    Returns:
        BaseLLMProvider のサブクラスインスタンス

    Raises:
        ValueError: 未対応のプロバイダー名が指定された場合
        EnvironmentError: 必要な環境変数が未設定の場合
    """
    provider_name = ai_config.get("provider", "claude").lower().strip()

    if provider_name not in _PROVIDER_REGISTRY:
        available = ", ".join(_PROVIDER_REGISTRY.keys())
        raise ValueError(
            f"未対応のプロバイダー: '{provider_name}'\n"
            f"利用可能なプロバイダー: {available}"
        )

    # 文字列からクラスを動的にインポートする
    module_path, class_name = _PROVIDER_REGISTRY[provider_name].rsplit(".", 1)

    import importlib

    module = importlib.import_module(module_path)
    provider_class = getattr(module, class_name)

    logger.info(f"プロバイダー '{provider_name}' を選択")
    return provider_class(ai_config)
