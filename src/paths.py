import sys
from pathlib import Path

# project_root = parent of the directory containing paths.py
project_root = Path(__file__).resolve().parent.parent
src_root = project_root / "src"
logs_root = project_root / "logs"

if str(project_root) not in sys.path:
	sys.path.insert(0, str(project_root))

print(f"[debug] sys.path: {sys.path}")
print(f"[debug] project_root: {project_root}")
print(f"[debug] src_root: {src_root}")
print(f"[debug] logs_root: {logs_root}")
