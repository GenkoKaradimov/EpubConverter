"""Run Phase 2 checks: pdf_service and pdf_extractor with a generated test PDF (no pytest)."""

import sys
import tempfile
from pathlib import Path

# Create minimal PDF with PyMuPDF
try:
    import fitz
except ImportError:
    print("SKIP: PyMuPDF not installed (pip install pymupdf)")
    sys.exit(0)

with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
    pdf_path = Path(f.name)
try:
    doc = fitz.open()
    page = doc.new_page(width=400, height=200)
    page.insert_text((50, 50), "Chapter One", fontsize=14)
    page.insert_text((50, 80), "Body text.", fontsize=11)
    doc.save(pdf_path)
    doc.close()

    # pdf_service
    from services.pdf_service import BlockData, extract_pages

    pages = extract_pages(pdf_path)
    assert isinstance(pages, list) and len(pages) >= 1
    assert all(isinstance(b, BlockData) for b in pages[0])
    text_all = " ".join(b.text for b in pages[0])
    assert "Chapter" in text_all or "Body" in text_all
    print("pdf_service OK")

    # pdf_extractor
    from core.converters.pdf_extractor import PdfExtractor
    from core.models import BookMetadata, Document

    extractor = PdfExtractor()
    document = extractor.extract(pdf_path)
    assert isinstance(document, Document)
    assert isinstance(document.metadata, BookMetadata)
    assert len(document.root_nodes) >= 1
    flat = document.flat_list()
    assert len(flat) >= 1
    print("pdf_extractor OK")

finally:
    pdf_path.unlink(missing_ok=True)

print("All Phase 2 checks passed.")
