import openai
from typing import Dict, Tuple, Optional
from engine.template_loader import load_article_template  # ✅ 新增：讀取模板

def generate_article(
    subject: str,
    company: str,
    people: Optional[str],
    participants: str,
    transcript: str,
    summary_points: str,
    opening_style: str,
    opening_context: str,
    paragraphs: int,
    api_key: str,
    model: str = "gpt-4o-mini",
    max_completion_tokens: int = 4000
) -> Tuple[str, Dict, int]:
    """
    生成專訪文章（最終整合版）
    支援多位受訪者權重、開場風格、採訪情境與模板結構輸出
    """

    openai.api_key = api_key

    # === 解析受訪者資訊 ===
    participants_info = []
    for line in participants.split('\n'):
        line = line.strip()
        if not line:
            continue
        parts = line.split('／')
        if len(parts) == 3:
            participants_info.append({
                "name": parts[0],
                "title": parts[1],
                "weight": parts[2]
            })

    participants_desc = "\n".join([
        f"- {p['name']}（{p['title']}）- {'主軸人物' if p['weight'] == '1' else '輔助人物'}"
        for p in participants_info
    ]) or "（未提供受訪者資料）"

    # === 載入文章模板 ===
    template_text = load_article_template()

    # === 通用內容規範 ===
    writing_guidelines = f"""
【撰寫要求】
1. 文章結構：
   - 主標題使用「#」
   - 各段落小標題使用「##」
   - 段落結構：開場 + {paragraphs} 段主體 + 結語
2. 開場段落：
   - 風格：{opening_style}
   - 自然融入採訪情境：{opening_context or '（無特定描述）'}
3. 引言規範：
   - 使用「」包住受訪者直接引述的話
   - 主軸人物（權重1）引用比例應佔 60–70%
   - 輔助人物（權重2）平均分配剩餘篇幅
4. 語氣與風格：
   - 專業、真實、有臨場感
   - 避免過度形容詞與推銷語氣
5. 字數建議：
   - 每段 300–500 字
   - 全文約 1500–2500 字
6. 段落邏輯：
   - 開場：設定氛圍與主題導入
   - 主體：每段聚焦一個核心觀點或轉折
   - 結語：收斂價值觀、展望未來
"""

    # === 根據模型類型組裝 Prompt ===
    if model.startswith("o1"):
        # o1 系列不支援 system role
        prompt = f"""你是一位專業的商業與人物專訪撰稿人。請根據以下資料生成一篇具有深度與敘事感的完整報導。

【文章資訊】
主題：{subject}
企業：{company}
段落數：{paragraphs}

【受訪者資訊】
{participants_desc}

【逐字稿內容】
{transcript}

【重點摘要】
{summary_points or '（無特定摘要）'}

{writing_guidelines}

【參考文章模板】
{template_text}

請直接輸出完整文章（含主標題與 Markdown 結構）。
"""
        messages = [{"role": "user", "content": prompt}]

    else:
        # gpt-4o / gpt-4o-mini
        system_prompt = """你是一位專業的專訪報導撰稿人，擅長將逐字稿轉化為具敘事感與邏輯結構的完整文章。

你的風格：
- 善用開場畫面或引句吸引讀者
- 清楚鋪陳多人物的觀點與互動
- 精準引用語錄，不誇飾
- 結構嚴謹且語氣流暢
- 使用 Markdown 層級標題呈現文章結構"""

        user_prompt = f"""請根據以下資料撰寫完整專訪文章：

【文章資訊】
主題：{subject}
企業：{company}
段落數：{paragraphs}
開場風格：{opening_style}

【受訪者資訊】
{participants_desc}

【採訪情境】
{opening_context or '（無特定描述）'}

【逐字稿內容】
{transcript}

【重點摘要】
{summary_points or '（無特定摘要）'}

{writing_guidelines}

【參考文章模板】
{template_text}

請輸出完整文章（含主標題 # 與小標題 ##），
段落之間請以空行分隔，保持 Markdown 格式。
"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

    # === 呼叫 API ===
    max_retries = 3
    retries = 0
    article, checks = "", {}

    for attempt in range(max_retries):
        try:
            if model.startswith("o1"):
                response = openai.ChatCompletion.create(
                    model=model,
                    messages=messages,
                    max_completion_tokens=max_completion_tokens
                )
            else:
                response = openai.ChatCompletion.create(
                    model=model,
                    messages=messages,
                    max_tokens=max_completion_tokens,
                    temperature=0.7,
                    top_p=0.9
                )

            article = response.choices[0].message.content.strip()
            checks = quality_check(article, paragraphs, participants_info)

            # 若品質檢查通過則提前返回
            if all(checks.values()):
                return article, checks, retries

            retries += 1

        except Exception as e:
            retries += 1
            if attempt == max_retries - 1:
                raise Exception(f"API 呼叫失敗：{str(e)}")

    return article, checks, retries


# === 品質檢查 ===
def quality_check(article: str, expected_paragraphs: int, participants: list) -> Dict[str, bool]:
    """
    品質檢查：
    - 標題結構
    - 段落數量
    - 引言格式
    - 字數充分
    - 主軸人物提及
    - 避免空泛詞彙
    """
    checks = {}

    # 1️⃣ 標題檢查
    checks["包含主標題"] = article.startswith("#")

    # 2️⃣ 段落數檢查（允許 ±1 誤差）
    actual_paragraphs = article.count("\n\n")
    checks["段落數符合"] = abs(actual_paragraphs - expected_paragraphs) <= 1

    # 3️⃣ 引言檢查
    checks["包含引言"] = "「" in article and "」" in article

    # 4️⃣ 字數檢查
    word_count = len(article.replace(" ", "").replace("\n", ""))
    checks["字數充足"] = word_count >= 1500

    # 5️⃣ 主軸人物檢查
    main_names = [p["name"] for p in participants if p["weight"] == "1"]
    checks["提及主軸人物"] = (
        any(name in article for name in main_names) if main_names else True
    )

    # 6️⃣ 避免空泛詞彙
    filler_words = ["非常成功", "十分重要", "極為關鍵", "相當優秀", "令人感動", "展現非凡"]
    checks["避免空泛詞彙"] = not any(word in article for word in filler_words)

    return checks
