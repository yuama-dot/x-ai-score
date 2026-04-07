import os
import json
from datetime import datetime, timezone, timedelta

# --- 設定 ---
REPORT_DIR = "reports"   # 履歴保存用ディレクトリ
os.makedirs(REPORT_DIR, exist_ok=True)
SECTORS = ["メモリ", "AIインフラ", "フォトニクス", "マクロ"]

# --- 日本時間取得 ---
JST = timezone(timedelta(hours=+9))
now = datetime.now(JST)
timestamp = now.strftime("%Y%m%d_%H%M")

# --- 前回レポート読み込み ---
def load_previous_report():
    latest_file = None
    files = sorted(os.listdir(REPORT_DIR), reverse=True)
    for f in files:
        if f.startswith("report_") and f.endswith(".json"):
            latest_file = f
            break
    if latest_file:
        with open(os.path.join(REPORT_DIR, latest_file), "r", encoding="utf-8") as fp:
            return json.load(fp)
    return {}

previous_report = load_previous_report()

# --- データ取得（ここをX投稿APIやスクレイピングに置き換え） ---
def fetch_sector_data(sector):
    # 例: 投稿件数ランダム生成（実際はAPIから取得）
    import random
    posts = random.randint(0, 5)
    if posts < 3:
        return {"score": "データ不足", "details": [], "post_count": posts}
    # ダミー詳細
    details = [{"text": f"{sector}注目投稿{i+1}", "url": f"https://x.com/dummy{i+1}"} for i in range(posts)]
    score = random.choice(["強気", "中立", "弱気"])
    return {"score": score, "details": details, "post_count": posts}

# --- 新規レポート生成 ---
report = {
    "timestamp": timestamp,
    "sectors": {}
}

for sector in SECTORS:
    data = fetch_sector_data(sector)
    # 投稿が少ない場合は前回内容をコピーして履歴に残す
    if data["score"] == "データ不足" and sector in previous_report.get("sectors", {}):
        report["sectors"][sector] = previous_report["sectors"][sector]
        report["sectors"][sector]["note"] = "前回データをコピー（新規投稿不足）"
    else:
        report["sectors"][sector] = data

# --- 保存 ---
filename = os.path.join(REPORT_DIR, f"report_{timestamp}.json")
with open(filename, "w", encoding="utf-8") as fp:
    json.dump(report, fp, ensure_ascii=False, indent=2)

print(f"Saved report: {filename}")
