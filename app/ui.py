import sys
import os
import json
import uuid
import time
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

import streamlit as st
from engine.generator import generate_article
from selector import list_styles

# ========== 常數設定 ==========
DEFAULT_MAX_USAGE = 2
REQUEST_TIMEOUT = 5

# ========== 工具函數 ==========
def get_secret(key: str, default=None):
    """優先讀 st.secrets，其次讀環境變數"""
    try:
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return os.getenv(key, default)

def notify_author(event: str, details: dict):
    """透過 webhook 通知作者；若未設定，顯示聯絡方式"""
    webhook = get_secret("NOTIFY_WEBHOOK_URL", "")
    author_email = get_secret("AUTHOR_EMAIL", "")
    
    payload = {
        "event": event,
        "timestamp": int(time.time()),
        "details": details,
    }
    
    if webhook:
        try:
            import requests
            requests.post(webhook, json=payload, timeout=REQUEST_TIMEOUT)
            st.success("已通知作者，我們會盡快協助你。")
            return
        except Exception:
            pass
    
    if author_email:
        st.info(f"請來信聯絡作者：{author_email}")
    else:
        st.info("請聯絡作者以協助開通使用。")

def handle_usage_limit_notification():
    """處理使用次數達上限的通知"""
    if st.button("通知作者申請開通/重置"):
        notify_author(
            event="usage_limit_reached",
            details={
                "session_id": st.session_state.session_id,
                "usage_count": st.session_state.usage_count,
            },
        )

# ========== 初始化設定 ==========
st.set_page_config(page_title="專訪文章生成器", layout="wide")
st.title("📝 專訪文章生成器")

# API Key 檢查
OPENAI_API_KEY = get_secret("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    st.error("伺服器尚未設定 OPENAI_API_KEY。")
    st.stop()
os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY

# 初始化 session 狀態
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "usage_count" not in st.session_state:
    st.session_state.usage_count = 0

# ========== 密碼驗證 ==========
APP_PASSWORD = get_secret("APP_PASSWORD", None)
if APP_PASSWORD:
    if not st.session_state.authenticated:
        with st.form("auth_form", clear_on_submit=False):
            pwd = st.text_input("請輸入存取密碼", type="password")
            submitted = st.form_submit_button("進入")
            if submitted:
                if pwd == APP_PASSWORD:
                    st.session_state.authenticated = True
                    st.success("驗證成功")
                else:
                    st.error("密碼錯誤")
                    st.stop()
    if not st.session_state.authenticated:
        st.stop()
else:
    st.caption("🔒 未設定 APP_PASSWORD（目前為持連結可用模式）")

# ========== 使用次數限制 ==========
MAX_USAGE = int(get_secret("MAX_USAGE", DEFAULT_MAX_USAGE))
st.caption(f"本瀏覽器可用次數：{st.session_state.usage_count}/{MAX_USAGE}")

if st.session_state.usage_count >= MAX_USAGE:
    st.error("⚠️ 你已達本次使用上限。")
    handle_usage_limit_notification()
    st.stop()

# ========== 左側輸入表單 ==========
with st.sidebar:
    st.header("輸入區")
    
    styles = list_styles() or ["企業", "學校", "政府"]
    style_label = st.selectbox("文章風格類型", styles)
    
    subject = st.text_input("主題")
    company = st.text_input("企業名稱（可多個，用逗號分隔）")
    people = st.text_input("人物姓名（可多個，用逗號分隔）")
    participants = st.text_area("受訪者清單（選填，多位請分行）")
    transcript_text = st.text_area("逐字稿內容（請直接貼上）")
    summary_points = st.text_area("重點摘要（每行一點，建議 3–7 行）")
    
    word_count = st.slider("字數範圍", 1500, 2000, (1500, 2000))
    paragraphs = st.radio("段落數", [3, 4])
    
    generate_btn = st.button("生成文章")

# ========== 右側輸出區 ==========
st.header("輸出區")

if generate_btn:
    # 檢查必填欄位
    required_fields = {
        "主題": subject,
        "企業": company,
        "人物": people,
        "逐字稿": transcript_text,
        "重點摘要": summary_points,
    }
    missing = [k for k, v in required_fields.items() if not v or not v.strip()]
    
    if missing:
        st.error("⚠️ 請填寫：" + "、".join(missing))
        st.stop()
    
    with st.spinner("⏳ 正在生成文章，請稍候..."):
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
                api_key=None,
            )
            
            st.subheader("📰 文章內容")
            st.markdown(article)
            
            st.subheader("✅ 檢查結果")
            st.json(checks)
            
            if retries == 0:
                st.success("✨ 本文一次生成，無需修稿")
            else:
                st.warning(f"✏️ 本文經過 {retries} 次自動修稿後產生")
            
            # 增加使用次數
            st.session_state.usage_count += 1
            st.info(f"已使用 {st.session_state.usage_count}/{MAX_USAGE} 次")
            
            # 若達上限，提供通知按鈕
            if st.session_state.usage_count >= MAX_USAGE:
                handle_usage_limit_notification()
        
        except Exception as e:
            st.error(f"生成文章時發生錯誤：{e}")