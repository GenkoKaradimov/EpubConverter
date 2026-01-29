"""Unit tests for pdf_service (extract_pages, BlockData). Uses a generated test PDF."""

import tempfile
from pathlib import Path

import pytest

from services.pdf_service import BlockData, extract_pages


def _make_test_pdf(path: Path) -> None:
    """Create a minimal PDF with one page and two blocks (different font sizes) using PyMuPDF."""
    try:
        import fitz
    except ImportError:
        pytest.skip("PyMuPDF not installed")
    doc = fitz.open()
    page = doc.new_page(width=400, height=200)
    # Block 1: larger font (heading-like)
    page.insert_text((50, 50), "Chapter One", fontsize=16)
    # Block 2: normal text
    page.insert_text((50, 90), "This is paragraph text.", fontsize=11)
    doc.save(path)
    doc.close()


def test_extract_pages_returns_list_of_pages() -> None:
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        path = Path(f.name)
    try:
        _make_test_pdf(path)
        pages = extract_pages(path)
        assert isinstance(pages, list)
        assert len(pages) >= 1
        assert isinstance(pages[0], list)
        for block in pages[0]:
            assert isinstance(block, BlockData)
            assert hasattr(block, "text")
            assert hasattr(block, "font_size")
    finally:
        path.unlink(missing_ok=True)


def test_extract_pages_content_and_font_size() -> None:
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        path = Path(f.name)
    try:
        _make_test_pdf(path)
        pages = extract_pages(path)
        assert len(pages) == 1
        blocks = pages[0]
        # We expect at least some text; font_size may be present
        all_text = " ".join(b.text for b in blocks)
        assert "Chapter" in all_text or "paragraph" in all_text or "One" in all_text or "text" in all_text
        # At least one block should have font_size from PyMuPDF
        sizes = [b.font_size for b in blocks if b.font_size is not None]
        assert len(sizes) >= 1
    finally:
        path.unlink(missing_ok=True)


def test_extract_pages_file_not_found() -> None:
    with pytest.raises(FileNotFoundError, match="not found"):
        extract_pages(Path("/nonexistent/file.pdf"))


def test_extract_pages_raises_when_pymupdf_not_installed() -> None:
    """When fitz is None, extract_pages raises RuntimeError."""
    from services import pdf_service
    orig = pdf_service.fitz
    try:
        pdf_service.fitz = None
        with pytest.raises(RuntimeError, match="PyMuPDF"):
            extract_pages(Path("/any/path.pdf"))
    finally:
        pdf_service.fitz = orig
