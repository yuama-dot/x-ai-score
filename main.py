import os
import json
import shutil
import logging
import datetime
from pathlib import Path
from xai_sdk import Client
from xai_sdk.chat import user
from xai_sdk.tools import x_search

# --- ログ設定 ---
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

# --- 設定 ---
API_KEY = os.environ.get("XAI_API_KEY")
if not API_KEY:
    raise ValueError("XAI_API_KEY が設定されていません。Secrets に登録してください。")

MODEL = "grok-4-fast"
client = Client(api_key=API_KEY)

JST = datetime.timezone(datetime.timedelta(hours=+9))
now_jst = datetime.datetime.now(JST)
timestamp = now_jst.strftime("%Y%m%d_%H%M")
today = now_jst.strftime("%Y%m%d")

SECTORS: dict[str, list[str]] = {
    "メモリ": ["MU", "SK Hynix", "HBM"],
    "AIインフラ": ["$NVDA Blackwell", "NVDA earnings AI infrastructure", "NVIDIA datacenter demand"],
    "フォトニクス": ["住友電工", "CPO"],
    "マクロ": ["S&P500 tariff recession risk 2026"],
    "半導体素材/技術": ["from:paurooteri"],
}

# スコア → テキスト変換
SCORE_TO_SENTIMENT = {2: "強気", 1: "やや強気", 0: "中立", -1: "やや弱気", -2: "弱気"}
SCORE_TO_ARROW = {2: "▲▲", 1: "▲", 0: "→", -1: "▼", -2: "▼▼"}


# ─────────────────────────────────────────
# キャッシュ操作
# ─────────────────────────────────────────

def cache_path(sector: str, date: str) -> Path:
    safe_name = sector.replace(" ", "_").replace("/", "_")
    return Path("cache") / date / f"{safe_name}.json"


def load_cache(sector: str, date: str) -> dict | None:
    path = cache_path(sector, date)
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return None


def save_cache(sector: str, data: dict) -> None:
    path = cache_path(sector, today)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def find_prev_date() -> str | None:
    """今日より前で最も新しいキャッシュ日付を返す。"""
    cache_root = Path("cache")
    if not cache_root.exists():
        return None
    dates = sorted(
        (d.name for d in cache_root.iterdir() if d.is_dir() and d.name < today),
        reverse=True,
    )
    return dates[0] if dates else None


# ─────────────────────────────────────────
# API 呼び出し
# ─────────────────────────────────────────

def fetch_raw_content(sector: str, keywords: list[str]) -> str:
    prompt = (
        f"次のキーワードについて最新情報をXで調べ、"
        f"投稿の原文とURLを出力してください: {', '.join(keywords)}"
    )
    chat = client.chat.create(model=MODEL, tools=[x_search()])
    chat.append(user(prompt))
    return chat.sample().content


def score_content(sector: str, keywords: list[str], raw_content: str) -> dict:
    scoring_prompt = f"""
以下はX（旧Twitter）から取得した「{sector}」セクター（キーワード: {', '.join(keywords)}）に関する最新投稿です。

---
{raw_content}
---

この情報を投資家の視点で分析し、以下のJSON形式のみで回答してください。

{{
  "score": <-2〜+2の整数。+2=強気, +1=やや強気, 0=中立, -1=やや弱気, -2=弱気>,
  "sentiment": <"強気" | "やや強気" | "中立" | "やや弱気" | "弱気">,
  "reason": <スコアの根拠を2〜3文で説明>,
  "key_signals": [<重要シグナル1>, <重要シグナル2>, <重要シグナル3>]
}}
"""
    score_chat = client.chat.create(model=MODEL, response_format="json_object")
    score_chat.append(user(scoring_prompt))
    parsed = json.loads(score_chat.sample().content)

    # スコアを -2〜+2 に正規化
    raw_score = parsed.get("score")
    score = max(-2, min(2, int(raw_score))) if raw_score is not None else None

    return {
        "score": score,
        "sentiment": parsed.get("sentiment", SCORE_TO_SENTIMENT.get(score, "不明")),
        "reason": parsed.get("reason", ""),
        "key_signals": parsed.get("key_signals", []),
        "content": raw_content,
    }


# ─────────────────────────────────────────
# セクター処理
# ─────────────────────────────────────────

