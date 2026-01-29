"""Run Phase 3 checks: in-memory Document -> EPUB, verify file opens and content (no pytest)."""

import sys
import tempfile
from pathlib import Path

try:
    from ebooklib import epub
    import ebooklib
except ImportError:
    print("SKIP: ebooklib not installed (pip install ebooklib)")
    sys.exit(0)

from core.converters.epub_builder import EpubBuilder
from core.models import BookMetadata, ContentNode, Document

# Fixed in-memory Document
meta = BookMetadata(title="Test Book", language="en", authors=["Test Author"])
ch0 = ContentNode(id="ch_0", text="Chapter One", level=1)
p0 = ContentNode(id="p_0", text="First paragraph.", level=0)
p1 = ContentNode(id="p_1", text="Second paragraph.", level=0)
ch1 = ContentNode(id="ch_1", text="Chapter Two", level=1)
p2 = ContentNode(id="p_2", text="Only paragraph here.", level=0)
doc = Document(metadata=meta, root_nodes=[ch0, p0, p1, ch1, p2])

with tempfile.NamedTemporaryFile(suffix=".epub", delete=False) as f:
    path = Path(f.name)
try:
    builder = EpubBuilder()
    builder.build(doc, path)
    assert path.exists() and path.stat().st_size > 0
    print("epub_builder write OK")

    book = epub.read_epub(path)
    titles = book.get_metadata("DC", "title")
    assert titles and "Test Book" in str(titles[0][0])
    creators = book.get_metadata("DC", "creator")
    assert creators and "Test Author" in str(creators[0][0])
    print("epub_builder metadata OK")

    full_content = b""
    for item in book.get_items():
        if item.get_type() == ebooklib.ITEM_DOCUMENT:
            full_content += item.get_content()
    text = full_content.decode("utf-8", errors="replace")
    assert "Chapter One" in text and "First paragraph" in text
    assert "Chapter Two" in text and "Only paragraph here" in text
    print("epub_builder content OK")

finally:
    path.unlink(missing_ok=True)

print("All Phase 3 checks passed.")
