# ==========================================================
#  generator.py（穩定版 - 僅使用 gpt-4o-mini 和 gpt-4o）
# ==========================================================

import os

# 清除可能的代理環境變數
for _k in [
    "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
    "http_proxy", "https_proxy", "all_proxy",
]:
    os.environ.pop(_k, None)

# 通知 SDK 不走任何代理
os.environ["NO_PROXY"] = "*"
os.environ["no_proxy"] = "*"

print("✅ 環境變數清理完成")

# ==========================================================
# 主要生成邏輯
# ==========================================================
from openai import OpenAI
from typing import Dict, Tuple, List, TypedDict
from engine.template_loader import load_template

# === 常數定義 ===
TRANSCRIPT_LENGTH_THRESHOLD = 8000
MAX_SEGMENT_LENGTH = 5000
DEFAULT_MODEL = "gpt-4o-mini"
SUMMARY_MODEL = "gpt-4o"
MAX_TOKENS_NORMAL = 4000
MAX_TOKENS_SAFE_MODE = 8000
TEMPERATURE = 0.7
TOP_P = 0.9
MAX_API_ATTEMPTS = 2


class ParticipantInfo(TypedDict):
    name: str
    title: str
    weight: str


def generate_article(
    subject: str,
    company: str,
    participants: str,
    transcript: str,
    summary_points: str,
    opening_style: str,
    opening_context: str,
    paragraphs: int,
    api_key: str,
    model: str = DEFAULT_MODEL,
    max_tokens: int = MAX_TOKENS_NORMAL
) -> Tuple[str, Dict, int]:
    """生成專訪文章（支援 gpt-4o-mini 和 gpt-4o）"""

    # === 模型別名映射 ===
    model_alias = {
        "gpt-5-mini": "gpt-4o-mini",
        "gpt-4-turbo": "gpt-4o",
        "gpt-5": "gpt-4o",
        "快速測試": "gpt-4o-mini",
        "正式生成": "gpt-4o",
        "gpt-4o-mini": "gpt-4o-mini",
        "gpt-4o": "gpt-4o",
    }
    selected_model = model_alias.get(model, DEFAULT_MODEL)
    print(f"🧠 模型選擇：{model} → {selected_model}")

    # === 解析受訪者 ===
    participants_info = _parse_participants(participants)
    participants_desc = _format_participants(participants_info)

    # === 長逐字稿模式 ===
    transcript_length = _count_chars(transcript)
    safe_mode = transcript_length > TRANSCRIPT_LENGTH_THRESHOLD
    compressed_transcript = transcript

    if safe_mode:
        print(f"⚠️ 啟用長逐字稿安全模式（約 {transcript_length} 字）")
        compressed_transcript = summarize_long_transcript(transcript, SUMMARY_MODEL, api_key)

    # === 載入模板 ===
    try:
        template_text = load_template("article_template.txt")
        template_length = len(template_text)
        print(f"✅ 模板載入成功（約 {template_length} 字）")
    except Exception as e:
        raise Exception(f"模板載入失敗：{str(e)}")

    # === 強化的 System Prompt ===
    system_prompt = """你是一位資深專訪作者，熟悉商業、教育、與公共議題報導。

【核心要求】
1. 必須嚴格遵循「文章模板」的所有指示與結構規範
2. 全文字數控制在 1500–2000 字
3. 文章結構：開場 → 主體段落 → 結語
4. 每段至少包含一則直接引言，使用全形引號「」
5. 所有引言與資訊均須來自逐字稿，不得捏造
6. 語氣專業、自然、具溫度與觀察性
7. 每個段落需要加上簡潔精煉的小標題（## 格式）
8. 段落節奏需保持輕重有致，避免平鋪直敘

【語言要求】
- 使用台灣慣用語，避免中國大陸用語
- 統一使用：公部門、使用者、網路、高品質、實際導入、整合、領域、管理、提升效率
- 避免使用：互聯網、高質量、落地、打通、賽道、管控、提效、增量

【寫作原則】
- 以第三人稱旁白撰寫
- 保持專業中性，不使用推銷語氣
- 用具體細節取代抽象形容
- 段落開頭具轉場語，避免連續以引言開頭

請完全按照「文章模板」的詳細規範執行。"""

    # === 優化的 User Prompt ===
    user_prompt = f"""請根據以下資訊撰寫完整專訪文章。

【文章資訊】
主題：{subject}
企業/組織：{company}
段落數：{paragraphs}
開場風格：{opening_style}
採訪情境：{opening_context or '（無特定描述）'}

【受訪者資訊】
{participants_desc}

【逐字稿內容】
{compressed_transcript}

【重點摘要】
{summary_points or '（無重點摘要）'}

========================================
【文章模板 - 請嚴格遵循】
========================================
{template_text}
========================================

【最終檢查清單】
生成文章後，請確認：
✓ 字數 1500-2000 字
✓ 每段約 300-400 字
✓ 包含 4-6 則引言
✓ 開場具體且吸引人
✓ 結語呼應開場
✓ 使用台灣慣用語
✓ 小標題格式正確（##）
✓ 主標題格式正確（#）

現在請開始撰寫完整文章。"""

    # === 呼叫 Chat Completions API ===
    client = OpenAI(api_key=api_key)
    
    for attempt in range(MAX_API_ATTEMPTS):
        try:
            print(f"🔄 嘗試生成文章（第 {attempt + 1}/{MAX_API_ATTEMPTS} 次）")
            
            response = client.chat.completions.create(
                model=selected_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=TEMPERATURE,
                top_p=TOP_P,
                max_tokens=min(max_tokens, 16000),
            )

            article = response.choices[0].message.content.strip()
            checks = quality_check(article, paragraphs, participants_info)
            
            print(f"✅ 文章生成成功（字數：{_count_chars(article)}）")
            return article, checks, attempt

        except Exception as e:
            error_msg = str(e)
            print(f"⚠️ API 呼叫失敗（第 {attempt + 1} 次）：{error_msg}")
            
            if attempt == MAX_API_ATTEMPTS - 1:
                raise Exception(f"API 呼叫失敗（已重試 {MAX_API_ATTEMPTS} 次）：{error_msg}")

    raise Exception("未預期錯誤：生成失敗")


