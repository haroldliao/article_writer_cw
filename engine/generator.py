from openai import OpenAI
from typing import Dict, Tuple, Optional, List, TypedDict
from engine.template_loader import load_template

class ParticipantInfo(TypedDict):
    name: str
    title: str
    weight: str


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
    max_tokens: int = 4000
) -> Tuple[str, Dict, int]:
    """
    生成專訪文章（支援長逐字稿安全模式 + openai>=1.0）
    """
    client = OpenAI(api_key=api_key)
    participants_info = _parse_participants(participants)
    participants_desc = _format_participants(participants_info)

    # === 檢查逐字稿長度 ===
    transcript_length = len(transcript.replace(" ", "").replace("\n", ""))
    safe_mode = transcript_length > 8000
    compressed_transcript = transcript

    if safe_mode:
        print(f"⚠️ 啟用長逐字稿安全模式：逐字稿長度約 {transcript_length} 字")
        compressed_transcript = summarize_long_transcript(
            client=client,
            transcript=transcript,
            api_key=api_key
        )

    # === 載入模板 ===
    try:
        template_text = load_template("article_template.txt")
    except Exception:
        template_text = "(模板載入失敗，使用預設通用模板)"

    # === System Prompt ===
    system_prompt = (
        "你是一位專業的專訪報導撰稿人，擅長將逐字稿轉化為具敘事感與邏輯結構的完整文章，"
        "能精準控制篇幅與引用比例，符合企業／政府／教育等正式出版需求。"
    )

    # === User Prompt ===
    user_prompt = f"""
請根據以下資訊撰寫完整專訪文章，並結合文章模板作為參考：

【文章資訊】
主題：{subject}
企業：{company}
段落數：{paragraphs}
開場風格：{opening_style}
採訪情境：{opening_context or '（無特定描述）'}

【受訪者資訊】
{participants_desc}

【逐字稿摘要內容】
{compressed_transcript}

【重點摘要】
{summary_points or '（無特定摘要）'}

【文章模板】
{template_text}

【撰寫要求】
1. 結構：開場 + {paragraphs} 段主體 + 結語
2. 主軸人物引用篇幅約 60–70%
3. 文字語氣：專業、真實、有畫面感
4. 每段 300–500 字，全篇約 1600–2000 字
5. 若檢測到中國慣用語，請自動修正為台灣常用說法
6. 請輸出完整文章（含主標題 # 與小標題 ##），段落之間以空行分隔
"""

    # === 呼叫 API ===
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=max_tokens if not safe_mode else 12000,
                temperature=0.7,
                top_p=0.9
            )

            article = response.choices[0].message.content.strip()
            checks = quality_check(article, paragraphs, participants_info)
            return article, checks, attempt

        except Exception as e:
            if attempt == max_attempts - 1:
                raise Exception(f"API 呼叫失敗（已重試 {max_attempts} 次）：{e}")

    raise Exception("未預期錯誤：生成失敗")


# === 分段摘要輔助 ===
def summarize_long_transcript(client: OpenAI, transcript: str, api_key: str) -> str:
    """
    當逐字稿超過 8000 字時，自動執行分段摘要。
    """
    max_segment_length = 5000
    lines = transcript.split("\n")
    segments = []
    buffer = ""
    for line in lines:
        buffer += line + "\n"
        if len(buffer) > max_segment_length:
            segments.append(buffer.strip())
            buffer = ""
    if buffer:
        segments.append(buffer.strip())

    summaries = []
    for idx, seg in enumerate(segments):
        print(f"🧩 正在摘要第 {idx + 1} 段，共 {len(segments)} 段...")
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "你是一位摘要專家，請保留人物觀點、數據、事件邏輯。"
                },
                {
                    "role": "user",
                    "content": f"請摘要以下逐字稿內容，限 300–400 字：\n{seg}"
                }
            ],
            max_tokens=800
        )
        summaries.append(response.choices[0].message.content.strip())

    print("✅ 摘要完成，組合為壓縮版逐字稿")
    return "\n\n".join(summaries)


# === 受訪者處理與品質檢查 ===
def _parse_participants(participants: str) -> List[ParticipantInfo]:
    info = []
    for line in participants.split("\n"):
        parts = [p.strip() for p in line.split("／")]
        if len(parts) == 3:
            info.append({"name": parts[0], "title": parts[1], "weight": parts[2]})
    return info


def _format_participants(participants_info: List[ParticipantInfo]) -> str:
    if not participants_info:
        return "（未提供受訪者資料）"
    return "\n".join([
        f"- {p['name']}（{p['title']}）- {'主軸人物' if p['weight']=='1' else '輔助人物'}"
        for p in participants_info
    ])


def quality_check(article: str, expected_paragraphs: int, participants: List[ParticipantInfo]) -> Dict[str, bool]:
    checks = {}
    checks["包含主標題"] = article.startswith("#")
    checks["包含引言"] = "「" in article and "」" in article
    checks["段落數符合"] = abs(article.count("## ") - expected_paragraphs) <= 1
    word_count = len(article.replace(" ", "").replace("\n", ""))
    checks["字數充足"] = 1500 <= word_count <= 2500
    main_names = [p["name"] for p in participants if p["weight"] == "1"]
    checks["提及主軸人物"] = any(name in article for name in main_names) if main_names else True
    filler_words = ["非常成功", "十分重要", "極為關鍵", "相當優秀", "令人感動", "展現非凡"]
    checks["避免空泛詞彙"] = not any(word in article for word in filler_words)
    return checks
