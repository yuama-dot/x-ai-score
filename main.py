# main.py
import os
import json
import datetime
from pathlib import Path
from xai_sdk import Client

# --- 設定 ---
API_KEY = os.getenv("XAI_API_KEY")
DATA_DIR = Path("history")
DATA_DIR.mkdir(exist_ok=True)
REPORT_DIR = Path("reports")
REPORT_DIR.mkdir(exist_ok=True)

SECTORS = {
    "メモリ": {"keywords": ["MU", "HBM"], "priority": False},
    "AIインフラ": {"keywords": ["NVDA", "GPU", "AI server"], "priority": False},
    "フォトニクス": {"keywords": ["住友電工", "CPO", "Photonics"], "priority": False},
    "マクロ": {"keywords": ["S&P500", "tariff", "recession", "GDP", "interest rate"], "priority": True},
}

MIN_POSTS = 3  # 投稿件数3件未満でデータ不足
HIGHLIGHT_NEW = True  # 新規投稿に[NEW]タグ付与

# --- xAI クライアント ---
client = Client(api_key=API_KEY)

def fetch_posts(keyword, limit=50):
    """指定キーワードでX投稿を取得"""
    results = client.search_posts(query=keyword, limit=limit)
    return [{"url": r["url"], "text": r["text"], "created_at": r["created_at"]} for r in results]

def analyze_sentiment(posts):
    """簡易スコアリング"""
    pos = sum(1 for p in posts if "positive" in p.get("sentiment", "").lower())
    neg = sum(1 for p in posts if "negative" in p.get("sentiment", "").lower())
    total = len(posts)
    if total < MIN_POSTS:
        return "データ不足", 0
    if pos > total/2:
        score = min(pos, 3)
        return "強気", score
    elif neg > total/2:
        score = -min(neg, 3)
        return "弱気", score
    else:
        return "中立", 0

def load_previous(sector):
    path = DATA_DIR / f"{sector}.json"
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_current(sector, data):
    path = DATA_DIR / f"{sector}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def mark_new_posts(prev_posts, curr_posts):
    prev_urls = {p["url"] for p in prev_posts}
    for p in curr_posts:
        if p["url"] not in prev_urls and HIGHLIGHT_NEW:
            p["text"] = "[NEW] " + p["text"]
    return curr_posts

def generate_markdown(report_date, sector_results):
    md = f"# 週次ポートフォリオ X スキャンレポート\n更新: {report_date}\n\n"
    # 総合サマリー
    all_scores = [res["score"] for res in sector_results.values() if isinstance(res["score"], int)]
    if all_scores:
        summary = "全体的に強気傾向" if sum(all_scores) > 0 else "全体的に弱気傾向"
    else:
        summary = "データ不足で総合判断不可"
    md += f"## 総合サマリー\n{summary}\n\n"

    # セクター別スコア
    md += "## セクター別スコア\n| セクター | センチメント | スコア |\n|---------|------------|-------|\n"
    for sector, res in sector_results.items():
        md += f"| {sector} | {res['sentiment']} | {res['score']} |\n"
    md += "\n"

    # セクター詳細
    md += "## セクター詳細\n"
    for sector, res in sector_results.items():
        md += f"### {sector}\n"
        if res["posts"]:
            for p in res["posts"]:
                md += f"- {p['text']} ({p['url']})\n"
        else:
            md += "- データ不足\n"
        md += "\n"
    return md

def main():
    now_jst = datetime.datetime.utcnow() + datetime.timedelta(hours=9)
    report_date = now_jst.strftime("%Y-%m-%d %H:%M")

    sector_results = {}
    for sector, info in SECTORS.items():
        all_posts = []
        for kw in info["keywords"]:
            posts = fetch_posts(kw)
            all_posts.extend(posts)
        prev_posts = load_previous(sector)
        curr_posts = mark_new_posts(prev_posts, all_posts)
        save_current(sector, curr_posts)
        sentiment, score = analyze_sentiment(curr_posts)
        sector_results[sector] = {"sentiment": sentiment, "score": score, "posts": curr_posts}

    # Markdown出力
    md_report = generate_markdown(report_date, sector_results)
    report_path = REPORT_DIR / f"report_{now_jst.strftime('%Y%m%d_%H%M')}.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(md_report)
    print(f"レポート出力完了: {report_path}")

if __name__ == "__main__":
    main()
