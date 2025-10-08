# engine/generator.py
from openai import OpenAI
import os
import re
import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
PROMPTS_DIR = ROOT / "cw_prompts"

# ==========================================================
# 🔹 通用載入函式
# ==========================================================
def load_text(path: str | Path) -> str:
    """載入純文字檔案"""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"找不到檔案：{p}")
    return p.read_text(encoding="utf-8")


def load_json(path: str | Path):
    """載入 JSON 檔案"""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"找不到檔案：{p}")
    return json.loads(p.read_text(encoding="utf-8"))


# ==========================================================
# 🔹 文章品質基礎檢查
# ==========================================================
def basic_check(article: str) -> dict:
    """簡易檢查：字數、段落、引號"""
    chinese = len(re.findall(r"[\u4e00-\u9fff]", article))
    english = len(re.findall(r"\b[a-zA-Z]+\b", article))
    word_count = chinese + english
    paragraphs = len([b for b in article.split("\n\n") if b.strip()])
    quotes = len(re.findall(r"[「\"]", article))

    return {
        "word_count": word_count,
        "paragraphs": paragraphs,
        "quotes": quotes,
        "within_range": 1500 <= word_count <= 2000,
        "has_enough_quotes": quotes >= 5
    }


# ==========================================================
# 🔹 開場設定組裝（新版 JSON 規格）
# ==========================================================
def _build_opening_block(style_label: str, context: dict | str):
    """
    從新版 opening_styles.json 取出風格模板，帶入情境。
    支援錯誤檢查與自動引入禁止事項 / 品質清單。
    """
    data = load_json(PROMPTS_DIR / "opening_styles.json")

    styles = data.get("styles", {})
    general_rules = data.get("general_rules", {})
    schema = data.get("contextSchema", {})

    # 若風格不存在，使用預設值
    if style_label not in styles:
        style_label = "場景式"

    # 🔸 若 context 是字串，嘗試轉為 dict
    if isinstance(context, str):
        try:
            context = json.loads(context)
        except Exception:
            context = {"setting": context.strip()}

    # 🔸 檢查必要欄位
    required = schema.get("required", {}).keys()
    missing = [k for k in required if not context.get(k)]
    if missing:
        raise ValueError(f"缺少必要採訪情境資料（{', '.join(missing)}），無法生成開場。")

    style = styles[style_label]

    # 🔸 整理禁止事項與品質檢查
    forbid_list = general_rules.get("禁止事項", [])
    quality_list = general_rules.get("品質檢查清單", [])

    forbid = "\n".join([f"- {r}" for r in forbid_list])
    quality = "\n".join(quality_list)

    # 🔸 整理寫作指引
    writing_tips = ""
    if "寫作指引" in style:
        writing_tips = "\n".join([f"- {k}：{v}" for k, v in style["寫作指引"].items()])

    # 🔸 JSON 格式化的情境顯示
    context_desc = json.dumps(context, ensure_ascii=False, indent=2)

    # 🔸 組合開場說明區塊
    return f"""開場風格：{style_label}

採訪情境（依據 contextSchema 提供）：
{context_desc}

寫作指令：
{style.get('instructions', '（無特定指令）')}

寫作指引：
{writing_tips or '（無特別指引）'}

禁止事項：
{forbid}

品質檢查清單：
{quality}
"""


# ==========================================================
# 🔹 主函式：文章生成
# ==========================================================
def generate_article(
    subject: str,
    company: str,
    people: str,
    participants: str,
    transcript: str,
    summary_points: str,
    opening_style: str = "場景式",
    opening_context: dict | str = "",
    word_count_range: tuple | None = None,
    paragraphs: int | None = None,
    api_key: str | None = None
) -> tuple[str, dict, int]:
    """
    生成專訪文章。
    回傳：(文章內容, 檢查結果 dict, 修稿次數)
    """
    client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))

    # 載入 prompts
    system_prompt = load_text(PROMPTS_DIR / "system_style.txt")
    template_prompt = load_text(PROMPTS_DIR / "article_template.txt")

    # === 產出限制 ===
    constraints_lines = []
    if word_count_range and len(word_count_range) == 2:
        constraints_lines.append(
            f"全文字數必須在 {word_count_range[0]}–{word_count_range[1]} 字之間。"
        )
    if paragraphs:
        constraints_lines.append(
            f"主體段落固定為 {paragraphs} 段，每段約 300–400 字。"
        )

    constraints_lines.extend([
        "全文至少包含 5 則以上的受訪者直接引言（使用「」標示）。",
        "每一個段落都必須有清楚的小標題，使用『### 小標題』格式標示。",
        "開場段落 150–200 字，需自然銜接主題，允許 ±20 字。"
    ])
    constraints_text = "\n".join(constraints_lines)

    # === 開場設定區塊（新版）===
    opening_block = _build_opening_block(opening_style, opening_context)

    # === 使用者輸入組裝 ===
    user_prompt = f"""請依照以下文章模板生成一篇完整專訪文章。

=== 文章模板 ===
{template_prompt}

=== 產出限制 ===
{constraints_text}

=== 開場設定（必須遵循） ===
{opening_block}

=== 使用者資料 ===
主題：{subject}
企業名稱：{company}
人物姓名：{people}
受訪者清單：{participants}

逐字稿（已清理）：
{transcript}

重點摘要：
{summary_points}
"""

    # ==========================================================
    # 🔹 呼叫模型
    # ==========================================================
    def call_model(prompt: str, sys: str, temperature=0.7, max_tokens=3500) -> str:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": sys},
                {"role": "user", "content": prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens
        )
        return resp.choices[0].message.content.strip()

    # === 第一次生成 ===
    article = call_model(user_prompt, system_prompt)
    checks = basic_check(article)

    # ==========================================================
    # 🔹 自動修稿循環
    # ==========================================================
    max_retries, retry_count = 2, 0
    while (not checks["within_range"] or not checks["has_enough_quotes"]) and retry_count < max_retries:
        fix_prompt = f"""以下是初稿文章，請依需求修正（保持語氣與內容）：

=== 修正要求 ===
{constraints_text}

=== 開場設定 ===
{opening_block}

=== 初稿 ===
{article}

請根據「開場設定」及「通用規則」修正篇幅與結構，
避免重複或拖沓，確保語氣自然流暢。
"""
        article = call_model(
            fix_prompt,
            "你是專業編輯，負責調整文章結構與篇幅。",
            temperature=0.5
        )
        checks = basic_check(article)
        retry_count += 1

    return article, checks, retry_count


# ==========================================================
# 🔹 測試執行
# ==========================================================
if __name__ == "__main__":
    try:
        context_example = {
            "interviewee": "張瑋，建築師",
            "topic": "舊城再生計畫",
            "transcript": "「那裡以前是我爸的印刷廠。」",
            "setting": "台中舊市區老工廠",
            "datetime": "2025年5月午後",
            "background": "第二代創業者",
            "keyData": "城市更新第三期，投入經費2.3億元"
        }

        article, checks, retries = generate_article(
            subject="舊城再生與青年創業",
            company="築城設計事務所",
            people="張瑋",
            participants="張瑋、設計團隊",
            transcript="這是訪談逐字稿內容...",
            summary_points="1. 舊城空間再利用\n2. 青年返鄉創業\n3. 綠建築理念推廣",
            opening_style="場景式",
            opening_context=context_example,
            word_count_range=(1500, 2000),
            paragraphs=3
        )

        print(article[:500])
        print("\n=== 檢查結果 ===")
        print(checks)
        print(f"修稿次數: {retries}")

    except Exception as e:
        print(f"❌ 錯誤: {e}")
