"""Unit tests for EpubBuilder: in-memory Document -> EPUB, verify file opens and content."""

import tempfile
from pathlib import Path

import pytest

from core.converters.epub_builder import EpubBuilder
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


def test_epub_builder_writes_file() -> None:
    doc = _make_sample_document()
    builder = EpubBuilder()
    with tempfile.NamedTemporaryFile(suffix=".epub", delete=False) as f:
        path = Path(f.name)
    try:
        builder.build(doc, path)
        assert path.exists()
        assert path.stat().st_size > 0
    finally:
        path.unlink(missing_ok=True)


def test_epub_builder_file_opens_and_has_content() -> None:
    try:
        import ebooklib
        from ebooklib import epub
    except ImportError:
        pytest.skip("ebooklib not installed")

    doc = _make_sample_document()
    builder = EpubBuilder()
    with tempfile.NamedTemporaryFile(suffix=".epub", delete=False) as f:
        path = Path(f.name)
    try:
        builder.build(doc, path)
        book = epub.read_epub(path)
        # Metadata
        titles = book.get_metadata("DC", "title")
        assert titles and any("Test Book" in str(t[0]) for t in titles)
        creators = book.get_metadata("DC", "creator")
        assert creators and any("Test Author" in str(c[0]) for c in creators)
        # Document items: find xhtml and check body content
        full_content = b""
        for item in book.get_items():
            if item.get_type() == ebooklib.ITEM_DOCUMENT:
                full_content += item.get_content()
        text = full_content.decode("utf-8", errors="replace")
        assert "Chapter One" in text
        assert "First paragraph" in text
        assert "Second paragraph" in text
        assert "Chapter Two" in text
        assert "Only paragraph here" in text
    finally:
        path.unlink(missing_ok=True)


def test_epub_builder_raises_when_ebooklib_not_installed() -> None:
    from core.converters import epub_builder

    orig = epub_builder.epub
    try:
        epub_builder.epub = None
        builder = EpubBuilder()
        doc = _make_sample_document()
        with tempfile.NamedTemporaryFile(suffix=".epub", delete=False) as f:
            path = Path(f.name)
        try:
            with pytest.raises(RuntimeError, match="ebooklib"):
                builder.build(doc, path)
        finally:
            path.unlink(missing_ok=True)
    finally:
        epub_builder.epub = orig
