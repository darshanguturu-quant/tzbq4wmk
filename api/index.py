"""
Vercel Serverless Function entry point for FastAPI backend.
"""

import sys
from pathlib import Path

# Add repository root to Python module search path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from backend.app.main import app  # noqa: F401
