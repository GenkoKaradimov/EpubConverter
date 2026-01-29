"""Unit tests for EpubExtractor: EPUB file -> Document, metadata and content."""

import tempfile
from pathlib import Path

import pytest

from core.converters.epub_builder import EpubBuilder
from core.converters.epub_extractor import EpubExtractor
from core.models import BookMetadata, ContentNode, Document


def _make_sample_document() -> Document:
    """Fixed in-memory Document: one chapter (h1 + 2 paragraphs), second chapter (h1 + 1 paragraph)."""
    meta = BookMetadata(title="Test Book", language="en", authors=["Test Author"])
    ch0 = ContentNode(id="ch_0", text="Chapter One", level=1)
    p0 = ContentNode(id="p_0", text="First paragraph.", level=0)
    p1 = ContentNode(id="p_1", text="Second paragraph.", level=0)
    ch1 = ContentNode(id="ch_1", text="Chapter Two", level=1)
    p2 = ContentNode(id="p_2", text="Only paragraph here.", level=0)
    root_nodes = [ch0, p0, p1, ch1, p2]
    return Document(metadata=meta, root_nodes=root_nodes)


def test_epub_extractor_extracts_metadata_and_content() -> None:
    try:
        import ebooklib
        from ebooklib import epub
    except ImportError:
        pytest.skip("ebooklib not installed")

    doc = _make_sample_document()
    with tempfile.NamedTemporaryFile(suffix=".epub", delete=False) as f:
        path = Path(f.name)
    try:
        EpubBuilder().build(doc, path)
        extracted = EpubExtractor().extract(path)
        assert extracted.metadata.title == "Test Book"
        assert extracted.metadata.language == "en"
        assert "Test Author" in extracted.metadata.authors
        flat = extracted.flat_list()
        assert len(flat) >= 5
        texts = [n.text for n in flat]
        assert "Chapter One" in texts
        assert "First paragraph." in texts
        assert "Second paragraph." in texts
        assert "Chapter Two" in texts
        assert "Only paragraph here." in texts
        levels = [n.level for n in flat]
        assert 1 in levels
        assert 0 in levels
    finally:
        path.unlink(missing_ok=True)


def test_epub_extractor_raises_on_missing_file() -> None:
    extractor = EpubExtractor()
    with pytest.raises(FileNotFoundError, match="EPUB not found|not found"):
        extractor.extract(Path("/nonexistent/epub/file.epub"))


def test_epub_extractor_raises_when_ebooklib_not_installed() -> None:
    from core.converters import epub_extractor

    orig_epub = epub_extractor.epub
    orig_ebooklib = epub_extractor.ebooklib
    try:
        epub_extractor.epub = None
        epub_extractor.ebooklib = None
        extractor = EpubExtractor()
        with tempfile.NamedTemporaryFile(suffix=".epub", delete=False) as f:
            path = Path(f.name)
        try:
            with pytest.raises(RuntimeError, match="ebooklib"):
                extractor.extract(path)
        finally:
            path.unlink(missing_ok=True)
    finally:
        epub_extractor.epub = orig_epub
        epub_extractor.ebooklib = orig_ebooklib
