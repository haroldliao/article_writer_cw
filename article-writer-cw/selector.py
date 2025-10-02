import os
from pathlib import Path

# 自動找到專案根目錄 (假設專案結構中 styles/ 與 app/, engine/ 在同一層)
PROJECT_ROOT = Path(__file__).resolve().parent
while PROJECT_ROOT != PROJECT_ROOT.root:
    if (PROJECT_ROOT / "styles").exists():
        break
    PROJECT_ROOT = PROJECT_ROOT.parent

STYLE_DIR = PROJECT_ROOT / "styles"

# 風格映射表
STYLE_MAPPING = {
    "企業": "style_corporate.md",
    "學校": "style_school.md",
    "政府": "style_government.md"
}

def list_styles() -> list[str]:
    """列出所有可用風格標籤"""
    return [
        label for label, fname in STYLE_MAPPING.items()
        if (STYLE_DIR / fname).exists()
    ]

def load_style(style_label: str) -> str:
    """
    載入指定風格檔案內容
    
    Args:
        style_label: 風格標籤 ("企業", "學校", "政府")
    
    Returns:
        風格檔案的文字內容
    
    Raises:
        ValueError: 風格不存在
        FileNotFoundError: 檔案不存在
    """
    if style_label not in STYLE_MAPPING:
        available = list_styles()
        raise ValueError(f"風格「{style_label}」不存在。可用風格: {available}")
    
    path = STYLE_DIR / STYLE_MAPPING[style_label]
    
    if not path.exists():
        raise FileNotFoundError(f"風格檔案不存在: {path}")
    
    return path.read_text(encoding="utf-8")

def get_style_path(style_label: str) -> Path:
    """
    取得指定風格檔案的完整路徑
    """
    if style_label not in STYLE_MAPPING:
        raise ValueError(f"風格「{style_label}」不存在")
    return STYLE_DIR / STYLE_MAPPING[style_label]
