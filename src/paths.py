import sys
import os

# Always add the src dir to sys.path if not present
SRC_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SRC_DIR not in sys.path:
	sys.path.insert(0, SRC_DIR)