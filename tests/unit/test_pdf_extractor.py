"""Unit tests for PdfExtractor: returns correct Document + BookMetadata from PDF."""

import tempfile
from pathlib import Path

import pytest

from core.converters.pdf_extractor import PdfExtractor
from core.models import BookMetadata, Document


def _make_simple_pdf(path: Path, title: str = "Test Book") -> None:
    """Create a minimal PDF with optional metadata using PyMuPDF."""
    try:
        import fitz
    except ImportError:
        pytest.skip("PyMuPDF not installed")
    doc = fitz.open()
    doc.set_metadata({"title": title, "author": "Test Author"})
    page = doc.new_page(width=400, height=200)
    page.insert_text((50, 50), "First Chapter", fontsize=14)
    page.insert_text((50, 80), "Some body text here.", fontsize=11)
    doc.save(path)
    doc.close()


def test_pdf_extractor_returns_document() -> None:
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        path = Path(f.name)
    try:
        _make_simple_pdf(path)
        extractor = PdfExtractor()
        doc = extractor.extract(path)
        assert isinstance(doc, Document)
        assert isinstance(doc.metadata, BookMetadata)
        assert doc.metadata.title == "Test Book"
        assert "Test Author" in doc.metadata.authors
        assert len(doc.root_nodes) >= 1
        flat = doc.flat_list()
        assert len(flat) >= 1
        texts = [n.text for n in flat if hasattr(n, "text")]
        assert any("Chapter" in t or "First" in t for t in texts)
        assert any("body" in t or "text" in t for t in texts)
    finally:
        path.unlink(missing_ok=True)


def test_pdf_extractor_file_not_found() -> None:
    extractor = PdfExtractor()
    with pytest.raises(FileNotFoundError, match="not found"):
        extractor.extract(Path("/nonexistent/file.pdf"))


def test_pdf_extractor_heading_heuristic() -> None:
    """Blocks with larger font become level 1; others level 0."""
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        path = Path(f.name)
    try:
        _make_simple_pdf(path)
        extractor = PdfExtractor(heading_ratio=1.2)
        doc = extractor.extract(path)
        flat = doc.flat_list()
        levels = [n.level for n in flat if hasattr(n, "level")]
        assert 0 in levels
        # We expect at least one heading (level 1) when font sizes differ
        assert 1 in levels
    finally:
        path.unlink(missing_ok=True)
