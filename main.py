# main.py
import datetime
from xai_sdk import Client
from xai_sdk.chat import user
from xai_sdk.tools import x_search
import os
import markdown

# ==== APIキー設定 ====
API_KEY = os.environ.get("XAI_API_KEY")
client = Client(api_key=API_KEY)

# ==== 関数定義 ====
def x_sentiment(topic, lang="ja"):
    lang_note = {"ja": "日本語の投稿を中心に", "en": "英語の投稿を中心に", "both": "日英両方の投稿を"}[lang]
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    prompt = f"""X（Twitter）で「{topic}」について{lang_note}最新情報を検索し、以下の形式で出力してください。

【検索トピック】{topic}
【検索日時】{now}

【センチメント】強気/弱気/中立のいずれか
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

URLだけでなく必ず投稿本文テキストを含めること。"""

    chat = client.chat.create(
        model="grok-4-1-fast",
        tools=[x_search()],
    )
    chat.append(user(prompt))
    response = chat.sample()
    return response.content

def x_user_check(handle: str, topic: str):
    prompt = f"""@{handle}の最新投稿を検索し、「{topic}」に関連する内容があれば本文・日時・URLとともに紹介してください。
関連投稿がなければ「関連投稿なし」と返してください。"""
    chat = client.chat.create(
        model="grok-4-1-fast",
        tools=[x_search(allowed_x_handles=[handle])],
    )
    chat.append(user(prompt))
    response = chat.sample()
    return response.content

# ==== 検索リスト ====
SEARCHES = [
    ("Micron MU HBM4 AI memory Vera Rubin", "en"),
    ("HBM4 SK Hynix Samsung memory AI chip", "en"),
    ("NVIDIA NVDA Blackwell GB300 datacenter", "en"),
    ("AI infrastructure hyperscaler capex 2026", "en"),
    ("S&P500 AI tariff recession sentiment", "both"),
    ("住友電工 フォトニクス CPO 光トランシーバ", "ja"),
    ("CPO co-packaged optics photonics InP wafer", "en"),
]

# ==== レポート生成 ====
timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
report_name = f"report_{timestamp}.md"

with open(report_name, "w", encoding="utf-8") as f:
    f.write(f"# 📊 AI市場レポート\n\n更新: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")

    # 特定アカウントチェック
    f.write("## === @paurooteri チェック ===\n")
    result = x_user_check("paurooteri", "AI memory photonics CPO HBM")
    f.write(result + "\n\n")

    f.write("## === ポートフォリオスキャン ===\n")
    for topic, lang in SEARCHES:
        f.write(f"\n### {topic}\n")
        result = x_sentiment(topic, lang=lang)
        f.write(result + "\n")

# 最新版コピー
with open("latest.md", "w", encoding="utf-8") as f:
    with open(report_name, "r", encoding="utf-8") as src:
        f.write(src.read())

# ==== HTML変換 ====
with open(report_name, "r", encoding="utf-8") as md_file:
    md_text = md_file.read()

html_content = markdown.markdown(md_text, extensions=['tables'])
html_template = f"""
<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI市場レポート</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Helvetica Neue', sans-serif; padding: 10px; line-height: 1.6; }}
h1,h2,h3 {{ color: #333; }}
a {{ color: #1a0dab; text-decoration: none; }}
table {{ border-collapse: collapse; width: 100%; margin: 10px 0; }}
th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
th {{ background-color: #f2f2f2; }}
</style>
</head>
<body>
{html_content}
</body>
</html>
"""

with open("latest.html", "w", encoding="utf-8") as html_file:
    html_file.write(html_template)

print("レポート生成完了:", report_name, "／最新HTML: latest.html")
