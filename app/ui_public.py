import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))  # ✅ 關鍵新增

import streamlit as st
from engine.generator import generate_article
import json
from datetime import datetime

st.set_page_config(
    page_title="🌐 專訪文章生成器（雲端正式版）",
    layout="wide",
    initial_sidebar_state="expanded"
)

# === 自訂樣式 ===
st.markdown("""
<style>
    .stAlert > div { padding: 0.5rem 1rem; }
    .success-box { background-color: #d4edda; padding: 1rem; border-radius: 0.5rem; }
    .warning-text { color: #856404; background-color: #fff3cd; padding: 0.5rem; border-radius: 0.25rem; }
</style>
""", unsafe_allow_html=True)

st.title("🌐 專訪文章生成器（雲端正式版）")

# === API Key 驗證 ===
try:
    api_key = st.secrets["OPENAI_API_KEY"]
    if not api_key.startswith("sk-"):
        raise ValueError("API Key 格式錯誤")
    st.success("✅ 已從 Secrets 載入 API Key")
except Exception as e:
    st.error(f"❌ 無法載入 API Key：{e}")
    st.info("💡 請至 Streamlit Cloud → Settings → Secrets 設定 `OPENAI_API_KEY`")
    st.stop()

# === Sidebar 輸入區 ===
with st.sidebar:
    st.header("⚙️ 基本設定")
    model_choice = st.selectbox(
        "AI 模型選擇",
        options=["gpt-4o-mini", "o1-preview"],
        index=0,
        help="選擇生成模型：gpt-4o-mini 為快速版，o1-preview 為高品質版"
    )

    if model_choice == "o1-preview":
        st.warning("⚠️ o1-preview 生成速度較慢，但推理品質更高")

    st.divider()
    st.header("📝 文章資訊")

    subject = st.text_input("主題 *", placeholder="例：數位轉型策略")
    company = st.text_input("企業名稱 *", placeholder="例：台灣科技公司")

    # === 受訪者資訊 ===
    st.subheader("👥 受訪者資訊")
    participants = st.text_area(
        "受訪者清單（每行一位）*",
        placeholder="格式：姓名／職稱／權重\n\n範例：\n王大明／執行長／1\n李小華／技術長／2",
        height=150,
        help="權重：1 = 主軸人物（主角），2 = 輔助人物（補充觀點）"
    )

    # 預覽受訪者格式
    if participants:
        lines = [l.strip() for l in participants.split('\n') if l.strip()]
        parsed, has_error = [], False
        for line in lines:
            parts = line.split('／')
            if len(parts) == 3:
                name, title, weight = parts
                if weight in ['1', '2']:
                    icon = "⭐" if weight == "1" else "◆"
                    parsed.append(f"{icon} {name}（{title}）")
                else:
                    parsed.append(f"❌ 權重錯誤：{line}")
                    has_error = True
            else:
                parsed.append(f"❌ 格式錯誤：{line}")
                has_error = True

        with st.expander("📋 解析預覽", expanded=has_error):
            if has_error:
                st.error("請修正以下格式錯誤：")
            else:
                st.success("✅ 格式正確")
                st.caption("⭐ 主軸人物（權重1）為核心；◆ 輔助人物提供補充觀點。")
            for item in parsed:
                st.text(item)

    st.divider()
    st.header("📄 內容素材")

    transcript = st.text_area(
        "逐字稿內容 *",
        height=250,
        placeholder="請貼上採訪逐字稿（建議至少 2000 字）"
    )

    if transcript:
        word_count = len(transcript.replace(' ', '').replace('\n', ''))
        if word_count < 2000:
            st.error(f"❌ 目前 {word_count} 字，至少需要 2000 字")
        elif word_count < 2500:
            st.warning(f"⚠️ 目前 {word_count} 字，建議 2500 字以上")
        else:
            st.success(f"✅ 字數統計：{word_count} 字")

    summary_points = st.text_area(
        "重點摘要（選填）",
        height=120,
        placeholder="每行一個重點，協助 AI 聚焦關鍵訊息"
    )

    st.divider()
    st.header("🎨 風格設定")

    col1, col2 = st.columns(2)
    with col1:
        opening_style = st.selectbox(
            "開場風格",
            options=["場景式", "金句式", "事件式", "對比式", "成就式"]
        )
    with col2:
        paragraphs = st.slider("段落數", 3, 8, 5)

    opening_context = st.text_area(
        "採訪情境（選填）",
        height=100,
        placeholder="例：在明亮的實驗室裡，張博士笑著說..."
    )

    st.divider()

    # === 驗證輸入 ===
    def validate_inputs():
        errors, warnings = [], []
        if not subject.strip():
            errors.append("請填寫主題")
        if not company.strip():
            errors.append("請填寫企業名稱")
        if not participants.strip():
            errors.append("請填寫受訪者清單")
        if not transcript.strip():
            errors.append("請貼上逐字稿")

        if transcript:
            wc = len(transcript.replace(' ', '').replace('\n', ''))
            if wc < 2000:
                errors.append(f"逐字稿至少需 2000 字（目前 {wc}）")
            elif wc < 2500:
                warnings.append(f"建議逐字稿 2500 字以上（目前 {wc}）")

        return errors, warnings

    errors, warnings = validate_inputs()
    if errors:
        st.error("❌ 請修正以下問題：")
        for e in errors:
            st.markdown(f"• {e}")
        generate_btn = st.button("🚀 生成文章", disabled=True, use_container_width=True)
    else:
        if warnings:
            st.warning("⚠️ 提醒：")
            for w in warnings:
                st.markdown(f"• {w}")
        generate_btn = st.button("🚀 生成文章", type="primary", use_container_width=True)

# === 主畫面輸出 ===
if generate_btn:
    with st.spinner("🤖 AI 正在生成文章，請稍候..."):
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
                model=model_choice
            )

            st.balloons()
            st.success(f"✅ 生成完成！（重試 {retries} 次）")

            tab1, tab2, tab3 = st.tabs(["📄 文章內容", "🔍 品質檢查", "💾 匯出選項"])

            with tab1:
                st.markdown(article)
                st.caption("💡 可直接複製全文或下載 Markdown/TXT/JSON 檔案")
                wc = len(article.replace(' ', '').replace('\n', ''))
                st.metric("文章字數", f"{wc} 字")

            with tab2:
                st.subheader("品質檢查結果")
                if isinstance(checks, dict):
                    all_passed = all(checks.values())
                    if all_passed:
                        st.success("✅ 所有檢查項目通過")
                    else:
                        st.warning("⚠️ 部分項目未通過")
                    check_table = [{"檢查項目": k, "狀態": "✅" if v else "❌"} for k, v in checks.items()]
                    st.table(check_table)
                else:
                    st.json(checks)

            with tab3:
                st.subheader("匯出選項")
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                st.download_button("📥 下載 Markdown", data=article, file_name=f"interview_{ts}.md", mime="text/markdown")
                st.download_button("📥 下載純文字", data=article.replace('#', ''), file_name=f"interview_{ts}.txt", mime="text/plain")
                st.download_button("📥 下載 JSON", data=json.dumps({"article": article, "checks": checks}, ensure_ascii=False, indent=2),
                                   file_name=f"interview_{ts}.json", mime="application/json")

        except Exception as e:
            st.error(f"❌ 生成失敗：{e}")

st.divider()
st.caption("🔒 使用 Streamlit Secrets 管理金鑰 | Powered by OpenAI")
