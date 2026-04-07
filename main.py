# -*- coding: utf-8 -*-
"""
x-ai-research 全部入り版
更新: 2026-04-07
"""

!pip install openai xai-sdk --quiet
import datetime
import os
from xai_sdk import Client
from xai_sdk.chat import user
from xai_sdk.tools import x_search

# --- API設定 ---
API_KEY = os.environ.get("XAI_API_KEY", "ここにあなたのXAI_API_KEYをセット")
client = Client(api_key=API_KEY)

# --- 定義関数 ---

def x_sentiment(topic, lang="ja"):
    """トピック別センチメント分析（本文＋URL）"""
    lang_note = {"ja": "日本語の投稿を中心に", "en": "英語の投稿を中心に", "both": "日英両方の投稿を"}[lang]
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    prompt = f"""
Xで「{topic}」について{lang_note}最新情報を検索し、以下の形式で出力してください。

【検索トピック】{topic}
【検索日時】{now}

【センチメント】強気/弱気/中立
【根拠】1〜2文で具体的に

【キーワード】キーワード1 / キーワード2 / キーワード3

【市場の声まとめ】
Xで見られる意見・論調を200〜300字でまとめた段落テキスト。箇条書きではなく文章で。

【注目ポスト】
1. @投稿者名
   「投稿本文の全文」
   URL

2. @投稿者名
   「投稿本文の全文」
   URL

3. @投稿者名
   「投稿本文の全文」
   URL

※必ず投稿本文も含めること
"""
    chat = client.chat.create(model="grok-4-1-fast", tools=[x_search()])
    chat.append(user(prompt))
    response = chat.sample()
    return response.content

def x_user_check(handle: str, topic: str):
    """特定アカウント監視"""
    prompt = f"""
@{handle}の最新投稿を検索し、「{topic}」に関連する内容があれば本文・日時・URLとともに紹介してください。
関連投稿がなければ「関連投稿なし」と返してください。
"""
    chat = client.chat.create(model="grok-4-1-fast", tools=[x_search(allowed_x_handles=[handle])])
    chat.append(user(prompt))
    response = chat.sample()
    return response.content

def calculate_score(posts_summary):
    """ポジティブ/ネガティブ比率から過熱度と総合スコアを算出"""
    pos = posts_summary.get("pos", 0)
    neg = posts_summary.get("neg", 0)
    neu = posts_summary.get("neu", 0)
    total = pos + neg + neu
    heat_ratio = pos / total if total > 0 else 0
    if heat_ratio > 0.7:
        phase = "過熱"
    elif heat_ratio >= 0.5:
        phase = "健全強気"
    else:
        phase = "弱気"
    score = 0
    if pos > neg:
        score += 1
    if heat_ratio > 0.7:
        score -= 1
    return {"heat_ratio": round(heat_ratio*100,1), "phase": phase, "score": score}

# --- トピック設定 ---
SEARCHES = [
    ("Micron MU HBM4 AI memory Vera Rubin", "en"),
    ("HBM4 SK Hynix Samsung memory AI chip", "en"),
    ("NVIDIA NVDA Blackwell GB300 datacenter", "en"),
    ("AI infrastructure hyperscaler capex 2026", "en"),
    ("S&P500 AI tariff recession sentiment", "both"),
    ("住友電工 フォトニクス CPO 光トランシーバ", "ja"),
    ("CPO co-packaged optics photonics InP wafer", "en"),
]

# --- 実行 ---
results = []

results.append(f"# 📊 AI市場レポート\n更新: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}\n")

# paurooteri監視
results.append("## 👀 注目アカウント @paurooteri\n")
results.append(x_user_check("paurooteri", "AI 半導体 HBM CPO"))

# トピックごとセンチメント解析
for topic, lang in SEARCHES:
    results.append("\n" + "="*50 + "\n")
    results.append(f"### トピック: {topic}")
    sentiment = x_sentiment(topic, lang)
    results.append(sentiment)

# --- 履歴保存 ---
timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
filename = f"report_{timestamp}.md"
with open(filename, "w", encoding="utf-8") as f:
    f.write("\n".join(results))

# 最新コピー
with open("latest.md", "w", encoding="utf-8") as f:
    f.write("\n".join(results))

print(f"レポートを保存しました: {filename}")
