# ==========================================================
#  generator.py（最終穩定版）
#  - 完整支援新版 OpenAI SDK (v2.x)
#  - 自動清除與攔截 proxies 問題
# ==========================================================

# ---- Hard guard for unexpected 'proxies' in any OpenAI() init ----
import os

# 1️⃣ 擴大清除所有可能的代理環境變數
for _k in [
    "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
    "http_proxy", "https_proxy", "all_proxy",
    "OPENAI_HTTP_PROXY", "OPENAI_PROXY",
    "openai_http_proxy", "openai_proxy"
]:
    if _k in os.environ:
        print(f"⚠️ 清除代理環境變數：{_k}")
        os.environ.pop(_k, None)

# 2️⃣ 通知 SDK 不走任何代理
os.environ["NO_PROXY"] = "*"
os.environ["no_proxy"] = "*"

# 3️⃣ 攔截 OpenAI() 初始化中的 proxies
try:
    from openai import OpenAI as _SDKOpenAI
    _old_init = _SDKOpenAI.__init__

    def _patched_init(self, *args, **kwargs):
        if "proxies" in kwargs:
            print("⚠️ 偵測到 proxies 參數，已自動移除以避免 SDK 錯誤。")
            kwargs.pop("proxies", None)
        # 嘗試清除 http_client 內的代理設定
        if "http_client" in kwargs:
            try:
                http_client = kwargs["http_client"]
                if hasattr(http_client, "proxies"):
                    setattr(http_client, "proxies", None)
            except Exception:
                pass
        return _old_init(self, *args, **kwargs)

    _SDKOpenAI.__init__ = _patched_init
    print("✅ OpenAI() 初始化 proxies 防護已啟用")
except Exception as _e:
    print(f"ℹ️ OpenAI() 補丁略過：{_e}")

# ==========================================================
# 主要生成邏輯
# ==========================================================
import openai
from typing import Dict, Tuple, List, TypedDict
from engine.template_loader import load_template

# === 常數定義 ===
TRANSCRIPT_LENGTH_THRESHOLD = 8000
MAX_SEGMENT_LENGTH = 5000
DEFAULT_MODEL = "gpt-5-mini"
SUMMARY_MODEL = "gpt-4-turbo"
MAX_TOKENS_NORMAL = 4000
MAX_TOKENS_SAFE_MODE = 8000
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
    """生成專訪文章（支援新版 SDK + 多模型選擇）"""
    openai.api_key = api_key

    # === 模型別名 ===
    model_alias = {
        "gpt-5-mini": "gpt-5-mini",
        "gpt-4-turbo": "gpt-4-turbo",
        "gpt-5": "gpt-5",
        "gpt-4o-mini": "gpt-4o-mini",
        "gpt-4o": "gpt-4o",
    }
    selected_model = model_alias.get(model, DEFAULT_MODEL)

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
    except Exception as e:
        raise Exception(f"模板載入失敗：{str(e)}")

    # === Prompt ===
    system_prompt = (
        "你是一位專業的專訪報導撰稿人，擅長將逐字稿轉化為具敘事感與邏輯結構的完整文章，"
        "能精準控制篇幅與引用比例，符合企業／政府／教育等正式出版需求。"
    )

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

    # === 呼叫 Chat Completions API ===
    for attempt in range(MAX_API_ATTEMPTS):
        try:
            print(f"🧠 使用模型：{selected_model}")
            from openai import OpenAI  # 顯式建立 client 確保經過補丁
            client = OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model=selected_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=TEMPERATURE,
                top_p=TOP_P,
                max_completion_tokens=min(max_tokens, 4000),
            )

            article = response.choices[0].message.content.strip()
            checks = quality_check(article, paragraphs, participants_info)
            return article, checks, attempt

        except Exception as e:
            if attempt == MAX_API_ATTEMPTS - 1:
                raise Exception(f"API 呼叫失敗（已重試 {MAX_API_ATTEMPTS} 次）：{e}")
            print(f"⚠️ API 呼叫失敗，正在重試（第 {attempt + 1} 次）：{e}")

    raise Exception("未預期錯誤：生成失敗")


def summarize_long_transcript(transcript: str, model: str, api_key: str) -> str:
    """長逐字稿摘要模式"""
    from openai import OpenAI
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
                max_completion_tokens=800,
            )
            summaries.append(response.choices[0].message.content.strip())
        except Exception as e:
            summaries.append(f"[摘要失敗：{e}]")
    print("✅ 摘要完成，組合為壓縮版逐字稿")
    return "\n\n".join(summaries)


def _split_transcript(transcript: str, max_length: int) -> List[str]:
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
    return len(text.replace(" ", "").replace("\n", ""))


def _parse_participants(participants: str) -> List[ParticipantInfo]:
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
    if not participants_info:
        return "（未提供受訪者資料）"
    return "\n".join([
        f"- {p['name']}（{p['title']}）- {'主軸人物' if p['weight'] == '1' else '輔助人物'}"
        for p in participants_info
    ])


def quality_check(article: str, expected_paragraphs: int, participants: List[ParticipantInfo]) -> Dict[str, bool]:
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
