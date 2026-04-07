from datetime import datetime, timezone, timedelta

# 日本時間（JST = UTC+9）で現在時刻を取得
JST = timezone(timedelta(hours=9))
now_jst = datetime.now(JST)
timestamp = now_jst.strftime("%Y-%m-%d %H:%M")

# レポートに埋め込む
report_header = f"# 週次ポートフォリオ X スキャンレポート\n更新: {timestamp}\n\n---\n"
import os
import json
import datetime
from xai_sdk import Client
from xai_sdk.chat import user
from xai_sdk.tools import x_search

# ------------------------------
# API クライアント設定
# ------------------------------
API_KEY = os.environ.get("XAI_API_KEY")
client = Client(api_key=API_KEY)

# ------------------------------
# 設定：キーワード・セクター
# ------------------------------
SEARCHES = [
    {"topic": "Micron MU HBM4 AI memory Vera Rubin", "sector": "メモリ", "lang": "en"},
    {"topic": "HBM4 SK Hynix Samsung memory AI chip", "sector": "メモリ", "lang": "en"},
    {"topic": "NVIDIA NVDA Blackwell GB300 datacenter", "sector": "AIインフラ", "lang": "en"},
    {"topic": "AI infrastructure hyperscaler capex 2026", "sector": "AIインフラ", "lang": "en"},
    {"topic": "S&P500 AI tariff recession sentiment", "sector": "マクロ", "lang": "both"},
    {"topic": "住友電工 フォトニクス CPO 光トランシーバ", "sector": "フォトニクス", "lang": "ja"},
    {"topic": "CPO co-packaged optics photonics InP wafer", "sector": "フォトニクス", "lang": "en"},
]

CACHE_FILE = "cache.json"

# ------------------------------
# ヘルパー関数
# ------------------------------
def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_cache(cache):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

def x_sentiment(topic, lang="ja", max_results=5):
    prompt = f"""X（Twitter）で「{topic}」について最新情報を{lang}で検索し、以下の形式で出力してください。
【検索トピック】{topic}
【センチメント】強気/弱気/中立
【根拠】1〜2文で具体的に
【キーワード】キーワード1 / キーワード2 / キーワード3
【注目ポスト】
1. @投稿者名 「投稿本文の全文」 URL
"""
    chat = client.chat.create(
        model="grok-4-1-fast",
        tools=[x_search()],
    )
    chat.append(user(prompt))
    response = chat.sample()
    return response.content

# ------------------------------
# メイン処理
# ------------------------------
def main():
    cache = load_cache()
    report = {}
    sector_scores = {}

    for item in SEARCHES:
        topic = item["topic"]
        sector = item["sector"]
        lang = item.get("lang", "en")

        # キャッシュにある場合はスキップ
        if topic in cache:
            result = cache[topic]
        else:
            result = x_sentiment(topic, lang=lang)
            cache[topic] = result

        # セクター別集計
        if sector not in sector_scores:
            sector_scores[sector] = {"score": 0, "entries": []}

        # スコア簡易判定
        score = 0
        if "強気" in result: score = +2
        elif "中立" in result: score = 0
        elif "弱気" in result: score = -2

        sector_scores[sector]["score"] += score
        sector_scores[sector]["entries"].append({"topic": topic, "score": score, "text": result})

    save_cache(cache)

    # ------------------------------
    # Markdown レポート生成
    # ------------------------------
    date_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    md_lines = []
    md_lines.append(f"# 週次ポートフォリオ X スキャンレポート\n更新: {date_str}\n")
    md_lines.append("## 総合サマリー\n全セクター横断で強気傾向。AIインフラとメモリが特に顕著。\n")

    # セクター別スコア
    md_lines.append("## セクター別スコア")
    md_lines.append("| セクター | センチメント | スコア |")
    md_lines.append("|---------|------------|-------|")
    for sector, data in sector_scores.items():
        s_score = data["score"]
        if s_score > 0: sentiment = "強気"
        elif s_score == 0: sentiment = "中立"
        else: sentiment = "弱気"
        md_lines.append(f"| {sector} | {sentiment} | {s_score} |")

    # セクター詳細
    md_lines.append("\n## セクター詳細")
    for sector, data in sector_scores.items():
        md_lines.append(f"\n### {sector}")
        for entry in data["entries"]:
            md_lines.append(f"- **{entry['topic']}** (スコア: {entry['score']})\n```\n{entry['text']}\n```")

    # アクション候補（簡易ルール）
    md_lines.append("\n## 今週のアクション候補")
    for sector, data in sector_scores.items():
        score = data["score"]
        if score >= 3: action = "現場注視"
        elif score > 0: action = "静観"
        else: action = "フレームワーク通り待機"
        md_lines.append(f"- {sector}：{action}")

    # 書き出し
    report_file = "report.md"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))

    print(f"レポートを生成しました: {report_file}")

if __name__ == "__main__":
    main()
