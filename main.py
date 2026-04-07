import os
import datetime
from xai_sdk import Client
from xai_sdk.chat import user
from xai_sdk.tools import x_search

# =========================
# 🔐 APIキー
# =========================
API_KEY = os.getenv("XAI_API_KEY")
client = Client(api_key=API_KEY)

# =========================
# 🎯 分析トピック
# =========================
TOPIC = "NVIDIA HBM AI datacenter"

# =========================
# 📊 分析関数（透明スコア）
# =========================
def analyze(topic):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    prompt = f"""
Xで「{topic}」を分析：

【目的】
投資判断に使える透明な分析

【出力形式（必ず守る）】

# 📊 AI市場レポート

更新: {now}

---

## 🧭 センチメント
強気 / 中立 / 弱気

---

## 📊 スコア内訳
・ポジティブ投稿数：◯件
・ネガティブ投稿数：◯件
・中立投稿数：◯件

---

## 🔍 重要根拠（必ずURL付き）
1. 理由 + URL
2. 理由 + URL
3. 理由 + URL

---

## 👀 インフルエンサー意見
・@ユーザー名：意見 + URL

---

## 🧮 総合スコア
+3 〜 -3 で評価

---

## 💡 判断理由
なぜそのスコアかを簡潔に説明
"""

    chat = client.chat.create(
        model="grok-4-1-fast",
        tools=[x_search()],
    )
    chat.append(user(prompt))

    return chat.sample().content


# =========================
# 🚀 実行
# =========================
if __name__ == "__main__":
    result = analyze(TOPIC)

    # ⏱️ タイムスタンプ
    now = datetime.datetime.now().strftime("%Y%m%d_%H%M")

    # 📁 履歴ファイル
    history_filename = f"report_{now}.md"

    # 📌 最新ファイル
    latest_filename = "latest.md"

    # 保存（履歴）
    with open(history_filename, "w") as f:
        f.write(result)

    # 保存（最新）
    with open(latest_filename, "w") as f:
        f.write(result)

    print(f"Saved: {history_filename}")
    print("Updated: latest.md")
