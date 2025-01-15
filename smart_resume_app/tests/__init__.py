"""Test package initialization."""
from pathlib import Path
import sys

# Add project root to Python path for imports
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)
