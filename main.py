import os
import datetime
import json
from pathlib import Path
from xai_sdk import Client
from xai_sdk.chat import user
from xai_sdk.tools import x_search

# — 設定 —

API_KEY = os.environ.get(“XAI_API_KEY”)
if not API_KEY:
raise ValueError(“XAI_API_KEY が設定されていません。Secrets に登録してください。”)

client = Client(api_key=API_KEY)

JST = datetime.timezone(datetime.timedelta(hours=+9))
now_jst = datetime.datetime.now(JST)
timestamp = now_jst.strftime(”%Y%m%d_%H%M”)
today = now_jst.strftime(”%Y%m%d”)

sectors = {
“メモリ”: [“MU”, “SK Hynix”, “HBM”],
“AIインフラ”: [“NVDA”, “NVIDIA”],
“フォトニクス”: [“住友電工”, “CPO”],
“マクロ”: [“S&P500 tariff recession risk 2026”]
}

# キャッシュは日付ごとに分離

cache_dir = Path(“cache”) / today
cache_dir.mkdir(parents=True, exist_ok=True)

sector_results = {}

for sector, keywords in sectors.items():
cache_file = cache_dir / f”{sector.replace(’ ’, ‘_’)}.json”

```
if cache_file.exists():
    with open(cache_file, "r", encoding="utf-8") as f:
        sector_results[sector] = json.load(f)
    print(f"[{sector}] キャッシュ使用")
    continue

print(f"[{sector}] X検索中...")

# =========================================
# Stage 1: X検索
# =========================================
try:
    prompt_text = (
        f"次のキーワードについて最新情報をXで調べ、"
        f"投稿の原文とURLを出力してください: {', '.join(keywords)}"
    )
    chat = client.chat.create(model="grok-4-fast", tools=[x_search()])
    chat.append(user(prompt_text))
    search_response = chat.sample()
    raw_content = search_response.content

except Exception as e:
    print(f"[{sector}] X検索エラー: {e}")
    sector_results[sector] = {
        "score": None, "sentiment": "エラー",
        "reason": str(e), "key_signals": [], "content": ""
    }
    continue

if not raw_content or len(raw_content.strip()) < 50:
    print(f"[{sector}] データ不足")
    sector_results[sector] = {
        "score": None, "sentiment": "データ不足",
        "reason": "取得投稿数が少ないため分析不能",
        "key_signals": [], "content": raw_content
    }
    continue

# =========================================
# Stage 2: センチメント分析
# response_format='json_object' でJSON出力を強制
# =========================================
print(f"[{sector}] スコアリング中...")
try:
    scoring_prompt = f"""
```

以下はX（旧Twitter）から取得した「{sector}」セクター（キーワード: {’, ’.join(keywords)}）に関する最新投稿です。

-----

## {raw_content}

この情報を投資家の視点で分析し、以下のJSON形式で回答してください。

{{
“score”: <-2〜+2の整数。+2=強気, +1=やや強気, 0=中立, -1=やや弱気, -2=弱気>,
“sentiment”: <“強気” | “やや強気” | “中立” | “やや弱気” | “弱気”>,
“reason”: <スコアの根拠を2〜3文で説明>,
“key_signals”: [<重要シグナル1>, <重要シグナル2>, <重要シグナル3>]
}}
“””
score_chat = client.chat.create(
model=“grok-4-fast”,
response_format=“json_object”  # JSON出力を強制
)
score_chat.append(user(scoring_prompt))
score_response = score_chat.sample()

```
    parsed = json.loads(score_response.content)

    data = {
        "score": parsed.get("score"),
        "sentiment": parsed.get("sentiment", "不明"),
        "reason": parsed.get("reason", ""),
        "key_signals": parsed.get("key_signals", []),
        "content": raw_content
    }

except json.JSONDecodeError as e:
    print(f"[{sector}] JSONパースエラー: {e}")
    data = {
        "score": None, "sentiment": "分析エラー",
        "reason": f"JSONパース失敗: {e}",
        "key_signals": [], "content": raw_content
    }
except Exception as e:
    print(f"[{sector}] スコアリングエラー: {e}")
    data = {
        "score": None, "sentiment": "分析エラー",
        "reason": str(e), "key_signals": [], "content": raw_content
    }

with open(cache_file, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

sector_results[sector] = data
```

# =========================================

# レポート作成（アクション判断はClaudeに委任）

# =========================================

report_file = f”report_{timestamp}.md”
with open(report_file, “w”, encoding=“utf-8”) as f:
f.write(f”# 週次ポートフォリオ X スキャンレポート\n”)
f.write(f”更新: {now_jst.strftime(’%Y-%m-%d %H:%M’)} JST\n\n”)

```
f.write("## セクター別スコア\n")
f.write("| セクター | センチメント | スコア |\n")
f.write("|---------|------------|:-----:|\n")
for sector, data in sector_results.items():
    score_display = data["score"] if data["score"] is not None else "-"
    f.write(f"| {sector} | {data['sentiment']} | {score_display} |\n")

f.write("\n## セクター詳細\n")
for sector, data in sector_results.items():
    score_display = data["score"] if data["score"] is not None else "-"
    f.write(f"### {sector}（スコア: {score_display} / {data['sentiment']}）\n\n")

    if data.get("reason"):
        f.write(f"**根拠**: {data['reason']}\n\n")

    if data.get("key_signals"):
        f.write("**主要シグナル**:\n")
        for sig in data["key_signals"]:
            f.write(f"- {sig}\n")
        f.write("\n")

    f.write(f"**Xポスト内容**:\n{data['content']}\n\n")
    f.write("---\n\n")
```

print(f”Report saved to {report_file}”)
