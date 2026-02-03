# tech-news-discord-bot

毎朝 **AWS・Databricks のチェンジログ** や **技術ブログ** を収集し、キーワードでフィルタリングして **AI 要約付き** で Discord に通知する GitHub Actions ボット。

---

## 機能一覧

| 機能 | 詳細 |
|------|------|
| RSS 収集 | AWS / Databricks / dev.to / Medium など複数ソースから記事を収集 |
| キーワードフィルタリング | 設定したキーワードに基づいてスコアリング・選定 |
| AI 要約（マルチプロバイダー） | Claude / ChatGPT / Gemini を `settings.yaml` で切り替え可能 |
| Discord 通知 | Webhook via embeds で見やすい通知を送信 |
| 毎朝スケジュール | GitHub Actions の `cron` で毎朝 7:00 AM JST に実行 |
| 手動実行 | `workflow_dispatch` で任意のタイミングで実行可能 |

---

## リポジトリ構成

```
tech-news-discord-bot/
├── .github/
│   └── workflows/
│       └── daily_notify.yml      # GitHub Actions ワークフロー
├── config/
│   └── settings.yaml             # キーワード・ソース・AI設定
├── src/
│   ├── __init__.py
│   ├── main.py                   # エントリポイント
│   ├── fetcher.py                # RSS 収集
│   ├── filter.py                 # キーワードフィルタリング・スコアリング
│   ├── summarizer.py             # AI 要約（プロバイダー非依存）
│   ├── notifier.py               # Discord Webhook 通知
│   └── providers/                # LLM プロバイダー層
│       ├── __init__.py           # ファクトリ（プロバイダー動的選択）
│       ├── base.py               # 抽象基底クラス
│       ├── claude.py             # Anthropic Claude
│       ├── chatgpt.py            # OpenAI ChatGPT
│       └── gemini.py             # Google Gemini
├── requirements.txt              # Python依存関係
├── .gitignore
└── README.md
```

---

## 初期設定

### 1. GitHub Secrets の設定

リポジトリの `Settings → Secrets and variables → Actions` で以下の Secret を設定してください。
**使用するプロバイダーに対応する Secret のみ** 設定すればOKです。

| Secret 名 | 対応プロバイダー | 取得方法 |
|-----------|-----------------|----------|
| `DISCORD_WEBHOOK_URL` | ― (必須) | Discord チャンネル設定 → 連携 → Webhook で作成 |
| `ANTHROPIC_API_KEY` | Claude | [console.anthropic.com](https://console.anthropic.com) で取得 |
| `OPENAI_API_KEY` | ChatGPT | [platform.openai.com](https://platform.openai.com) で取得 |
| `GEMINI_API_KEY` | Gemini | [aistudio.google.com](https://aistudio.google.com) で取得 |

### 2. AI プロバイダーの選択

`config/settings.yaml` の `ai` セクションで使用するプロバイダーとモデルを選んでください。

```yaml
# --------- Claude を使う場合 ---------
ai:
  provider: claude
  model: "claude-sonnet-4-20250514"

# --------- ChatGPT を使う場合 ---------
# ai:
#   provider: chatgpt
#   model: "gpt-4o-mini"

# --------- Gemini を使う場合 ---------
# ai:
#   provider: gemini
#   model: "gemini-2.0-flash"
```

> **⚠️ Gemini Free tier について:**  
> Gemini の無料プランはバースト制限（瞬間的な連続呼び出し）が非常に厳しく、複数記事の要約処理には不向きです。実運用では Claude または ChatGPT を推奨します。Gemini を使う場合は有料プラン（Pay-as-you-go）への切り替えを検討してください。

### 3. キーワードの設定

`config/settings.yaml` の `keywords` セクションで収集したいキーワードを編集してください。

```yaml
keywords:
  - AWS
  - Databricks
  - Kubernetes
  # ... 追加・削除 自由
```

### 4. 収集ソースの追加・削除

`config/settings.yaml` の `sources` セクションで RSS URL を管理してください。

```yaml
sources:
  - id: my_new_source
    name: "My Source"
    type: rss
    url: "https://example.com/feed"
    max_items: 20
```

> **注意:** 新しいソースを追加した場合、`src/notifier.py` の `_SOURCE_EMOJI` と `_SOURCE_COLOR` にも対応エントリを追加すると、Discord での表示が改善されます。

### 5. AI 要約の無効化

要約を無効にする場合は `config/settings.yaml` で以下のように変更してください。

```yaml
ai:
  enabled: false
```

---

## ローカルでの実行（テスト）

`.env` ファイルを作成し、環境変数を設定してください。（`.env` は `.gitignore` で除外されているため、コミットされません）

```bash
# .env の作成（テンプレートをコピーして値を埋める）
cp .env.example .env
# → エディタで DISCORD_WEBHOOK_URL や API キーの値を入力してください
```

`.env.example`（テンプレート）の内容：

```env
# Discord
DISCORD_WEBHOOK_URL=your_webhook_url_here

# AI プロバイダー（使用するものだけ埋める）
ANTHROPIC_API_KEY=your_anthropic_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here
```

実行コマンド：

```bash
# 依存関係インストール
pip install -r requirements.txt

# .env を読み込んで DRY RUN で実行（Discord には送信しない）
set -a && source .env && set +a
DRY_RUN=true python -m src.main

# 実際に Discord に送信
set -a && source .env && set +a
python -m src.main
```

---

## スケジュール変更

`.github/workflows/daily_notify.yml` の `cron` で時間を変경してください。

現在の設定: `0 22 * * *`（UTC）= **毎朝 7:00 AM JST**

| 希望時間 (JST) | cron (UTC) |
|----------------|------------|
| 6:00 AM | `0 21 * * *` |
| 7:00 AM | `0 22 * * *` |
| 8:00 AM | `0 23 * * *` |
| 9:00 AM | `0 0 * * *` |

---

## アーキテクチャ

```
GitHub Actions (cron: 毎朝7AM JST)
        │
        ▼
┌─────────────┐
│  fetcher.py │  ← RSS ソース（AWS / Databricks / dev.to ...）
└──────┬──────┘
       ▼
┌─────────────┐
│  filter.py  │  ← キーワード検索・スコアリング
└──────┬──────┘
       ▼
┌───────────────┐
│ summarizer.py │  ← プロバイダー非依存の要約インターフェース
└──────┬────────┘
       │
       ├─► providers/claude.py   (Anthropic)
       ├─► providers/chatgpt.py  (OpenAI)
       └─► providers/gemini.py   (Google)
              ← settings.yaml の provider で動的に切り替え
       │
       ▼
┌─────────────┐
│ notifier.py │  ← Discord Webhook で通知送信
└─────────────┘
```