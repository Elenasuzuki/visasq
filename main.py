import os
import json
import requests
import time
from playwright.sync_api import sync_playwright
from datetime import datetime, timedelta, timezone

# 環境変数の読み込み
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
VISASQ_COOKIE_JSON = os.environ.get("VISASQ_COOKIE")
VISASQ_EMAIL = os.environ.get("VISASQ_EMAIL")
VISASQ_PASSWORD = os.environ.get("VISASQ_PASSWORD")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")

# キーワード事前フィルタリング（LLMに渡す前に絞り込む）
FILTER_KEYWORDS = [
    "AI", "人工知能", "LLM", "生成AI", "ChatGPT", "機械学習", "ディープラーニング",
    "新規事業", "0→1", "スタートアップ", "新サービス", "新プロダクト",
    "DX", "デジタル変革", "デジタルトランスフォーメーション",
    "SaaS", "プロダクト", "PdM", "プロダクトマネージャ",
    "UX", "UI", "デザイン", "Figma",
    "知財", "特許", "IP",
    "ブランディング", "マーケティング",
    "パッケージ", "包装", "包材",
    "セキュリティ", "クラウド", "Azure", "Google Cloud",
    "DevOps", "CI/CD", "アジャイル",
]

# フィルタリング基準
MY_PROFILE = """
【職歴・コアスキル】
- 大手企業（大日本印刷）にて約8年間、企画開発職（PdM、デザイン企画、WEBデザイナー）として従事。
- 先端技術（生成AI/LLM）を用いた新規事業の0→1立ち上げ、および実践的なサービスデザイン・開発運用マネジメント。
- ターゲット業界：飲料、食品、日雑品、金融、包装・包材など。

【強み・話せるトピック（ビザスクの公募とマッチさせる要素）】
1. 生成AIを活用した新規BtoB SaaSプロダクトの0→1立ち上げ・PM経験
   - 統計データとLLMを連携した「仮想生活者への定性調査サービス（対話システム）」の企画・開発を構想からMVP、初期導入・検証まで一気通貫で主導。
   - 生成AIプロダクト初期のMVPの定義、UX先行型（FigmaやGitHub Copilotを用いたUIモック作成）での要件定義。
2. 生成AI特有のセキュリティ・コンプライアンス・知財
   - 大手企業の厳格なセキュリティ基準（データ分離環境等）に対応するセキュアなBtoB環境構築のノウハウ。
   - 自社開発技術の特許出願（権利化）と他社特許調査を開発と並行させる実務。
3. 保守運用・DevOps・QA体制構築
   - CI/CDパイプライン等のDevOps設計、品質保証（QA）体制、CSフロー構築。
4. ブランディング・デザインディレクション
   - 商品デザインディレクション、BtoBブランディング・マーケティングデザイン。

【学歴・資格】
- 東京藝術大学 美術学部デザイン科（学士） / 同大学院 美術研究科デザイン専攻（修士）
- Project Management Professional（PMP）、応用情報技術者、2種電気工事士

【主に使用しているツール・技術】
- Azure, Google Cloud, Dify, ChatGPT/Gemini Enterprise, GitHub Copilot, Figma
"""

def login_with_credentials(page):
    """メールアドレスとパスワードでログインする"""
    print("メールアドレス・パスワードでログインします...")
    page.goto("https://expert.visasq.com/auth/signin/")
    page.wait_for_load_state("networkidle")
    page.fill("input#username", VISASQ_EMAIL)
    page.fill("input#password", VISASQ_PASSWORD)
    page.click("button[type='submit']:not([value])")
    page.wait_for_load_state("networkidle")
    if "expert.visasq.com" not in page.url:
        raise Exception(f"ログインに失敗しました。現在のURL: {page.url}")
    print("ログイン成功。")

def get_visasq_issues():
    """Playwrightを使ってログイン状態で公募情報を1〜5ページ目まで巡回取得する"""
    issues = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()

        if VISASQ_EMAIL and VISASQ_PASSWORD:
            page = context.new_page()
            login_with_credentials(page)
        elif VISASQ_COOKIE_JSON:
            cookies = json.loads(VISASQ_COOKIE_JSON)
            for cookie in cookies:
                if "sameSite" in cookie:
                    val = str(cookie["sameSite"]).capitalize()
                    if val in ["Strict", "Lax", "None"]:
                        cookie["sameSite"] = val
                    else:
                        cookie.pop("sameSite")
            context.add_cookies(cookies)
            page = context.new_page()
        else:
            raise Exception("VISASQ_EMAIL/VISASQ_PASSWORD または VISASQ_COOKIE が設定されていません。")

        # 1ページ目から5ページ目まで巡回
        for page_num in range(1, 6):
            print(f"{page_num} ページ目を読み込んでいます...")
            url = f"https://expert.visasq.com/issue/?is_open_only=true&page={page_num}"
            
            try:
                page.goto(url)
                page.wait_for_load_state("networkidle")

                cards = page.query_selector_all("a[href*='/issue/']")
                if not cards:
                    print(f"{page_num} ページ目に公募が見つからないため、巡回を終了します。")
                    break

                for card in cards:
                    text = card.inner_text()
                    href = card.get_attribute("href")
                    card_url = f"https://expert.visasq.com{href}" if href.startswith("/") else href
                    if text:
                        issues.append({"url": card_url, "text": text.replace("\n", " ")})

                page.wait_for_timeout(1000)

            except Exception as e:
                print(f"{page_num} ページ目の取得中にエラーが発生しました: {e}")
                break

        browser.close()
    return issues

