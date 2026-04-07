# -*- coding: utf-8 -*-
"""
週次ポートフォリオ X スキャンレポート 自動生成（過去トレンド反映版）
改善ポイント:
1. 過去1〜2週間の投稿トレンドをスコアに反映
2. アクション候補欄は削除
3. 投稿数3件未満は「データ不足」
"""

import os
from datetime import datetime, timezone, timedelta
from xai_sdk import Client

# ===== 環境変数からAPIキー取得 =====
API_KEY = os.environ.get("XAI_API_KEY")
if not API_KEY:
    raise ValueError("XAI_API_KEYが設定されていません。GitHub Secretsに登録してください。")
client = Client(api_key=API_KEY)

# ===== タイムスタンプ（日本時間） =====
JST = timezone(timedelta(hours=+9))
now = datetime.now(JST)
timestamp_str = now.strftime("%Y-%m-%d %H:%M")

# ===== セクター設定 =====
sectors = {
    "メモリ": {"keywords": ["MU", "HBM"], "weight": 1.2},
    "AIインフラ": {"keywords": ["NVDA", "AI Server"], "weight": 1.5},
    "フォトニクス": {"keywords": ["住友電工", "CPO"], "weight": 1.1},
    "マクロ": {"keywords": ["S&P500", "tariff", "recession", "GDP", "interest rate"], "weight": 1.0}
}

# ===== 投稿取得・スコアリング関数 =====
def calc_sector_score(posts, past_posts=None, sector_weight=1.0):
    """
    スコアリング基準:
    - 投稿件数 < 3 → "データ不足"
    - 投稿強度: 弱い(+/-1), 強い(+/-2)
    - インフルエンサー投稿は重み1.5倍
    - 過去トレンド補正: 過去投稿の平均に0.3補正
    """
    if len(posts) < 3:
        return "データ不足"
    
    total_weighted_score = 0
    total_weight = 0
    
    for post in posts:
        base_score = post.get("score", 0)
        influence_weight = 1.5 if post.get("user") in ["Cointelegraph", "TradexWhisperer"] else 1.0
        total_weighted_score += base_score * influence_weight
        total_weight += influence_weight

    current_score = total_weighted_score / total_weight
    
    # 過去投稿補正
    if past_posts:
        past_score = sum(p.get("score",0) for p in past_posts) / max(len(past_posts),1)
        trend_weight = 0.3  # 過去投稿の影響度
        current_score = current_score * (1 - trend_weight) + past_score * trend_weight

    # セクター重み反映
    current_score *= sector_weight
    return round(current_score)

# ===== 各セクターの投稿取得（仮データ） =====
mock_posts_current = {
    "メモリ": [{"score": 2, "user": "TradexWhisperer"}, {"score": 1, "user": "一般"}, {"score": 1, "user": "一般"}],
    "AIインフラ": [{"score": 2, "user": "Cointelegraph"}, {"score": 2, "user": "一般"}, {"score": 1, "user": "一般"}],
    "フォトニクス": [{"score": 1, "user": "一般"}, {"score": 1, "user": "一般"}, {"score": 2, "user": "一般"}],
    "マクロ": [{"score": -1, "user": "一般"}, {"score": 0, "user": "一般"}, {"score": 1, "user": "一般"}]
}

mock_posts_past = {
    "メモリ": [{"score": 1, "user": "一般"}, {"score": 1, "user": "一般"}],
    "AIインフラ": [{"score": 1, "user": "一般"}, {"score": 2, "user": "一般"}],
    "フォトニクス": [{"score": 1, "user": "一般"}],
    "マクロ": [{"score": 0, "user": "一般"}]
}

# ===== スコア計算 =====
sector_scores = {}
for sector, info in sectors.items():
    posts = mock_posts_current.get(sector, [])
    past_posts = mock_posts_past.get(sector, [])
    sector_scores[sector] = calc_sector_score(posts, past_posts=past_posts, sector_weight=info["weight"])

# ===== 総合スコア（有効セクター平均） =====
valid_scores = [s for s in sector_scores.values() if isinstance(s, int)]
total_score = round(sum(valid_scores)/len(valid_scores)) if valid_scores else "データ不足"

# ===== レポート作成 =====
report_lines = [
    f"# 週次ポートフォリオ X スキャンレポート",
    f"更新: {timestamp_str}",
    "",
    "## 総合サマリー",
    "全セクター横断で市場のセンチメントをまとめています。",
    "",
    "## セクター別スコア",
    "| セクター | センチメント | スコア |",
    "|---------|------------|-------|"
]

for sector, score in sector_scores.items():
    sentiment = "強気" if isinstance(score,int) and score>0 else "弱気" if isinstance(score,int) and score<0 else "データ不足"
    report_lines.append(f"| {sector} | {sentiment} | {score} |")

# ===== ファイル出力 =====
output_file = f"report_{now.strftime('%Y%m%d_%H%M')}.md"
with open(output_file, "w", encoding="utf-8") as f:
    f.write("\n".join(report_lines))

print(f"レポート生成完了: {output_file}")
