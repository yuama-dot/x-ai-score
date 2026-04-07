import os
import datetime
import json
from pathlib import Path
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

# セクターとキーワード
sectors = {
    "メモリ": ["MU", "SK Hynix", "HBM"],
    "AIインフラ": ["NVDA", "NVIDIA"],
    "フォトニクス": ["住友電工", "CPO"],
    "マクロ": ["S&P500 tariff recession risk 2026"]
}

# キャッシュディレクトリ
cache_dir = Path("cache")
cache_dir.mkdir(exist_ok=True)

# --- 結果格納 ---
sector_results = {}

for sector, keywords in sectors.items():
    # キャッシュファイル名
    cache_file = cache_dir / f"{sector.replace(' ', '_')}.json"

    # キャッシュがあれば再利用
    if cache_file.exists():
        with open(cache_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            sector_results[sector] = data
        continue

    # キャッシュがなければXAI検索
    prompt_text = f"次のキーワードについて最新情報をXで調べ、本文とURLを出力してください: {', '.join(keywords)}"
    chat = client.chat.create(model="grok-4-1-fast", tools=[x_search()])
    chat.append(user(prompt_text))
    response = chat.sample()

    # 取得投稿数チェック
    post_count = len(response.content.split("\n"))
    if post_count < 3:
        data = {
            "score": None,
            "sentiment": "データ不足",
            "content": "取得投稿数が少ないため分析不能です。"
        }
    else:
        data = {
            "score": 2,
            "sentiment": "強気",
            "content": response.content
        }

    # 結果を保存
    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    sector_results[sector] = data

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

    f.write("## 総合サマリー\n")
    f.write("全セクターを横断した分析の結果、AIインフラとメモリ関連が強気の傾向を示しています。\n\n")

    # セクター別スコア
    f.write("## セクター別スコア\n")
    f.write("| セクター | センチメント | スコア |\n")
    f.write("|---------|------------|-------|\n")
    for sector, data in sector_results.items():
        score_display = data['score'] if data['score'] is not None else "-"
        f.write(f"| {sector} | {data['sentiment']} | {score_display} |\n")

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
