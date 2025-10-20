import sys
import os
from pathlib import Path

# 將父層加入模組搜尋路徑
sys.path.append(str(Path(__file__).parent.parent))

import streamlit as st
from engine.generator import generate_article
from engine.postprocess import build_docx_from_markdown  # ✅ 新增匯入
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

    transcript = st.text_area("逐字稿內容 *", height=300, placeholder="請貼上完整逐字稿（建議 2000–6000 字）")
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
        opening_style = st.selectbox("開場風格", ["場景式", "金句式", "事件式", "對比式", "成就式"])
    with col2:
        paragraphs = st.slider("段落數", 3, 8, 5)

    opening_context = st.text_area("採訪情境（選填）", height=80,
                                   placeholder="例：午後陽光灑進落地窗，王執行長微笑著說...")
    
    model_choice = st.selectbox(
        "AI 模型選擇",
        ["快速測試", "正式生成"],
        index=1,
        help="""
- 快速測試（gpt-4o-mini）：適合功能測試、快速驗證，成本低、速度快
- 正式生成（gpt-4o）：適合正式文章、長逐字稿處理，品質高、穩定可靠
        """
    )

    generate_btn = st.button("🚀 生成文章", use_container_width=True, type="primary")

# === 主畫面 ===
if generate_btn:
    valid, msg = validate_required_fields(api_key, subject, company, participants, transcript)
    if not valid:
        st.error(msg)
        st.stop()

    # ✅ 修改：移除 spinner，改用簡單訊息
    status_placeholder = st.empty()
    status_placeholder.info("🤖 AI 正在生成文章，請稍候...")
    
    try:
        article, checks, retries = generate_article(
            subject=subject,
            company=company,
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

        # ✅ 清除狀態訊息
        status_placeholder.empty()
        
        st.balloons()
        st.success(f"✅ 生成完成！（重試 {retries} 次）")
        
        # ✅ 修改：新增 4 個 tab，包含 Word 和 TXT 下載
        tab1, tab2, tab3, tab4 = st.tabs(["📄 文章內容", "🔍 品質檢查", "💾 下載 Markdown", "📦 下載其他格式"])
        
        with tab1:
            st.markdown(article)
            wc = count_words(article)
            actual_model = "gpt-4o-mini" if model_choice == "快速測試" else "gpt-4o"
            st.caption(f"📝 字數：{wc['total']}　模型：{actual_model}")
        
        with tab2:
            st.json(checks)
        
        with tab3:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename_base = f"{company}_{subject}_{timestamp}"
            
            st.download_button(
                "📥 下載 Markdown (.md)",
                data=article,
                file_name=f"{filename_base}.md",
                mime="text/markdown",
                use_container_width=True
            )
        
        with tab4:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename_base = f"{company}_{subject}_{timestamp}"
            
            # ✅ Word 下載
            st.subheader("📄 Microsoft Word")
            try:
                docx_data = build_docx_from_markdown(article)
                st.download_button(
                    "📥 下載 Word (.docx)",
                    data=docx_data,
                    file_name=f"{filename_base}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True
                )
            except Exception as e:
                st.error(f"Word 檔案生成失敗：{e}")
            
            st.divider()
            
            # ✅ 純文字下載
            st.subheader("📝 純文字檔")
            # 移除 Markdown 標記
            plain_text = article.replace("# ", "").replace("## ", "").replace("**", "")
            st.download_button(
                "📥 下載純文字 (.txt)",
                data=plain_text,
                file_name=f"{filename_base}.txt",
                mime="text/plain",
                use_container_width=True
            )

    except Exception as e:
        status_placeholder.empty()  # ✅ 清除狀態訊息
        error_msg = str(e)
        if "模板載入失敗" in error_msg:
            st.error("❌ 模板載入失敗，請確認 engine/templates/article_template.txt 是否存在且可讀取。")
        elif "max_completion_tokens" in error_msg or "max_tokens" in error_msg:
            st.error("⚠️ 參數錯誤：請更新 OpenAI 套件版本或確認模型支援。")
        else:
            st.error(f"❌ 生成失敗：{error_msg}")