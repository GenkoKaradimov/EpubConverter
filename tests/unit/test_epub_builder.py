"""Unit tests for EpubBuilder: in-memory Document -> EPUB, verify file opens and content."""

import tempfile
from pathlib import Path

import pytest

from core.converters.epub_builder import EpubBuilder
from core.models import BookMetadata, ContentNode, Document, ImageNode


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


def test_epub_builder_with_image_node() -> None:
    """Document with ImageNode and image on disk produces EPUB with img tag and image item."""
    try:
        import ebooklib
        from ebooklib import epub
    except ImportError:
        pytest.skip("ebooklib not installed")

    meta = BookMetadata(title="Book With Image", language="en")
    p = ContentNode(id="p_0", text="See below.", level=0)
    img_node = ImageNode(id="img_node_0", image_id="img_0", alt="A figure")
    with tempfile.TemporaryDirectory() as tmp:
        img_path = Path(tmp) / "img_0.png"
        img_path.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82")
        doc = Document(metadata=meta, root_nodes=[p, img_node], images={"img_0": img_path})
        builder = EpubBuilder()
        out_path = Path(tmp) / "out.epub"
        builder.build(doc, out_path)
        book = epub.read_epub(out_path)
        full_content = b""
        for item in book.get_items():
            if item.get_type() == ebooklib.ITEM_DOCUMENT:
                full_content += item.get_content()
        text = full_content.decode("utf-8", errors="replace")
        assert "See below" in text
        assert "<img" in text or "img_" in text
        has_image_item = any(item.get_type() == ebooklib.ITEM_IMAGE for item in book.get_items())
        assert has_image_item


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