def filter_by_keywords(issues):
    """キーワードに1つでもマッチする案件だけに絞り込む"""
    matched = [
        issue for issue in issues
        if any(kw.lower() in issue["text"].lower() for kw in FILTER_KEYWORDS)
    ]
    print(f"キーワードフィルタリング: {len(issues)} 件 -> {len(matched)} 件")
    return matched

def analyze_with_gemini(issues):
    """Gemini APIを使用して、公募案件を25件ずつに分割して解析する（503エラー時の自動リトライ付き）"""
    JST = timezone(timedelta(hours=9))
    now_jst = datetime.now(JST)
    
    today_ymd = now_jst.strftime("%Y/%m/%d")
    yesterday_ymd = (now_jst - timedelta(days=1)).strftime("%Y/%m/%d")
    today_kanji = now_jst.strftime("%Y年%m月%d日")
    yesterday_kanji = (now_jst - timedelta(days=1)).strftime("%Y年%m月%d日")

    model_name = "gemini-2.5-flash"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}

    chunk_size = 25
    all_matched_items = []

    for i in range(0, len(issues), chunk_size):
        chunk = issues[i:i + chunk_size]
        print(f"公募データ {i+1} 〜 {min(i + chunk_size, len(issues))} 件目をAI解析中...")

        prompt = f"""
        # あなたは優秀なコンサルタントマッチングエージェントです。
        以下の【私のプロフィール】と、スクレイピングで取得した【公募案件リスト（一部）】を比較分析してください。
        
        【私のプロフィール】
        {MY_PROFILE}

        【公募案件リスト】
        {json.dumps(chunk, ensure_ascii=False)}

        【選定基準（超重要）】
        以下の1と2の条件を「両方とも」満たす案件のみを抽出してください。

        1. 日付のフィルタリング（前日以降のみ）
           現在の日本時間は {today_ymd} です。
           各案件のテキストに含まれる「公開日」「掲載日」などの日付を確認し、【昨日（{yesterday_ymd}）以降】に公開された新着案件のみを対象にしてください。
           具体的には、以下のいずれかに該当するものだけを残し、一昨日以前の古い案件はマッチ度が高くても【絶対に除外】してください。
           - 日付が {today_ymd} または {yesterday_ymd} であるもの
           - 日付が {today_kanji} または {yesterday_kanji} であるもの
           - テキスト内に「本日」「昨日」「〇時間前」「〇分前」といった相対的な新着表現があるもの

        2. スキルのマッチング
           私の関心・経験領域、資格、話せるトピックのいずれかと親和性が高く、私が専門家としてアドバイス・貢献できる可能性が非常に高い案件（10点満点中7点以上）。
           特に「生成AI/LLMのビジネス導入・SaaS立ち上げ」「UXデザイン・Figma活用」「知財・特許戦略」「セキュア環境構築」「BtoBブランディング・マーケティング」に関するテーマは高めに評価してください。
        
        【出力フォーマット】
        必ず以下のJSON配列形式でのみ回答してください。合致する案件がない場合は空の配列 `[]` を返してください。雑談は一切不要です。
        [
          {{
            "title": "公募のタイトルまたは概要",
            "url": "該当案件のURL",
            "score": "マッチ度（10点満点）",
            "reason": "私のプロフィールのどの経験（生成AI立ち上げ、UX先行要件定義、知財など）とどうマッチしているかの簡潔な理由（1行）"
          }}
        ]
        """

        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "responseMimeType": "application/json"
            }
        }
        
        max_retries = 3
        response_text = ""
        
        for retry in range(max_retries):
            response = requests.post(url, headers=headers, json=payload)
            
            if response.status_code == 200:
                res_json = response.json()
                response_text = res_json["candidates"][0]["content"]["parts"][0]["text"].strip()
                break
            elif response.status_code == 503:
                wait_time = 6 * (retry + 1)
                print(f"  -> Gemini APIが混雑しています(503)。{wait_time}秒後に自動再試行します... ({retry + 1}/{max_retries})")
                time.sleep(wait_time)
            else:
                raise Exception(f"Gemini API Error: {response.status_code} - {response.text}")
        else:
            print(f"警告: 503エラーが連続したため、このブロック（{i+1}件目〜）の解析をスキップします。")
            continue

        if response_text:
            try:
                # コードブロック（```json ... ```）が含まれる場合に除去
                cleaned = response_text.strip()
                if cleaned.startswith("```"):
                    cleaned = cleaned.split("```", 2)[1]
                    if cleaned.startswith("json"):
                        cleaned = cleaned[4:]
                    cleaned = cleaned.rsplit("```", 1)[0].strip()
                chunk_matched = json.loads(cleaned)
                all_matched_items.extend(chunk_matched)
            except Exception as parse_err:
                print(f"JSONパースエラーが発生しました（スキップします）: {parse_err}")

        time.sleep(2)

    return all_matched_items

def send_notification(matched_items):
    """結果をDiscordのWebhookに通知する"""
    if not matched_items:
        print("前日以降に公開された、マッチする新着案件はありませんでした。")
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
        filtered_issues = filter_by_keywords(raw_issues)
        matched = analyze_with_gemini(filtered_issues) if filtered_issues else []
        send_notification(matched)
    else:
        print("公募データが取得できませんでした。Cookieの期限切れの可能性があります。")
