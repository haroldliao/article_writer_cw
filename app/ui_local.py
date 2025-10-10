import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import streamlit as st
from engine.generator import generate_article
import json
from datetime import datetime

st.set_page_config(
    page_title="🧠 專訪文章生成器（本機版）", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# === 自訂樣式 ===
st.markdown("""
<style>
    .stAlert > div { padding: 0.5rem 1rem; }
    .success-box { background-color: #d4edda; padding: 1rem; border-radius: 0.5rem; }
    .warning-text { color: #856404; background-color: #fff3cd; padding: 0.5rem; border-radius: 0.25rem; }
    .api-key-hint { 
        background-color: #e7f3ff; 
        padding: 1rem; 
        border-left: 4px solid #2196F3; 
        border-radius: 0.25rem;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

st.title("🧠 專訪文章生成器（本機版）")

# === Sidebar 輸入區 ===
with st.sidebar:
    st.header("⚙️ API 設定")
    
    # === API Key 輸入（本機版特有） ===
    api_key = st.text_input(
        "🔑 OpenAI API Key *",
        type="password",
        help="請輸入您的 OpenAI API Key，格式：sk-..."
    )
    
    # API Key 驗證提示
    if api_key:
        if api_key.startswith("sk-") and len(api_key) > 20:
            st.success("✅ API Key 格式正確")
        else:
            st.error("❌ API Key 格式錯誤，應以 sk- 開頭")
    else:
        st.markdown("""
        <div class="api-key-hint">
            <strong>💡 如何取得 API Key？</strong><br>
            1. 前往 <a href="https://platform.openai.com/api-keys" target="_blank">OpenAI Platform</a><br>
            2. 登入後點選「Create new secret key」<br>
            3. 複製金鑰並貼上
        </div>
        """, unsafe_allow_html=True)
    
    st.divider()
    
    # === 模型選擇 ===
    st.header("🤖 模型設定")
    model_choice = st.selectbox(
        "AI 模型選擇",
        options=[
            "gpt-4o-mini",
            "o1-preview"
        ],
        index=0,
        help="""
        - **gpt-4o-mini**：經濟快速，適合測試（推薦）
        - **o1-preview**：最強推理模型（成本較高）
        """
    )
    
    # 模型成本提示
    cost_info = {
        "gpt-4o-mini": "💰 約 $0.15 / 1M tokens（輸入）",
        "o1-preview": "💰 約 $15.00 / 1M tokens（輸入）⚠️ 成本較高"
    }
    st.caption(cost_info[model_choice])
    
    st.divider()
    st.header("📝 文章資訊")
    
    # === 必填欄位 ===
    subject = st.text_input(
        "主題 *", 
        placeholder="例：數位轉型策略",
        help="文章的核心主題"
    )
    company = st.text_input(
        "企業名稱 *", 
        placeholder="例：台灣科技公司"
    )
    
    # === 受訪者資訊（專業模式） ===
    st.subheader("👥 受訪者資訊")
    participants = st.text_area(
        "受訪者清單（每行一位）*",
        placeholder="格式：姓名／職稱／權重\n\n範例：\n王大明／執行長／1\n李小華／技術長／2\n林美玲／市場總監／2",
        height=150,
        help="權重說明：\n• 1 = 主軸人物（文章主要聚焦對象）\n• 2 = 輔助人物（提供補充觀點）"
    )
    
    # 即時預覽解析結果
    if participants:
        try:
            lines = [l.strip() for l in participants.split('\n') if l.strip()]
            parsed = []
            has_error = False
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
                    st.error("請修正以下錯誤：")
                else:
                    st.success("✅ 格式正確")
                for item in parsed:
                    st.text(item)
        except Exception:
            pass
    
    st.divider()
    st.header("📄 內容素材")
    
    transcript = st.text_area(
        "逐字稿內容 *",
        height=250,
        placeholder="請貼上採訪逐字稿...\n\n建議至少 2000 字以上，以確保文章內容豐富完整。",
        help="逐字稿是 AI 生成文章的核心素材，內容越詳細，生成品質越好"
    )
    
    # 字數統計與警告
    if transcript:
        word_count = len(transcript.replace(' ', '').replace('\n', ''))
        if word_count < 2000:
            st.error(f"❌ 目前 {word_count} 字，至少需要 2000 字")
        elif word_count < 2500:
            st.warning(f"⚠️ 目前 {word_count} 字，建議 2500 字以上效果更佳")
        else:
            st.success(f"✅ 字數統計：{word_count} 字")
    
    summary_points = st.text_area(
        "重點摘要（選填）",
        height=120,
        placeholder="每行一個重點，協助 AI 聚焦關鍵訊息\n\n範例：\n- 強調 AI 轉型的三大挑戰\n- 分享導入成功的實戰案例\n- 闡述未來五年發展願景",
        help="提供重點摘要可幫助 AI 更精準地提取核心內容"
    )
    
    st.divider()
    st.header("🎨 風格設定")
    
    col1, col2 = st.columns(2)
    with col1:
        opening_style = st.selectbox(
            "開場風格",
            options=["場景式", "金句式", "事件式", "對比式", "成就式"],
            help="""
            • 場景式：描繪採訪現場畫面
            • 金句式：以核心觀點開場
            • 事件式：從新聞事件切入
            • 對比式：呈現衝突或轉折
            • 成就式：點出企業/人物成就
            """
        )
    with col2:
        paragraphs = st.slider(
            "段落數",
            min_value=3,
            max_value=8,
            value=5,
            help="不含標題與結語，建議 4-6 段"
        )
    
    opening_context = st.text_area(
        "採訪情境（選填）",
        height=100,
        placeholder="範例：\n在公司頂樓咖啡廳，午後陽光灑入落地窗，王執行長一邊品著手沖咖啡，一邊分享他對產業的獨到見解...",
        help="提供場景描述可讓開場段落更生動、更有畫面感"
    )
    
    st.divider()
    
    # === 輸入驗證函數 ===
    def validate_inputs():
        """輸入驗證"""
        errors = []
        warnings = []
        
        # API Key 檢查
        if not api_key:
            errors.append("請輸入 OpenAI API Key")
        elif not api_key.startswith("sk-"):
            errors.append("API Key 格式錯誤（應以 sk- 開頭）")
        
        # 必填欄位檢查
        if not subject.strip():
            errors.append("請填寫主題")
        if not company.strip():
            errors.append("請填寫企業名稱")
        if not transcript.strip():
            errors.append("請貼上逐字稿")
        if not participants.strip():
            errors.append("請填寫受訪者清單")
        
        # 逐字稿字數檢查
        if transcript:
            word_count = len(transcript.replace(' ', '').replace('\n', ''))
            if word_count < 2000:
                errors.append(f"逐字稿至少需要 2000 字（目前 {word_count} 字）")
            elif word_count < 2500:
                warnings.append(f"逐字稿建議 2500 字以上（目前 {word_count} 字）")
        
        # 受訪者格式檢查
        if participants:
            lines = [l.strip() for l in participants.split('\n') if l.strip()]
            if len(lines) == 0:
                errors.append("受訪者清單不能為空")
            else:
                for idx, line in enumerate(lines, 1):
                    parts = line.split('／')
                    if len(parts) != 3:
                        errors.append(f"第 {idx} 行格式錯誤：{line[:30]}...")
                    elif parts[2] not in ['1', '2']:
                        errors.append(f"第 {idx} 行權重須為 1 或 2：{line[:30]}...")
                
                # 檢查是否有主軸人物
                weights = [l.split('／')[2] for l in lines if len(l.split('／')) == 3]
                if '1' not in weights:
                    warnings.append("建議至少設定一位主軸人物（權重 1）")
        
        return errors, warnings
    
    errors, warnings = validate_inputs()
    
    # 顯示錯誤訊息
    if errors:
        st.error("❌ 請修正以下問題：")
        for error in errors:
            st.markdown(f"• {error}")
        generate_btn = st.button("🚀 生成文章", disabled=True, use_container_width=True)
    else:
        # 顯示警告訊息（不阻擋生成）
        if warnings:
            st.warning("⚠️ 提醒：")
            for warning in warnings:
                st.markdown(f"• {warning}")
        
        generate_btn = st.button("🚀 生成文章", type="primary", use_container_width=True)

# === 主畫面輸出區 ===
if generate_btn:
    # 計算預估時間
    estimated_time = "30-60 秒" if model_choice == "gpt-4o-mini" else "60-120 秒"
    
    # 預估成本計算（粗略估算）
    if transcript:
        input_chars = len(transcript) + len(subject) + len(company) + len(participants or "")
        estimated_tokens = input_chars // 2  # 粗略估算（中文約2字元=1 token）
        
        if model_choice == "gpt-4o-mini":
            estimated_cost = (estimated_tokens / 1_000_000) * 0.15 + (4000 / 1_000_000) * 0.60
        else:  # o1-preview
            estimated_cost = (estimated_tokens / 1_000_000) * 15.00 + (4000 / 1_000_000) * 60.00
        
        st.info(f"💰 預估成本：約 ${estimated_cost:.4f} USD | ⏱️ 預計時間：{estimated_time}")
    
    with st.spinner(f"🤖 {model_choice} 正在生成文章..."):
        try:
            # 呼叫生成引擎
            article, checks, retries = generate_article(
                subject=subject,
                company=company,
                people=None,  # 不使用簡易模式
                participants=participants,
                transcript=transcript,
                summary_points=summary_points,
                opening_style=opening_style,
                opening_context=opening_context,
                paragraphs=paragraphs,
                api_key=api_key,
                model=model_choice,
                max_tokens=4000  # 設定最高 token 限制
            )
            
            # === 成功顯示 ===
            st.balloons()
            st.success(f"✅ 生成完成！使用模型：{model_choice}（重試 {retries} 次）")
            
            # === 結果分頁顯示 ===
            tab1, tab2, tab3 = st.tabs(["📄 文章內容", "🔍 品質檢查", "💾 匯出選項"])
            
            with tab1:
                st.markdown(article)
                
                # 文章統計
                word_count = len(article.replace(' ', '').replace('\n', '').replace('#', '').replace('*', ''))
                para_count = article.count('\n\n')
                st.divider()
                col1, col2, col3 = st.columns(3)
                col1.metric("文章字數", f"{word_count} 字")
                col2.metric("段落數", f"{para_count} 段")
                col3.metric("重試次數", f"{retries} 次")
            
            with tab2:
                st.subheader("品質檢查結果")
                
                # 格式化顯示檢查結果
                if isinstance(checks, dict):
                    all_passed = all(checks.values())
                    
                    if all_passed:
                        st.success("✅ 所有品質檢查項目通過")
                    else:
                        st.warning("⚠️ 部分檢查項目未通過")
                    
                    # 使用表格顯示
                    check_data = []
                    for key, value in checks.items():
                        status = "✅ 通過" if value else "❌ 未通過"
                        check_data.append({"檢查項目": key, "狀態": status})
                    
                    st.table(check_data)
                else:
                    st.json(checks)
                
                st.divider()
                st.caption("💡 若有檢查項目未通過，建議重新生成或手動調整")
            
            with tab3:
                st.subheader("匯出選項")
                
                col1, col2, col3 = st.columns(3)
                
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                
                with col1:
                    st.download_button(
                        label="📥 下載 Markdown",
                        data=article,
                        file_name=f"interview_{timestamp}.md",
                        mime="text/markdown",
                        use_container_width=True
                    )
                
                with col2:
                    # 轉換為純文字（移除 Markdown 語法）
                    plain_text = article.replace('#', '').replace('*', '').replace('_', '')
                    st.download_button(
                        label="📥 下載純文字",
                        data=plain_text,
                        file_name=f"interview_{timestamp}.txt",
                        mime="text/plain",
                        use_container_width=True
                    )
                
                with col3:
                    # 匯出完整結果（含 metadata）
                    full_result = {
                        "article": article,
                        "metadata": {
                            "subject": subject,
                            "company": company,
                            "participants": participants,
                            "model": model_choice,
                            "max_tokens": 4000,
                            "retries": retries,
                            "generated_at": datetime.now().isoformat(),
                            "word_count": word_count
                        },
                        "checks": checks
                    }
                    st.download_button(
                        label="📥 下載 JSON",
                        data=json.dumps(full_result, ensure_ascii=False, indent=2),
                        file_name=f"interview_{timestamp}.json",
                        mime="application/json",
                        use_container_width=True
                    )
                
                st.divider()
                
                # 複製提示
                st.info("💡 **快速複製：**\n- 文章內容：直接選取文字後按 Ctrl+C（Windows）或 Cmd+C（Mac）\n- 完整資料：下載 JSON 格式保留所有資訊")
                
                # 顯示生成資訊
                with st.expander("📊 生成詳細資訊"):
                    st.json({
                        "模型": model_choice,
                        "最大 Token": 4000,
                        "生成時間": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        "重試次數": retries,
                        "輸入字數": len(transcript.replace(' ', '').replace('\n', '')),
                        "輸出字數": word_count,
                        "API Key 狀態": "已驗證" if api_key.startswith("sk-") else "格式錯誤"
                    })
        
        except Exception as e:
            st.error(f"❌ 生成失敗")
            
            # 詳細錯誤資訊
            with st.expander("🐛 錯誤詳情（點擊展開）", expanded=True):
                st.code(str(e))
                
                # 常見錯誤提示（本機版特別關注 API Key 問題）
                error_str = str(e).lower()
                if "api key" in error_str or "authentication" in error_str or "unauthorized" in error_str:
                    st.warning("""
                    **可能原因：**
                    - API Key 無效或已過期
                    - API Key 權限不足
                    - 未啟用相關模型存取權限
                    
                    **建議：**
                    1. 前往 [OpenAI Platform](https://platform.openai.com/api-keys) 檢查 API Key
                    2. 確認帳戶有足夠額度
                    3. 檢查是否有權使用所選模型（o1-preview 需額外申請）
                    4. 嘗試重新生成新的 API Key
                    """)
                elif "rate limit" in error_str or "quota" in error_str:
                    st.warning("""
                    **可能原因：**
                    - API 配額已用完
                    - 請求頻率過高
                    - 超過帳戶使用限制
                    
                    **建議：**
                    1. 檢查 [OpenAI 使用額度](https://platform.openai.com/usage)
                    2. 等待幾分鐘後再試
                    3. 考慮升級方案或增加額度
                    """)
                elif "model" in error_str:
                    st.warning("""
                    **可能原因：**
                    - 模型名稱錯誤
                    - 帳戶無權使用此模型
                    - 模型已被棄用
                    
                    **建議：**
                    1. 確認模型可用性
                    2. o1-preview 需要特殊存取權限
                    3. 嘗試切換至 gpt-4o-mini
                    """)
                elif "timeout" in error_str or "connection" in error_str:
                    st.warning("""
                    **可能原因：**
                    - 請求超時
                    - 網路連線不穩定
                    - OpenAI 服務暫時無法連線
                    
                    **建議：**
                    1. 檢查網路連線
                    2. 稍後重試
                    3. 檢查 [OpenAI 狀態頁面](https://status.openai.com/)
                    """)
                else:
                    st.info("""
                    **一般建議：**
                    1. 檢查所有輸入格式是否正確
                    2. 確認逐字稿內容完整且無特殊字元
                    3. 嘗試縮短逐字稿後重試
                    4. 檢查網路連線狀態
                    5. 若問題持續，請聯繫支援
                    """)

# === 頁尾資訊 ===
st.divider()
footer_col1, footer_col2, footer_col3, footer_col4 = st.columns(4)
footer_col1.caption(f"🕒 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
footer_col2.caption(f"🤖 模型：{model_choice}")
footer_col3.caption(f"⚙️ Max Tokens: 4000")
footer_col4.caption(f"💻 本機版")

# === 側邊欄底部說明 ===
with st.sidebar:
    st.divider()
    with st.expander("ℹ️ 本機版說明"):
        st.markdown("""
        ### 本機版 vs 雲端版差異
        
        **本機版（當前）：**
        - ✅ 需手動輸入 API Key
        - ✅ API Key 不會被儲存
        - ✅ 適合個人使用
        - ✅ 完全掌控金鑰安全
        
        **雲端版：**
        - ✅ API Key 儲存在 Streamlit Secrets
        - ✅ 適合團隊共用
        - ✅ 需要部署到雲端
        
        ### 安全提醒
        - 🔒 切勿分享您的 API Key
        - 🔒 使用後建議清除瀏覽器快取
        - 🔒 定期檢查 API 使用量
        - 🔒 發現異常立即撤銷金鑰
        
        ### 成本控制建議
        - 💰 先用 gpt-4o-mini 測試
        - 💰 確認效果後再用 o1-preview
        - 💰 設定 OpenAI 帳戶用量警告
        - 💰 定期檢視使用報告
        """)
    
    with st.expander("🆘 常見問題"):
        st.markdown("""
        **Q: API Key 會被儲存嗎？**  
        A: 不會。本機版每次都需要重新輸入，關閉視窗後就會清除。
        
        **Q: 如何降低使用成本？**  
        A: 優先使用 gpt-4o-mini，僅在需要高品質推理時使用 o1-preview。
        
        **Q: 為什麼生成失敗？**  
        A: 常見原因：
        1. API Key 錯誤或過期
        2. 帳戶額度不足
        3. 逐字稿格式問題
        4. 網路連線異常
        
        **Q: o1-preview 和 gpt-4o-mini 差異？**  
        A: 
        - **o1-preview**：推理能力強，適合複雜分析，成本高
        - **gpt-4o-mini**：速度快成本低，適合一般文章生成
        
        **Q: 如何取得 o1-preview 存取權？**  
        A: 目前 o1-preview 需要額外申請，請至 OpenAI 平台查看資格。
        """)