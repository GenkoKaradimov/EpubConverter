"""
Integration script: create test PDF -> run pipeline -> verify EPUB opens.
Run from project root with PYTHONPATH=src: python tests/integration/run_pipeline_e2e.py
Skips if PyMuPDF or ebooklib not installed.
"""

import sys
import tempfile
from pathlib import Path

# Create test PDF
try:
    import fitz
except ImportError:
    print("SKIP: PyMuPDF not installed (pip install PyMuPDF)")
    sys.exit(0)
try:
    import ebooklib
    from ebooklib import epub
except ImportError:
    print("SKIP: ebooklib not installed (pip install ebooklib)")
    sys.exit(0)

from core.pipeline import run_pipeline

with tempfile.TemporaryDirectory() as tmp:
    pdf_path = Path(tmp) / "test.pdf"
    epub_path = Path(tmp) / "test.epub"
    doc = fitz.open()
    page = doc.new_page(width=400, height=200)
    page.insert_text((50, 50), "Chapter One", fontsize=14)
    page.insert_text((50, 80), "First paragraph.", fontsize=11)
    doc.save(pdf_path)
    doc.close()

    document, out_path = run_pipeline(pdf_path, epub_path)
    assert out_path.exists(), "EPUB file not created"
    book = epub.read_epub(out_path)
    full_content = b""
    for item in book.get_items():
        if item.get_type() == ebooklib.ITEM_DOCUMENT:
            full_content += item.get_content()
    text = full_content.decode("utf-8", errors="replace")
    assert "Chapter One" in text or "First paragraph" in text, "Expected content missing"

print("Integration: PDF -> pipeline -> EPUB OK (EPUB opens and has content).")
