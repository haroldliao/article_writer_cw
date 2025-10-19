import os
from openai import OpenAI

# === 防止 SDK proxy 問題 ===
def _clear_proxy_env():
    """安全清除代理環境變數"""
    for var in ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"]:
        if var in os.environ:
            print(f"⚠️ 移除環境變數：{var}")
            os.environ.pop(var, None)

# 在 os 載入完成後執行清除
_clear_proxy_env()

# === 封裝 OpenAI 初始化，防止 proxies 參數報錯 ===
_original_init = OpenAI.__init__

def patched_init(self, *args, **kwargs):
    """自動移除不支援的 proxies 參數"""
    if "proxies" in kwargs:
        print("⚠️ 移除不支援的 proxies 參數")
        kwargs.pop("proxies")
    return _original_init(self, *args, **kwargs)

# 套用補丁
OpenAI.__init__ = patched_init


# === 主要程式開始 ===
from typing import Dict, Tuple, List, TypedDict
from engine.template_loader import load_template

# === 常數定義 ===
TRANSCRIPT_LENGTH_THRESHOLD = 8000
MAX_SEGMENT_LENGTH = 5000
DEFAULT_MODEL = "gpt-5-mini"
SUMMARY_MODEL = "gpt-4-turbo"
MAX_TOKENS_NORMAL = 4000
MAX_TOKENS_SAFE_MODE = 12000
TEMPERATURE = 0.7
TOP_P = 0.9
MAX_API_ATTEMPTS = 1


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
    """
    生成專訪文章（支援長逐字稿安全模式 + 多模型選擇）
    """
    client = OpenAI(api_key=api_key)

    # === 模型別名對照表 ===
    model_alias = {
        "gpt-5-mini": "gpt-5-mini",
        "gpt-4-turbo": "gpt-4-turbo",
        "gpt-5": "gpt-5",
        "gpt-4o-mini": "gpt-4o-mini",
        "gpt-4o": "gpt-4o",
    }
    
    selected_model = model_alias.get(model)
    if not selected_model:
        print(f"⚠️ 未識別的模型名稱：{model}，自動使用 {DEFAULT_MODEL}")
        selected_model = DEFAULT_MODEL

    # === 解析受訪者資訊 ===
    participants_info = _parse_participants(participants)
    participants_desc = _format_participants(participants_info)

    # === 檢查逐字稿長度 ===
    transcript_length = _count_chars(transcript)
    safe_mode = transcript_length > TRANSCRIPT_LENGTH_THRESHOLD
    compressed_transcript = transcript

    if safe_mode:
        print(f"⚠️ 啟用長逐字稿安全模式：逐字稿長度約 {transcript_length} 字")
        compressed_transcript = summarize_long_transcript(
            client=client,
            transcript=transcript,
            model=SUMMARY_MODEL
        )

    # === 載入模板 ===
    try:
        template_text = load_template("article_template.txt")
    except Exception as e:
        error_msg = f"模板載入失敗：{str(e)}"
        print(f"❌ {error_msg}")
        raise Exception(error_msg)

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

    # === 呼叫 API（使用 Responses API） ===
    for attempt in range(MAX_API_ATTEMPTS):
        try:
            token_param = {}
            max_output = MAX_TOKENS_SAFE_MODE if safe_mode else max_tokens

            if "gpt-5" in selected_model:
                token_param = {"max_completion_tokens": min(max_output, 4000)}
            elif "gpt-4" in selected_model:
                token_param = {"max_completion_tokens": min(max_output, 8000)}
            else:
                token_param = {"max_completion_tokens": min(max_output, 4000)}

            print(f"🧠 使用模型：{selected_model}，Token 參數：{token_param}")

            response = client.responses.create(
                model=selected_model,
                input=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                **token_param,
                temperature=TEMPERATURE,
                top_p=TOP_P
            )

            article = response.output_text.strip()
            checks = quality_check(article, paragraphs, participants_info)
            return article, checks, attempt

        except Exception as e:
            if attempt == MAX_API_ATTEMPTS - 1:
                raise Exception(f"API 呼叫失敗（已重試 {MAX_API_ATTEMPTS} 次）：{e}")
            print(f"⚠️ API 呼叫失敗，正在重試（第 {attempt + 1} 次）：{e}")

    raise Exception("未預期錯誤：生成失敗")


def summarize_long_transcript(
    client: OpenAI, 
    transcript: str,
    model: str = SUMMARY_MODEL
) -> str:
    """當逐字稿超過閾值時，自動執行分段摘要。"""
    segments = _split_transcript(transcript, MAX_SEGMENT_LENGTH)
    summaries = []
    
    for idx, seg in enumerate(segments, 1):
        print(f"🧩 正在摘要第 {idx} 段，共 {len(segments)} 段...")
        try:
            response = client.responses.create(
                model=model,
                input=[
                    {"role": "system", "content": "你是一位摘要專家，請保留人物觀點、數據、事件邏輯。"},
                    {"role": "user", "content": f"請摘要以下逐字稿內容，限 300–400 字：\n{seg}"}
                ],
                max_completion_tokens=800,
                temperature=0.5
            )
            summaries.append(response.output_text.strip())
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
            info.append({
                "name": parts[0],
                "title": parts[1],
                "weight": parts[2]
            })
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
