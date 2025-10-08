import sys
import os
from pathlib import Path
import streamlit as st

# === 將專案根目錄加入模組搜尋路徑 ===
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from engine.generator import generate_article
from selector import list_styles

# === 頁面設定 ===
st.set_page_config(page_title="專訪文章生成器（本機版）", layout="wide")
st.title("🧠 專訪文章生成器 — 本機版")

# === 使用者輸入區 ===
with st.sidebar:
    st.header("輸入區（開發者用）")

    # 金鑰輸入
    api_key = st.text_input("🔑 輸入你的 OpenAI API Key", type="password")

    # 基本資料
    subject = st.text_input("主題")
    company = st.text_input("企業名稱（可多個，用逗號分隔）")
    people = st.text_input("人物姓名（可多個，用逗號分隔）")
    participants = st.text_area("受訪者清單（選填，多位請分行）")

    # ✅ 新增：開場風格與採訪情境
    opening_style = st.selectbox(
        "開場風格（五選一）",
        ["場景式", "金句式", "事件式", "對比式", "成就式"]
    )

    opening_context = st.text_area(
        "採訪情境（地點/氛圍/場景/互動）",
        placeholder="例：在台中工業區的廠房，一進門就是機器運轉聲與熱氣交織。"
    )

    # 主體設定
    transcript_text = st.text_area("逐字稿內容（請直接貼上）")
    summary_points = st.text_area("重點摘要（每行一點，建議 3–7 行）")

    # 風格類型（企業 / 學校 / 政府）
    styles = list_styles() or ["企業", "學校", "政府"]
    style_label = st.selectbox("文章風格類型", styles)

    # 字數與段落設定
    word_count = st.slider("字數範圍", 1500, 2000, (1500, 2000))
    paragraphs = st.radio("段落數", [3, 4])

    # 生成按鈕
    generate_btn = st.button("生成文章")

# === 右側輸出 ===
st.header("輸出區")

if generate_btn:
    if not api_key:
        st.error("⚠️ 請輸入 OpenAI API Key")
        st.stop()

    # 基本欄位檢查
    required_fields = {
        "主題": subject,
        "企業": company,
        "人物": people,
        "逐字稿": transcript_text,
        "重點摘要": summary_points,
    }
    missing = [k for k, v in required_fields.items() if not v.strip()]

    if missing:
        st.error(f"⚠️ 請填寫以下欄位: {', '.join(missing)}")
    else:
        with st.spinner("⏳ 正在生成文章..."):
            try:
                # ✅ 傳入新版參數名稱（對應 generator.py）
                article, checks, retries = generate_article(
                    subject=subject.strip(),
                    company=company.strip(),
                    people=people.strip(),
                    participants=participants.strip(),
                    transcript=transcript_text.strip(),
                    summary_points=summary_points.strip(),
                    opening_style=opening_style,       # ✅ 新增
                    opening_context=opening_context,   # ✅ 新增
                    word_count_range=word_count,
                    paragraphs=paragraphs,
                    api_key=api_key
                )

                st.subheader("📰 文章內容")
                st.markdown(article)

                st.subheader("✅ 檢查結果")
                st.json(checks)

                if retries == 0:
                    st.success("✨ 一次生成成功，無需修稿")
                else:
                    st.warning(f"✏️ 本文經過 {retries} 次自動修稿")

            except Exception as e:
                st.error(f"生成文章時發生錯誤: {e}")
