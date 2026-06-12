import os
import json
import requests
from playwright.sync_api import sync_playwright

# 環境変数の読み込み
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
VISASQ_COOKIE_JSON = os.environ.get("VISASQ_COOKIE")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")

# フィルタリング基準
MY_PROFILE = """
大日本印刷株式会社にて約8年間、企画開発職として商品デザイン、ブランドデザイン、生成AIサービスの事業開発に従事。

・2018年〜2022年：クライアント企業の商品デザインディレクション、および自社事業部のBtoBブランディング・マーケティングデザインを担当。
・2023年〜現在：生成AIと国内統計データを活用したリサーチSaaSの企画・開発を主導。UX設計からLLM連携、特許出願、セキュア環境構築、DevOps・QA体制構築までを牽引。

先端技術を用いた新規事業の0→1立ち上げ、および実践的なサービスデザイン・開発運用マネジメントに関して知見があります。

職歴
Lifeデザイン事業部ソリューションサービス本部
 企画開発職 
2023/04 - 現在
​生成AIと国内統計データを活用した「仮想生活者への定性調査サービス」の企画・開発を主導。
​■ プロダクト企画・要件定義
​統計（国勢調査等）とLLMを連携した仮想生活者対話システムの設計
​開発プロセスのマネジメント
開発技術の特許出願と他社特許調査
サービス全体の​UXデザイン（シナリオ・UIモック作成）と改善
​■ セキュリティ・環境構築
​国内大手企業のコンプライアンス、セキュリティ基準に対応するセキュアなBtoB環境の構築
​■ 保守運用・DevOps体制構築
​CI/CDパイプライン等のDevOps設計・構築、および品質保証（QA）体制の構築
商品企画・開発
PM
WEBデザイナー
製品・サービス
生成AIソリューション
取引先業界
飲料メーカー
食品メーカー
日雑品メーカー
金融業界
包装事業部マーケティング企画本部
 デザイン企画職 
2018/04 - 2023/03
クライアント企業の商品デザインディレクション、および自社事業部のBtoBブランディング・マーケティングデザインを担当
ブランディング
商品企画・開発
製品・サービス
包装
食品包材
飲料容器・包装材
BtoBマーケティング
取引先業界
食品メーカー
菓子メーカー

学歴

東京藝術大学大学院 
2016/04 - 2018/03
美術研究科デザイン専攻 
（修士）
東京藝術大学 
2011/04 - 2016/03
美術学部デザイン科 
（学士）

資格・免許
追加する
Project Management Professional（PMI）
2023/09
応用情報技術者
2023/06
2種電気工事士
2020/03
編集

話せるトピック
大手企業での生成AIを活用した新規サービス立ち上げ経験

■背景
​大手企業にて、生成AIと統計データを掛け合わせた新規BtoB SaaSプロダクトの0→1立ち上げ時のサービス企画・開発を主導しました。
​プロジェクト内でプロダクトマネージャー（PdM）の役割を担い、企画立案から要件定義、UXデザイン、開発管理、リリース後の保守運用体制構築まで一気通貫で推進しました。
​本サービスは、現代日本の縮図となるように設計された複数の仮想生活者と対話して高速にリサーチを行うプロダクトです。
フェーズとしては、構想段階からMVP（最小限のプロダクト）開発、そして国内大手企業（金融、食品、飲料、日雑品メーカー等）への初期導入・検証フェーズまでの一連のサイクルを経験しています。

■話せること
​■ 解決した課題の例
・生成AIの不確実性と、大手企業の厳格なセキュリティ基準（データ分離環境等）など、大手向け生成サービス特有のセキュリティ・コンプライアンス障壁の低予算での解決
・元デザイナーの知見を活かし、GitHub Copilotを用いたインタラクティブなUIモック作成からUX先行型で要件定義を進め、開発管理エンジニアや営業との認識ズレや無駄なドキュメンテーションを防止

​■ 具体的な施策や経験
・生成AIプロダクトの立ち上げ初期におけるMVPの定義の置き方
・自社開発技術の特許出願（権利化）と他社特許調査を開発と並行させる実務ノウハウ
・リリースを見据えたCI/CDパイプライン等のDevOps設計、品質保証（QA）体制、およびCSフローの構築とチーム教育

■おもな使用ツール
・Microsoft Azure
・Google Cloud
・Dify
・ChatGPT Enterprise
・Gemini Enterprise
・GitHub / GitHub Copilot
・Visual Studio Code
・Copilot for Microsoft 365
・Power Automate
・Figma
・Adobe Photoshop / Adobe Illustrator

​伝統的な大手企業組織の中で新規事業をスピード感を持って進める際のリアルな障壁や、それを突破した具体的な工夫について、相談者様の状況に合わせて概要をお伝え可能です。
"""

def get_visasq_issues():
    """Playwrightを使ってログイン状態で公募情報を取得する"""
    issues = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()

        if VISASQ_COOKIE_JSON:
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
        page.goto("https://expert.visasq.com/issue/?is_open_only=true")
        page.wait_for_load_state("networkidle")

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
    """HTTPリクエスト（REST API）を使ってGemini APIで公募案件をフィルタリングする"""
    # 2026年の標準モデルを使用
    model_name = "gemini-2.5-flash"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"

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
    必ず以下のJSON配列形式でのみ回答してください。合致する案件がない場合は空の配列 `[]` を返してください。
    [
      {{
        "title": "公募のタイトルまたは概要",
        "url": "該当案件のURL",
        "score": "マッチ度（10点満点）",
        "reason": "なぜマッチすると判断したかの簡潔な理由（1行）"
      }}
    ]
    """

    # Geminiに確実にJSONを吐き出させる設定
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }],
        "generationConfig": {
            "responseMimeType": "application/json"
        }
    }
    
    headers = {"Content-Type": "application/json"}
    
    # APIリクエストの実行
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code != 200:
        raise Exception(f"Gemini API Error: {response.status_code} - {response.text}")
        
    res_json = response.json()
    
    # レスポンスからテキスト（JSON文字列）を抽出してパース
    text_content = res_json["candidates"][0]["content"]["parts"][0]["text"].strip()
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
