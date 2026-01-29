"""
Minimal application configuration: paths, default language, file size limits.
Loads optional overrides from .env when python-dotenv is available.
"""

import os
import tempfile
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Base paths
APP_NAME = "EpubConverter"
USER_HOME = Path(os.path.expanduser("~"))
APP_DATA_DIR = USER_HOME / ".config" / APP_NAME
TEMP_DIR = Path(tempfile.gettempdir())
DEFAULT_OUTPUT_DIR = USER_HOME / "Documents"

# Ensure app data dir exists when used (call ensure_dirs() at startup if needed)
def ensure_dirs() -> None:
    """Create application directories if they do not exist."""
    APP_DATA_DIR.mkdir(parents=True, exist_ok=True)

# Default language for book metadata (e.g. EPUB dc:language)
DEFAULT_LANGUAGE = os.environ.get("EPUBCONVERTER_LANGUAGE", "en")

# File size limits (bytes); 0 or None means no limit
MAX_PDF_SIZE_BYTES = int(os.environ.get("EPUBCONVERTER_MAX_PDF_MB", "500")) * 1024 * 1024
MAX_EPUB_SIZE_BYTES = int(os.environ.get("EPUBCONVERTER_MAX_EPUB_MB", "100")) * 1024 * 1024
