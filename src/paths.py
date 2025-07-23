import sys
import os
from pathlib import Path

# Always add the src dir to sys.path if not present
project_root = Path(__file__).resolve().parent.parent.parent
src_root = project_root / "src"
logs_root = project_root / "logs"
if src_root not in sys.path:
	sys.path.insert(0, str(src_root))