def summarize_long_transcript(transcript: str, model: str, api_key: str) -> str:
    """長逐字稿摘要模式"""
    client = OpenAI(api_key=api_key)
    segments = _split_transcript(transcript, MAX_SEGMENT_LENGTH)
    summaries = []
    
    for idx, seg in enumerate(segments, 1):
        print(f"🧩 正在摘要第 {idx} 段 / 共 {len(segments)} 段")
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "你是一位摘要專家，請保留人物觀點、數據、事件邏輯。"},
                    {"role": "user", "content": f"請摘要以下逐字稿內容，限 300–400 字：\n{seg}"},
                ],
                temperature=0.5,
                max_tokens=800,
            )
            summaries.append(response.choices[0].message.content.strip())
        except Exception as e:
            print(f"⚠️ 第 {idx} 段摘要失敗：{e}")
            summaries.append(f"[摘要失敗：{seg[:200]}...]")
    
    print("✅ 摘要完成，組合為壓縮版逐字稿")
    return "\n\n".join(summaries)


def _split_transcript(transcript: str, max_length: int) -> List[str]:
    """將逐字稿分割成多個段落"""
    lines = transcript.split("\n")
    segments, buffer = [], ""
    for line in lines:
        buffer += line + "\n"
        if len(buffer) > max_length:
            segments.append(buffer.strip())
            buffer = ""
    if buffer.strip():
        segments.append(buffer.strip())
    return segments


def _count_chars(text: str) -> int:
    """計算文字字數（排除空格和換行）"""
    return len(text.replace(" ", "").replace("\n", ""))


def _parse_participants(participants: str) -> List[ParticipantInfo]:
    """解析受訪者資訊"""
    info = []
    for line in participants.split("\n"):
        line = line.strip()
        if not line:
            continue
        parts = [p.strip() for p in line.split("／")]
        if len(parts) == 3:
            info.append({"name": parts[0], "title": parts[1], "weight": parts[2]})
    return info


def _format_participants(participants_info: List[ParticipantInfo]) -> str:
    """格式化受訪者資訊為描述文字"""
    if not participants_info:
        return "（未提供受訪者資料）"
    return "\n".join([
        f"- {p['name']}（{p['title']}）- {'主軸人物' if p['weight'] == '1' else '輔助人物'}"
        for p in participants_info
    ])


def quality_check(
    article: str,
    expected_paragraphs: int,
    participants: List[ParticipantInfo]
) -> Dict[str, bool]:
    """檢查文章品質"""
    checks = {}
    checks["包含主標題"] = article.startswith("#")
    checks["包含引言"] = "「" in article and "」" in article
    paragraph_count = article.count("## ")
    checks["段落數符合"] = abs(paragraph_count - expected_paragraphs) <= 1
    word_count = _count_chars(article)
    checks["字數充足"] = 1500 <= word_count <= 2500
    main_names = [p["name"] for p in participants if p["weight"] == "1"]
    checks["提及主軸人物"] = any(name in article for name in main_names) if main_names else True
    filler_words = ["非常成功", "十分重要", "極為關鍵", "相當優秀", "令人感動", "展現非凡"]
    checks["避免空泛詞彙"] = not any(word in article for word in filler_words)
    return checks


