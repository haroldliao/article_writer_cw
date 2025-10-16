import os
from pathlib import Path

def load_template() -> str:
    """
    讀取 article_template.txt 模板內容。
    若找不到模板檔案，回傳預設備援內容。

    Returns:
        str: 模板文字內容
    """
    # 嘗試多個可能的搜尋路徑
    search_paths = [
        Path.cwd() / "engine" / "templates" / "article_template.txt",
        Path.cwd() / "engine" / "article_template.txt",
        Path.cwd() / "data" / "article_template.txt",
        Path(__file__).parent / "templates" / "article_template.txt",
    ]

    for path in search_paths:
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                print(f"✅ 已載入模板：{path}")
                return content
            except Exception as e:
                print(f"⚠️ 無法讀取模板：{path} ({e})")

    # 若找不到檔案，使用預設模板
    print("⚠️ 找不到 article_template.txt，使用內建模板。")
    return """
# 專訪文章模板（內建簡化版）

【開場】
以情境或引言開場，帶出主題與人物。

【主體】
以段落呈現主軸人物（權重1）與輔助人物（權重2）的觀點與互動，
每段 300–500 字，保持流暢與真實感。

【結語】
收斂訪談重點，回應主題或引言，帶出未來方向。
"""
