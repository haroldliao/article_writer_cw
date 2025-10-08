"""
ui_public.py（雲端正式版 - 含分段重寫功能）
使用 Streamlit Secrets 管理 API Key
"""

import streamlit as st
from engine.generator import generate_article, parse_article_to_blocks, build_article_from_blocks, regenerate_block


def main():
    st.set_page_config(page_title="新聞稿生成器", page_icon="📰", layout="wide")
    
    st.title("📰 新聞稿生成器（雲端正式版）")
    st.markdown("---")

    # === 側邊欄：基本設定 ===
    with st.sidebar:
        st.header("⚙️ 基本設定")
        
        # API Key 從 Streamlit Secrets 讀取
        try:
            api_key = st.secrets["OPENAI_API_KEY"]
            st.success("✅ API Key 已從 Secrets 載入")
        except Exception:
            st.error("❌ 無法載入 API Key，請檢查 Streamlit Secrets 設定")
            st.stop()
        
        model = st.selectbox(
            "選擇模型",
            ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"],
            index=0
        )
        
        word_count_label = st.selectbox(
            "字數範圍",
            ["300-500", "500-800", "800-1200"],
            index=1
        )
        # ✅ 將字數範圍轉為 tuple
        word_count_range = tuple(map(int, word_count_label.split("-")))
        
        paragraphs = st.slider("段落數量", 3, 8, 5)

    # === 主要輸入區 ===
    st.header("📝 新聞稿內容設定")
    
    col1, col2 = st.columns(2)
    
    with col1:
        subject = st.text_input(
            "新聞主題 *",
            placeholder="例：公司推出新產品",
            help="必填：描述新聞的核心主題"
        )
        
        company = st.text_input(
            "公司名稱 *",
            placeholder="例：科技創新股份有限公司",
            help="必填：發布新聞的公司名稱"
        )
    
    with col2:
        people = st.text_input(
            "相關人物",
            placeholder="例：執行長王大明、技術長李小華",
            help="選填：新聞中提及的重要人物"
        )
        
        participants = st.text_input(
            "參與單位",
            placeholder="例：工研院、台大、資策會",
            help="選填：合作或參與的其他單位"
        )

    # === 開場風格設定 ===
    st.subheader("🎨 開場風格")
    
    opening_style = st.selectbox(
        "選擇開場方式",
        [
            "直述主題",
            "引用名言",
            "提出問題",
            "描述場景",
            "數據開場",
            "故事開場"
        ],
        help="選擇新聞稿的開場風格"
    )
    
    opening_context = st.text_area(
        "開場補充說明（選填）",
        placeholder="例：強調產品的創新性、市場需求、社會影響等",
        height=100,
        help="提供額外的開場方向指引"
    )

    # === 內容要點 ===
    st.subheader("📋 內容要點")
    
    summary_points = st.text_area(
        "關鍵訊息（每行一個要點）",
        placeholder="• 產品特色與優勢\n• 市場定位與目標客群\n• 預期效益與影響\n• 未來發展計畫",
        height=150,
        help="條列式輸入新聞稿應包含的重點內容"
    )

    # === 生成按鈕 ===
    st.markdown("---")
    
    if st.button("🚀 生成新聞稿", type="primary", use_container_width=True):
        # 驗證必填欄位
        if not subject or not company:
            st.error("❌ 請填寫「新聞主題」和「公司名稱」")
            st.stop()
        
        with st.spinner("🤖 AI 正在生成新聞稿..."):
            try:
                # 呼叫生成引擎
                article, checks, retries = generate_article(
                    api_key=api_key,
                    model=model,
                    subject=subject.strip(),
                    company=company.strip(),
                    people=people.strip(),
                    participants=participants.strip(),
                    summary_points=summary_points.strip(),
                    opening_style=opening_style,
                    opening_context=opening_context.strip(),
                    word_count_range=word_count_range,
                    paragraphs=paragraphs,
                )
                
                # 儲存資料
                st.session_state.meta = {
                    "subject": subject.strip(),
                    "company": company.strip(),
                    "people": people.strip(),
                    "participants": participants.strip(),
                    "summary_points": summary_points.strip(),
                    "opening_style": opening_style,
                    "opening_context": opening_context,
                    "word_count_range": word_count_range,
                    "paragraphs": paragraphs,
                }
                st.session_state.blocks = parse_article_to_blocks(article)
                st.session_state.article = article
                
                # ✅ 顯示結果
                st.success(f"✅ 新聞稿生成成功！（重試次數：{retries}）")
                st.json(checks)
                
            except Exception as e:
                st.error(f"❌ 生成失敗：{str(e)}")
                st.stop()

    # === 顯示生成結果 ===
    if "article" in st.session_state:
        st.markdown("---")
        st.header("📰 生成結果")
        
        with st.container():
            st.markdown(st.session_state.article)
        
        st.download_button(
            label="📥 下載新聞稿 (TXT)",
            data=st.session_state.article,
            file_name="新聞稿.txt",
            mime="text/plain"
        )

    # === 區塊編輯 UI（分段重寫）===
    if "blocks" in st.session_state and st.session_state.blocks:
        st.divider()
        st.subheader("🧩 區塊編輯（逐段重寫）")
        st.info("💡 您可以手動編輯每個段落，或使用 AI 重新生成特定段落")

        for idx, block in enumerate(st.session_state.blocks):
            with st.expander(f"{idx+1}. [{block['role']}] {block['title']}", expanded=True):
                edited = st.text_area(
                    "段落內容（可手動修改後套用）",
                    value=block["content"],
                    height=220,
                    key=f"ta_{idx}"
                )

                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✏️ 重生本段", key=f"regen_{idx}", use_container_width=True):
                        with st.spinner(f"🤖 正在重生第 {idx+1} 段..."):
                            try:
                                new_block = regenerate_block(
                                    index=idx,
                                    blocks=st.session_state.blocks,
                                    meta=st.session_state.meta,
                                    api_key=api_key,
                                    model=model,
                                )
                                st.session_state.blocks[idx] = new_block
                                st.success(f"✅ 第 {idx+1} 段已重生")
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ 重生段落失敗：{e}")

                with col2:
                    if st.button("✅ 套用手動更改", key=f"apply_{idx}", use_container_width=True):
                        st.session_state.blocks[idx]["content"] = edited
                        st.success(f"✅ 第 {idx+1} 段已套用手動更改")
                        st.rerun()

        # === 重新組稿預覽 ===
        st.divider()
        col_preview, col_apply = st.columns([2, 1])
        with col_preview:
            if st.button("🧵 重新組稿預覽", use_container_width=True):
                st.session_state.preview_article = build_article_from_blocks(st.session_state.blocks)
        with col_apply:
            if st.button("💾 套用為最終稿", type="primary", use_container_width=True):
                st.session_state.article = build_article_from_blocks(st.session_state.blocks)
                st.success("✅ 已套用為最終稿")
                st.rerun()

        if "preview_article" in st.session_state:
            st.subheader("📰 重組後文章預覽")
            with st.container():
                st.markdown(st.session_state.preview_article)
            st.download_button(
                label="📥 下載重組稿 (TXT)",
                data=st.session_state.preview_article,
                file_name="新聞稿_重組.txt",
                mime="text/plain",
                key="download_preview"
            )

    # === 頁尾 ===
    st.markdown("---")
    st.caption("🔒 使用 Streamlit Secrets 安全管理 API Key | Powered by OpenAI")


if __name__ == "__main__":
    main()
