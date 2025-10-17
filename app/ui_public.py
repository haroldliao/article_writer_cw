import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import streamlit as st
from engine.generator import generate_article

import openai, streamlit
st.sidebar.warning(f"🔍 openai 版本：{openai.__version__} ｜ streamlit：{streamlit.__version__}")

from datetime import datetime
import json

st.set_page_config(page_title="🌐 專訪文章生成器（雲端正式版）",
                   layout="wide", initial_sidebar_state="expanded")
st.title("🌐 專訪文章生成器（雲端正式版）")

# === API Key ===
api_key = st.secrets.get("OPENAI_API_KEY", "")
if not api_key or not api_key.startswith("sk-"):
    st.error("❌ 無法載入 API Key（請檢查 Streamlit Secrets）")
    st.stop()
st.success("✅ 已從 Secrets 成功載入 API Key")

# === Sidebar ===
with st.sidebar:
    st.header("🧾 基本設定")
    subject = st.text_input("主題 *", placeholder="例：永續轉型與科技創新")
    company = st.text_input("企業／組織名稱 *", placeholder="例：台灣科技公司")

    st.subheader("👥 受訪者資訊")
    participants = st.text_area(
        "每行一位（姓名／職稱／權重）",
        placeholder="例：\n陳怡君／主任秘書／1\n林文博／專案經理／2",
        height=150
    )

    transcript = st.text_area("逐字稿內容 *", height=250)
    if transcript:
        wc = len(transcript.replace(" ", "").replace("\n", ""))
        if wc > 8000:
            st.warning("⚠️ 偵測到逐字稿超過 8000 字，將自動啟用【長逐字稿安全模式】。")
        elif wc < 2000:
            st.error(f"❌ 字數過少：目前 {wc} 字")
        else:
            st.success(f"✅ 字數：{wc} 字")

    summary_points = st.text_area("重點摘要（選填）", height=100)

    st.divider()
    st.header("🎨 風格設定")
    col1, col2 = st.columns(2)
    with col1:
        opening_style = st.selectbox("開場風格",
                                     ["場景式", "金句式", "事件式", "對比式", "成就式"])
    with col2:
        paragraphs = st.slider("段落數", 3, 8, 5)

    opening_context = st.text_area("採訪情境（選填）", height=80)
    model_choice = st.selectbox("AI 模型選擇",
                                ["gpt-5-mini", "gpt-4-turbo", "gpt-5"],
                                help="依用途選擇：短篇測試用 gpt-5-mini｜一般專訪稿 gpt-4-turbo｜高階精修用 gpt-5")
    generate_btn = st.button("🚀 生成文章", use_container_width=True, type="primary")

# === 主內容 ===
if generate_btn:
    if not all([subject, company, participants, transcript]):
        st.error("❌ 請確認所有必填欄位皆已填寫。")
        st.stop()

    with st.spinner("🤖 AI 正在生成文章..."):
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

            st.balloons()
            st.success(f"✅ 生成完成！（重試 {retries} 次）")
            tab1, tab2, tab3 = st.tabs(["📄 文章內容", "🔍 品質檢查", "💾 匯出"])
            with tab1:
                st.markdown(article)
                wc = len(article.replace(" ", "").replace("\n", ""))
                st.caption(f"📝 字數：{wc}　模型：{model_choice}")
            with tab2:
                st.json(checks)
            with tab3:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                st.download_button("📥 下載 Markdown",
                                   data=article,
                                   file_name=f"{company}_{subject}_{timestamp}.md",
                                   mime="text/markdown")

        except Exception as e:
            error_msg = str(e)
            if "模板載入失敗" in error_msg:
                st.error("❌ 模板載入失敗，請確認 engine/templates/article_template.txt 是否存在且可讀取。")
            elif "max_completion_tokens" in error_msg or "max_tokens" in error_msg:
                st.error("⚠️ 參數錯誤：請更新 OpenAI 套件版本或確認模型支援。")
            else:
                st.error(f"❌ 生成失敗：{error_msg}")
        finally:
            st.stop()
