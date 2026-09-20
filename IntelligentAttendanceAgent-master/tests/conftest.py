import sys
from pathlib import Path

# 确保项目根目录在 sys.path，便于 `from app.xxx import ...`
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
