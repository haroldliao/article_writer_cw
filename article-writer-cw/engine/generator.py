from openai import OpenAI
import os
import re
from selector import load_style  # 🔧 新增：載入 style_xxx.md

def load_prompt(path: str) -> str:
    """載入 prompt 檔案,包含錯誤處理"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        raise FileNotFoundError(f"找不到 prompt 檔案: {path}")
    except Exception as e:
        raise Exception(f"讀取檔案 {path} 時發生錯誤: {str(e)}")


def basic_check(article: str) -> dict:
    """基礎檢查文章品質"""
    word_count = len(article)
    paragraphs = article.count("\n\n") + 1
    quotes = len(re.findall(r"[「\"]", article))
    
    return {
        "word_count": word_count,
        "paragraphs": paragraphs,
        "quotes": quotes,
        "within_range": 1500 <= word_count <= 2000,
        "has_enough_quotes": quotes >= 5
    }


def generate_article(
    subject: str,
    company: str,
    people: str,
    participants: str,
    transcript: str,
    summary_points: str,
    style_label: str = "企業",  # 🔧 新增：使用者選的風格類型
    word_count_range: tuple | None = None,
    paragraphs: int | None = None,
    api_key: str | None = None
) -> tuple[str, dict, int]:
    """
    根據訪談資料生成文章,若檢查不通過會自動修稿
    
    Returns:
        (文章內容, 檢查結果 dict, 修稿次數)
    """
    client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
    
    # 載入 prompts
    system_prompt = load_prompt("cw_prompts/system_style.txt")
    template_prompt = load_prompt("cw_prompts/article_template.txt")
    style_prompt = load_style(style_label)  # 🔧 新增：讀取 style_xxx.md
    
    def call_model(user_prompt: str, system_prompt: str, temperature=0.7, max_tokens=3500) -> str:
        """呼叫 OpenAI API 生成內容"""
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content.strip()
    
    # 第一次生成
    constraints_lines = []
    if word_count_range and len(word_count_range) == 2:
        constraints_lines.append(
            f"全文字數必須在 {word_count_range[0]}–{word_count_range[1]} 字之間,低於範圍不可接受。"
        )
    if paragraphs:
        constraints_lines.append(
            f"主體段落必須固定為 {paragraphs} 段,每段約 300–400 字,其他段落不可額外新增。"
        )
    constraints_lines.append("全文至少包含 5 則以上的受訪者直接引言(使用「」標示)。")
    constraints_lines.append("每一個段落都必須有清楚的小標題,使用『### 小標題』格式標示。")
    
    constraints_text = "\n".join(constraints_lines)
    
    user_prompt = f"""
請依照以下文章模板,生成一篇完整專訪文章。

=== 文章模板 ===
{template_prompt}

=== 文章風格要求 ===
{style_prompt}

=== 產出限制 ===
{constraints_text}

=== 使用者資料 ===
主題: {subject}
企業名稱: {company}
人物姓名: {people}
受訪者清單: {participants}

逐字稿(已清理):
{transcript}

重點摘要:
{summary_points}
"""
    
    article = call_model(user_prompt, system_prompt)
    checks = basic_check(article)
    
    # 自動修稿流程
    max_retries = 2
    retry_count = 0
    
    while (not checks["within_range"] or not checks["has_enough_quotes"]) and retry_count < max_retries:
        fix_prompt = f"""
以下是初稿文章,請根據以下要求進行修正:

- 字數必須達到 {word_count_range[0]}–{word_count_range[1]} 字
- 主體段落固定為 {paragraphs} 段,每段 300–400 字
- 至少加入 5 則受訪者直接引言(「」)
- 每一個段落都必須有清楚的小標題,使用『### 小標題』格式標示
- 保留原本的風格與內容,僅調整結構與篇幅

初稿:
{article}
"""
        article = call_model(fix_prompt, "你是專業編輯,負責調整文章結構與篇幅。", temperature=0.5)
        checks = basic_check(article)
        retry_count += 1
    
    return article, checks, retry_count


# 測試用
if __name__ == "__main__":
    try:
        article, checks, retries = generate_article(
            subject="數位轉型成功案例",
            company="某某科技公司",
            people="張執行長",
            participants="張執行長、李技術長",
            transcript="這是訪談內容...",
            summary_points="1. 成功導入 AI\n2. 提升效率 30%",
            style_label="企業",  # 🔧 測試指定風格
            word_count_range=(1500, 2000),
            paragraphs=3
        )
        print(article[:500])
        print("\n=== 檢查結果 ===")
        print(checks)
        print(f"修稿次數: {retries}")
    except Exception as e:
        print(f"錯誤: {e}")
