"""
Integration test: PDF -> pipeline -> EPUB; verify EPUB opens and has expected content.
Requires PyMuPDF and ebooklib. Skips if not installed.
"""

import tempfile
from pathlib import Path

import pytest

from core.pipeline import PipelineError, run_pipeline


def _make_test_pdf(path: Path) -> None:
    """Create a minimal PDF with one page and some text using PyMuPDF."""
    try:
        import fitz
    except ImportError:
        pytest.skip("PyMuPDF not installed")
    doc = fitz.open()
    page = doc.new_page(width=400, height=200)
    page.insert_text((50, 50), "Chapter One", fontsize=14)
    page.insert_text((50, 80), "First paragraph.", fontsize=11)
    doc.save(path)
    doc.close()


def test_pipeline_pdf_to_epub_creates_file() -> None:
    try:
        import ebooklib
        from ebooklib import epub
    except ImportError:
        pytest.skip("ebooklib not installed")

    with tempfile.TemporaryDirectory() as tmp:
        pdf_path = Path(tmp) / "test.pdf"
        epub_path = Path(tmp) / "test.epub"
        _make_test_pdf(pdf_path)
        document, out_path = run_pipeline(pdf_path, epub_path)
        assert out_path == epub_path
        assert out_path.exists()
        assert out_path.stat().st_size > 0
        assert document is not None
        assert len(document.flat_list()) >= 1


def test_pipeline_epub_opens_and_has_content() -> None:
    try:
        import ebooklib
        from ebooklib import epub
    except ImportError:
        pytest.skip("ebooklib not installed")

    with tempfile.TemporaryDirectory() as tmp:
        pdf_path = Path(tmp) / "test.pdf"
        epub_path = Path(tmp) / "test.epub"
        _make_test_pdf(pdf_path)
        run_pipeline(pdf_path, epub_path)
        book = epub.read_epub(epub_path)
        titles = book.get_metadata("DC", "title")
        assert titles
        full_content = b""
        for item in book.get_items():
            if item.get_type() == ebooklib.ITEM_DOCUMENT:
                full_content += item.get_content()
        text = full_content.decode("utf-8", errors="replace")
        assert "Chapter One" in text or "First paragraph" in text


def test_pipeline_default_epub_path() -> None:
    try:
        import fitz
        from ebooklib import epub
    except ImportError:
        pytest.skip("PyMuPDF or ebooklib not installed")

    with tempfile.TemporaryDirectory() as tmp:
        pdf_path = Path(tmp) / "sample.pdf"
        _make_test_pdf(pdf_path)
        document, out_path = run_pipeline(pdf_path, epub_path=None)
        expected = pdf_path.with_suffix(".epub")
        assert out_path == expected
        assert out_path.exists()


def test_pipeline_missing_pdf_raises() -> None:
    with pytest.raises(PipelineError, match="not found"):
        run_pipeline(Path("/nonexistent/file.pdf"))
