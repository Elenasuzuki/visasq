import os
import json
import requests
from playwright.sync_api import sync_playwright
from google import genai  # 2026年最新のGemini SDK

# 環境変数の読み込み
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
VISASQ_COOKIE_JSON = os.environ.get("VISASQ_COOKIE")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")

# フィルタリング基準
MY_PROFILE = """
【関心・経験領域】
- 生成AI、LLMを活用したサービス開発や技術選定
- Webアプリケーション（特にSaaS）のプロダクトマネジメント・開発リード
- UI/UXデザイン、フロントエンド、デザインシステム構築
- 新規事業立ち上げ、技術トレンドの調査
"""

def get_visasq_issues():
    """Playwrightを使ってログイン状態で公募情報を取得する"""
    issues = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()

        # Cookieを設定してログイン状態をシミュレート
        if VISASQ_COOKIE_JSON:
            cookies = json.loads(VISASQ_COOKIE_JSON)
            
            # 【エラー修正】Playwrightが拒絶する不適切なsameSiteの値をクレンジング
            for cookie in cookies:
                if "sameSite" in cookie:
                    # 頭文字を大文字にする (例: "lax" -> "Lax")
                    val = str(cookie["sameSite"]).capitalize()
                    if val in ["Strict", "Lax", "None"]:
                        cookie["sameSite"] = val
                    else:
                        # "unspecified" などの無効な値は属性ごと削除してブラウザに任せる
                        cookie.pop("sameSite")

            context.add_cookies(cookies)

        page = context.new_page()
        page.goto("https://expert.visasq.com/issue/?is_open_only=true")
        page.wait_for_load_state("networkidle")

        # 公募カード要素からテキストとリンクを抽出
        cards = page.query_selector_all("a[href*='/issue/']")
        
        for card in cards:
            text = card.inner_text()
            href = card.get_attribute("href")
            url = f"https://expert.visasq{href}" if href.startswith("/") else href
            
            if text:
                issues.append({"url": url, "text": text.replace("\n", " ")})

        browser.close()
    return issues

def analyze_with_gemini(issues):
    """Gemini APIを使用して公募案件をフィルタリングする"""
    # 最新のクライアント初期化方法
    client = genai.Client(api_key=GEMINI_API_KEY)

    prompt = f"""
    あなたは優秀なビジネスエージェントです。
    以下の【私のプロフィール】と、取得した【公募案件リスト】を比較分析してください。
    
    【私のプロフィール】
    {MY_PROFILE}

    【公募案件リスト】
    {json.dumps(issues, ensure_ascii=False)}

    【選定基準】
    私の関心や経験領域とマッチ度が高い（10点満点中7点以上）と考えられる案件のみを抽出してください。
    
    【出力フォーマット】
    必ず以下のMarkdown形式のJSON配列でのみ回答してください。合致する案件がない場合は空の配列 `[]` を返してください。雑談や解説のテキストは一切不要です。
    [
      {{
        "title": "公募のタイトルまたは概要",
        "url": "該当案件のURL",
        "score": "マッチ度（10点満点）",
        "reason": "なぜマッチすると判断したかの簡潔な理由（1行）"
      }}
    ]
    """
    
    # 最新のAPI呼び出し形式に変更
    response = client.models.generate_content(
        model="gemini-1.5-flash",
        contents=prompt
    )
    
    text_content = response.text.strip()
    if text_content.startswith("```json"):
        text_content = text_content.split("```json")[1].split("```")[0].strip()
    elif text_content.startswith("```"):
        text_content = text_content.split("```")[1].split("```")[0].strip()
        
    return json.loads(text_content)

def send_notification(matched_items):
    """結果をDiscordのWebhookに通知する"""
    if not matched_items:
        print("マッチする案件はありませんでした。")
        return

    text_lines = ["🔔 **ビザスク新着マッチング公募** \n"]

    for item in matched_items:
        text_lines.append(
            f"• **[{item['title']}]({item['url']})**\n"
            f"  *マッチ度:* {item['score']}/10\n"
            f"  *選定理由:* {item['reason']}\n"
        )

    payload = {"content": "\n".join(text_lines)}
    response = requests.post(WEBHOOK_URL, json=payload)
    
    if response.status_code in [200, 204]:
        print(f"{len(matched_items)} 件の案件をDiscordに通知しました。")
    else:
        print(f"通知に失敗しました。ステータスコード: {response.status_code} - {response.text}")

if __name__ == "__main__":
    print("スクレイピングを開始します...")
    raw_issues = get_visasq_issues()
    print(f"{len(raw_issues)} 件の公募を取得しました。AI解析にかけます...")
    
    if raw_issues:
        matched = analyze_with_gemini(raw_issues)
        send_notification(matched)
    else:
        print("公募データが取得できませんでした。Cookieの期限切れの可能性があります。")
