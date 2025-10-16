import sys
import os
from pathlib import Path

# 將父層加入模組搜尋路徑
sys.path.append(str(Path(__file__).parent.parent))

import streamlit as st
from engine.generator import generate_article
from datetime import datetime
import json

# === 頁面設定 ===
st.set_page_config(
    page_title="🧠 專訪文章生成器（本機版）",
    layout="wide",
    initial_sidebar_state="expanded"
)

# === 輔助函數 ===
def validate_api_key(key: str) -> tuple[bool, str]:
    if not key:
        return False, "請輸入 API Key（sk-...）"
    if not key.startswith("sk-"):
        return False, "API Key 格式錯誤（需以 sk- 開頭）"
    return True, "✅ API Key 格式正確"

def count_words(text: str) -> dict:
    text_clean = text.replace(" ", "").replace("\n", "")
    chinese = sum(1 for c in text_clean if '\u4e00' <= c <= '\u9fff')
    return {"total": len(text_clean), "chinese": chinese}

def validate_required_fields(api_key: str, subject: str, company: str,
                            participants: str, transcript: str) -> tuple[bool, str]:
    if not all([api_key, subject, company, participants, transcript]):
        missing = []
        if not api_key: missing.append("API Key")
        if not subject: missing.append("主題")
        if not company: missing.append("企業／組織名稱")
        if not participants: missing.append("受訪者資訊")
        if not transcript: missing.append("逐字稿內容")
        return False, f"缺少必填欄位：{', '.join(missing)}"
    return True, ""

# === 主畫面標題 ===
st.title("🧠 專訪文章生成器（本機版）")

# === Sidebar ===
with st.sidebar:
    st.header("⚙️ API 設定")
    api_key = st.text_input("🔑 OpenAI API Key *", type="password")

    # API Key 驗證
    valid, msg = validate_api_key(api_key)
    st.info(msg if not valid else "✅ API Key 格式正確")

    st.divider()

    st.header("🧾 文章設定")
    subject = st.text_input("主題 *", placeholder="例：AI 驅動的創新策略")
    company = st.text_input("企業／組織名稱 *", placeholder="例：台灣科技公司")

    st.subheader("👥 受訪者資訊")
    participants = st.text_area(
        "每行一位（姓名／職稱／權重）",
        placeholder="例：\n王大明／執行長／1\n李小華／技術長／2",
        height=150
    )

    transcript = st.text_area(
        "逐字稿內容 *",
        height=300,
        placeholder="請貼上完整逐字稿（建議 2000–6000 字）"
    )

    # 自動偵測長逐字稿提示
    if transcript:
        word_count = len(transcript.replace(" ", "").replace("\n", ""))
        if word_count > 8000:
            st.warning("⚠️ 偵測到逐字稿超過 8000 字，將自動啟用【長逐字稿安全模式】。")
        elif word_count < 2000:
            st.error(f"❌ 字數過少：目前 {word_count} 字，建議 2000 字以上。")
        else:
            st.success(f"✅ 字數：{word_count} 字")

    summary_points = st.text_area("重點摘要（選填）", height=100)

    st.divider()
    st.header("🎨 風格設定")

    col1, col2 = st.columns(2)
    with col1:
        opening_style = st.selectbox(
            "開場風格",
            ["場景式", "金句式", "事件式", "對比式", "成就式"]
        )
    with col2:
        paragraphs = st.slider("段落數", 3, 8, 5)

    opening_context = st.text_area(
        "採訪情境（選填）",
        height=80,
        placeholder="例：午後陽光灑進落地窗，王執行長微笑著說..."
    )

    model_choice = st.selectbox(
        "AI 模型選擇",
        ["gpt-4o-mini", "gpt-4-turbo-128k", "o1-preview"],
        help="長篇逐字稿可使用 gpt-4-turbo-128k"
    )

    generate_btn = st.button("🚀 生成文章", use_container_width=True, type="primary")

# === 主畫面 ===
if generate_btn:
    valid, msg = validate_required_fields(api_key, subject, company, participants, transcript)
    if not valid:
        st.error(msg)
        st.stop()

    with st.spinner("🤖 AI 正在生成文章..."):
        try:
            article, checks, retries = generate_article(
                subject=subject,
                company=company,
                people=None,
                participants=participants,
                transcript=transcript,
                summary_points=summary_points,
                opening_style=opening_style,
                opening_context=opening_context,
                paragraphs=paragraphs,
                api_key=api_key,
                model=model_choice,
                max_tokens=4000
            )

            st.balloons()
            st.success(f"✅ 生成完成！（重試 {retries} 次）")

            tab1, tab2, tab3 = st.tabs(["📄 文章內容", "🔍 品質檢查", "💾 匯出"])

            with tab1:
                st.markdown(article)
                wc = count_words(article)
                st.caption(f"📝 字數：{wc['total']}　模型：{model_choice}")

            with tab2:
                st.subheader("品質檢查結果")
                st.json(checks)

            with tab3:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{company}_{subject}_{timestamp}.md"
                st.download_button(
                    "📥 下載 Markdown",
                    data=article,
                    file_name=filename,
                    mime="text/markdown"
                )
                full_json = json.dumps({
                    "article": article,
                    "metadata": {"subject": subject, "company": company, "model": model_choice},
                    "checks": checks
                }, ensure_ascii=False, indent=2)
                st.download_button("📥 下載 JSON", data=full_json, file_name=filename.replace(".md", ".json"))

        except Exception as e:
            st.error(f"❌ 生成失敗：{e}")
            st.exception(e)
