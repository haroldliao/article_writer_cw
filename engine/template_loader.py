import os
from pathlib import Path

def load_template(filename: str = "article_template.txt") -> str:
    """
    嘗試從多個可能路徑載入模板內容。
    若找不到檔案，直接 raise Exception（不使用預設模板）。

    Args:
        filename (str): 模板檔案名稱，預設為 article_template.txt

    Returns:
        str: 模板文字內容

    Raises:
        FileNotFoundError: 若所有搜尋路徑皆不存在
        Exception: 若讀取檔案發生其他錯誤
    """

    # 🟦 修改：以目前檔案所在資料夾為基準，動態組成搜尋路徑
    base_dir = Path(__file__).resolve().parent
    search_paths = [
        base_dir / "templates" / filename,                # engine/templates/article_template.txt ✅
        base_dir / filename,                              # engine/article_template.txt
        base_dir.parent / "templates" / filename,         # 根目錄/templates/article_template.txt
        Path.cwd() / "engine" / "templates" / filename,   # 兼容舊版 cwd 執行
    ]

    tried_paths = []  # 紀錄嘗試過的路徑

    for path in search_paths:
        tried_paths.append(str(path))
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                print(f"✅ 已載入模板：{path}")
                return content
            except Exception as e:
                raise Exception(f"模板讀取失敗：{path} ({e})")

    # 🟦 修改：找不到模板時直接 raise Exception（不使用預設模板）
    error_message = (
        "模板載入失敗：找不到 article_template.txt。\n"
        f"已嘗試以下路徑：\n" + "\n".join(f" - {p}" for p in tried_paths)
    )
    print(f"❌ {error_message}")
    raise Exception(error_message)
