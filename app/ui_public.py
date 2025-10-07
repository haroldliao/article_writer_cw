import sys
from pathlib import Path
import streamlit as st

# === 專案根目錄設定 ===
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from engine.generator import generate_article
from selector import list_styles

# === 頁面設定 ===
st.set_page_config(page_title="專訪文章生成器(雲端版)", layout="wide")
st.title("🌐 專訪文章生成器")

# === 讀取金鑰與密碼 ===
OPENAI_API_KEY = st.secrets.get("OPENAI_API_KEY")
APP_PASSWORD = st.secrets.get("APP_PASSWORD")

if not OPENAI_API_KEY:
    st.error("⚠️ 尚未在 Streamlit Secrets 中設定 OPENAI_API_KEY。")
    st.stop()

# === 密碼驗證 ===
if APP_PASSWORD:
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    
    if not st.session_state.authenticated:
        with st.form("auth_form"):
            password = st.text_input("🔒 請輸入使用密碼", type="password")
            if st.form_submit_button("進入"):
                if password == APP_PASSWORD:
                    st.session_state.authenticated = True
                    st.success("✅ 驗證成功")
                    st.rerun()
                else:
                    st.error("❌ 密碼錯誤")
        st.stop()
else:
    st.caption("⚠️ 未設定 APP_PASSWORD,目前為任何人可使用模式。")

# === 使用者輸入區 ===
with st.sidebar:
    st.header("輸入區")
    subject = st.text_input("主題")
    company = st.text_input("企業名稱(可多個,用逗號分隔)")
    people = st.text_input("人物姓名(可多個,用逗號分隔)")
    participants = st.text_area("受訪者清單(選填,多位請分行)")
    transcript_text = st.text_area("逐字稿內容(請直接貼上)")
    summary_points = st.text_area("重點摘要(每行一點,建議 3–7 行)")
    
    styles = list_styles() or ["企業", "學校", "政府"]
    style_label = st.selectbox("文章風格類型", styles)
    word_count = st.slider("字數範圍", 1500, 2000, (1500, 2000))
    paragraphs = st.radio("段落數", [3, 4])
    
    if st.button("生成文章"):
        st.session_state.trigger_generate = True

# === 右側輸出區 ===
st.header("輸出區")

if st.session_state.get("trigger_generate"):
    st.session_state.trigger_generate = False
    
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
                article, checks, retries = generate_article(
                    subject=subject.strip(),
                    company=company.strip(),
                    people=people.strip(),
                    participants=participants.strip(),
                    transcript=transcript_text.strip(),
                    summary_points=summary_points.strip(),
                    style_label=style_label,
                    word_count_range=word_count,
                    paragraphs=paragraphs,
                    api_key=OPENAI_API_KEY,
                )
                
                st.subheader("📰 文章內容")
                st.markdown(article)
                
                st.subheader("✅ 檢查結果")
                st.json(checks)
                
                if retries == 0:
                    st.success("✨ 一次生成成功,無需修稿")
                else:
                    st.warning(f"✏️ 本文經過 {retries} 次自動修稿後產生")
                    
            except Exception as e:
                st.error(f"生成文章時發生錯誤: {e}")