def process_sector(sector: str, keywords: list[str]) -> dict:
    cached = load_cache(sector, today)
    if cached:
        log.info(f"[{sector}] キャッシュ使用")
        return cached

    log.info(f"[{sector}] X検索中...")
    try:
        raw_content = fetch_raw_content(sector, keywords)
    except Exception as e:
        log.error(f"[{sector}] X検索エラー: {e}")
        return {"score": None, "sentiment": "エラー", "reason": str(e), "key_signals": [], "content": ""}

    if not raw_content or len(raw_content.strip()) < 50:
        log.warning(f"[{sector}] データ不足")
        return {
            "score": None, "sentiment": "データ不足",
            "reason": "取得投稿数が少ないため分析不能",
            "key_signals": [], "content": raw_content or "",
        }

    log.info(f"[{sector}] スコアリング中...")
    try:
        data = score_content(sector, keywords, raw_content)
    except json.JSONDecodeError as e:
        log.error(f"[{sector}] JSONパースエラー: {e}")
        data = {"score": None, "sentiment": "分析エラー", "reason": f"JSONパース失敗: {e}", "key_signals": [], "content": raw_content}
    except Exception as e:
        log.error(f"[{sector}] スコアリングエラー: {e}")
        data = {"score": None, "sentiment": "分析エラー", "reason": str(e), "key_signals": [], "content": raw_content}

    save_cache(sector, data)
    return data


# ─────────────────────────────────────────
# レポート生成
# ─────────────────────────────────────────

def score_cell(score: int | None, prev_score: int | None) -> str:
    if score is None:
        return "-"
    arrow = SCORE_TO_ARROW.get(score, "")
    if prev_score is not None and prev_score != score:
        diff = score - prev_score
        sign = "+" if diff > 0 else ""
        return f"{arrow} {score} ({sign}{diff})"
    return f"{arrow} {score}"


def overall_sentiment(avg: float) -> str:
    if avg >= 1.5:
        return "強気"
    if avg >= 0.5:
        return "やや強気"
    if avg >= -0.5:
        return "中立"
    if avg >= -1.5:
        return "やや弱気"
    return "弱気"


def generate_report(sector_results: dict, prev_results: dict, prev_date: str | None) -> str:
    lines: list[str] = []
    lines.append("# 週次ポートフォリオ X スキャンレポート")
    lines.append(f"更新: {now_jst.strftime('%Y-%m-%d %H:%M')} JST\n")

    # 総合スコア
    valid_scores = [d["score"] for d in sector_results.values() if isinstance(d.get("score"), int)]
    if valid_scores:
        avg = sum(valid_scores) / len(valid_scores)
        sentiment = overall_sentiment(avg)
        lines.append(f"## 総合スコア: **{avg:.1f}** / {sentiment}")
        prev_note = f"（前回: {prev_date}）" if prev_date else ""
        lines.append(f"> -2（弱気）〜 +2（強気）の平均スコア。スコア横の括弧は前回比{prev_note}。\n")

    # セクター別スコア表
    lines.append("## セクター別スコア")
    lines.append("| セクター | センチメント | スコア |")
    lines.append("|---------|------------|:-----:|")
    for sector, data in sector_results.items():
        prev_score = prev_results.get(sector, {}).get("score")
        cell = score_cell(data["score"], prev_score)
        lines.append(f"| {sector} | {data['sentiment']} | {cell} |")

    # セクター詳細
    lines.append("\n## セクター詳細")
    for sector, data in sector_results.items():
        score_display = data["score"] if data["score"] is not None else "-"
        lines.append(f"### {sector}（スコア: {score_display} / {data['sentiment']}）\n")
        if data.get("reason"):
            lines.append(f"**根拠**: {data['reason']}\n")
        if data.get("key_signals"):
            lines.append("**主要シグナル**:")
            for sig in data["key_signals"]:
                lines.append(f"- {sig}")
            lines.append("")
        lines.append(f"**Xポスト内容**:\n{data['content']}\n")
        lines.append("---\n")

    return "\n".join(lines)


# ─────────────────────────────────────────
# エントリーポイント
# ─────────────────────────────────────────

def main() -> None:
    sector_results = {
        sector: process_sector(sector, keywords)
        for sector, keywords in SECTORS.items()
    }

    prev_date = find_prev_date()
    prev_results = {}
    if prev_date:
        for sector in SECTORS:
            cached = load_cache(sector, prev_date)
            if cached:
                prev_results[sector] = cached

    report_content = generate_report(sector_results, prev_results, prev_date)

    report_file = f"report_{timestamp}.md"
    Path(report_file).write_text(report_content, encoding="utf-8")
    shutil.copy(report_file, "report.md")
    log.info(f"Report saved: {report_file}")


if __name__ == "__main__":
    main()
