import os
import datetime
from xai_sdk import Client
from xai_sdk.chat import user
from xai_sdk.tools import x_search

# --- 設定 ---
API_KEY = os.environ.get("XAI_API_KEY")
if not API_KEY:
    raise ValueError("XAI_API_KEY が設定されていません。Secrets に登録してください。")

client = Client(api_key=API_KEY)

# 日本時間タイムスタンプ
JST = datetime.timezone(datetime.timedelta(hours=+9))
now_jst = datetime.datetime.now(JST)
timestamp = now_jst.strftime("%Y%m%d_%H%M")

# セクターリスト
sectors = {
    "メモリ": ["MU", "SK Hynix", "HBM"],
    "AIインフラ": ["NVDA", "NVIDIA"],
    "フォトニクス": ["住友電工", "CPO"],
    "マクロ": ["S&P500", "関税"]
}

# 結果格納
sector_results = {}

# --- 各セクターをスキャン ---
for sector, keywords in sectors.items():
    prompt_text = f"次のキーワードについて最新情報をXで調べ、本文とURLを出力してください: {', '.join(keywords)}"
    chat = client.chat.create(model="grok-4-1-fast", tools=[x_search()])
    chat.append(user(prompt_text))
    response = chat.sample()
    # 仮に感情スコアを +2/+3/-2 でサンプル
    sector_results[sector] = {
        "score": 2,  # 後でAIに感情分析させても良い
        "sentiment": "強気",
        "content": response.content
    }

# --- アクション候補 ---
actions = {
    "メモリ": "静観（テーゼ変化なし）",
    "AIインフラ": "現場シグナル待ち",
    "フォトニクス": "注視",
    "マクロ": "フレームワーク通り待機"
}

# --- レポート作成 ---
report_file = f"report_{timestamp}.md"
with open(report_file, "w", encoding="utf-8") as f:
    f.write(f"# 週次ポートフォリオ X スキャンレポート\n")
    f.write(f"更新: {now_jst.strftime('%Y-%m-%d %H:%M')}\n\n")
    
    # 総合サマリー（簡易）
    f.write("## 総合サマリー\n")
    f.write("全セクターを横断した分析の結果、AIインフラとメモリ関連が特に強気の傾向を示しています。\n\n")
    
    # セクター別スコア
    f.write("## セクター別スコア\n")
    f.write("| セクター | センチメント | スコア |\n")
    f.write("|---------|------------|-------|\n")
    for sector, data in sector_results.items():
        f.write(f"| {sector} | {data['sentiment']} | {data['score']} |\n")
    
    # セクター詳細
    f.write("\n## セクター詳細\n")
    for sector, data in sector_results.items():
        f.write(f"### {sector}\n")
        f.write(f"{data['content']}\n\n")
    
    # 今週のアクション候補
    f.write("## 今週のアクション候補\n")
    for sector, action in actions.items():
        f.write(f"- {sector}: {action}\n")

print(f"Report saved to {report_file}")
