# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository does

cron-job.orgが毎日JST 9:00にGitHub Actions（workflow_dispatch）をトリガーするビザスク公募マッチング通知スクリプト。

1. Playwrightでビザスクにメール/パスワードログインし、公募一覧（1〜5ページ）をスクレイピング
2. `FILTER_KEYWORDS` でキーワード事前フィルタリング
3. Gemini APIでプロフィールとのマッチ度を判定（7点以上のみ抽出）
4. Discordのwebhookに通知（公開日・締切日・マッチ度・選定理由を含む）

## Running the script

```bash
# 依存インストール
pip install playwright requests
playwright install chromium

# 実行（環境変数が必要）
GEMINI_API_KEY=... VISASQ_EMAIL=... VISASQ_PASSWORD=... WEBHOOK_URL=... python main.py
```

## Architecture

`main.py` のみの単一ファイル構成。以下の関数がパイプラインを形成：

- `login_with_credentials(page)` — Auth0経由（`https://auth-service.visasq.com`）でログイン。セレクターは `input#username`, `input#password`, `get_by_role("button", name="ログイン")`
- `get_visasq_issues()` — ログイン後、`/direct_interview/` と `/direct_recruitment/` のリンクを収集。`/issue/` はページネーションリンクのため対象外
- `filter_by_keywords(issues)` — `FILTER_KEYWORDS` リストで事前絞り込み（Gemini APIリクエスト数削減目的）
- `analyze_with_gemini(issues)` — 60件ずつチャンク処理。`gemini-2.5-flash` 使用。無料枠は1日20リクエストなので通常1〜2リクエストに収まる設計。Geminiにはタイトル・URL・公開日・締切日・スコア・理由をJSON形式で返させる
- `send_notification(matched_items)` — Discord 2000文字制限に対応して分割送信

## Trigger architecture

GitHub Actionsのscheduledトリガーは不安定なため、cron-job.org（外部サービス）がGitHub API経由でworkflow_dispatchをトリガーする構成。`cron.yml` のschedule設定は残っているがフォールバック用。

## Key constants to modify

- `FILTER_KEYWORDS`（L15付近）— キーワード事前フィルタのリスト（パッケージ・包装・包材等を含む）
- `MY_PROFILE`（L33付近）— Geminiに渡すプロフィール文（話せない領域の明示を含む）
- `chunk_size = 60`（`analyze_with_gemini`内）— Gemini APIリクエスト数に直結

## GitHub Actions secrets

| Secret | 用途 |
|--------|------|
| `VISASQ_EMAIL` | ログイン用メールアドレス |
| `VISASQ_PASSWORD` | ログイン用パスワード |
| `GEMINI_API_KEY` | Gemini API キー |
| `WEBHOOK_URL` | Discord Webhook URL |
| `VISASQ_COOKIE` | 旧方式のCookieログイン（フォールバック用、現在は未使用） |
