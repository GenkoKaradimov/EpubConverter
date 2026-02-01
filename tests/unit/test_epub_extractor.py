"""Unit tests for EpubExtractor: EPUB file -> Document, metadata and content. Includes fallback (directory/ZIP) for pdf2epub-style EPUBs."""

import tempfile
import zipfile
from pathlib import Path

import pytest

from core.converters.epub_builder import EpubBuilder
from core.converters.epub_extractor import EpubExtractor
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
        texts = [n.text for n in flat if isinstance(n, ContentNode)]
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


def test_epub_extractor_from_unzipped_directory() -> None:
    """Extract from pdf2epub-style unzipped folder (META-INF, OPS/package.opf, OPS/*.xhtml)."""
    CONTAINER_XML = """<?xml version="1.0"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OPS/package.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
"""
    PACKAGE_OPF = """<?xml version="1.0"?>
<package version="3.0" xmlns="http://www.idpf.org/2007/opf" unique-identifier="pub-id">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:title>Fallback Test</dc:title>
    <dc:language>en</dc:language>
    <dc:creator>Test Author</dc:creator>
    <dc:identifier id="pub-id">urn:uuid:test</dc:identifier>
  </metadata>
  <manifest>
    <item id="titlepage" href="titlepage.xhtml" media-type="application/xhtml+xml"/>
    <item id="s00000" href="s00000-beta.xhtml" media-type="application/xhtml+xml"/>
  </manifest>
  <spine toc="ncx">
    <itemref idref="titlepage" linear="yes"/>
    <itemref idref="s00000" linear="yes"/>
  </spine>
</package>
"""
    TITLEPAGE_XHTML = """<?xml version="1.0"?><html xmlns="http://www.w3.org/1999/xhtml"><body><p>Cover</p></body></html>"""
    CHAPTER_XHTML = """<?xml version="1.0"?><html xmlns="http://www.w3.org/1999/xhtml"><body><h1>Chapter One</h1><p>First paragraph.</p></body></html>"""

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "META-INF").mkdir()
        (root / "META-INF" / "container.xml").write_text(CONTAINER_XML, encoding="utf-8")
        (root / "OPS").mkdir()
        (root / "OPS" / "package.opf").write_text(PACKAGE_OPF, encoding="utf-8")
        (root / "OPS" / "titlepage.xhtml").write_text(TITLEPAGE_XHTML, encoding="utf-8")
        (root / "OPS" / "s00000-beta.xhtml").write_text(CHAPTER_XHTML, encoding="utf-8")
        images_dir = root / "out_images"

        doc = EpubExtractor().extract(root, images_dir=images_dir)
        assert doc.metadata.title == "Fallback Test"
        assert doc.metadata.language == "en"
        assert "Test Author" in doc.metadata.authors
        flat = doc.flat_list()
        texts = [n.text for n in flat if isinstance(n, ContentNode)]
        assert "Cover" in texts
        assert "Chapter One" in texts
        assert "First paragraph." in texts


def test_epub_extractor_from_zip_fallback() -> None:
    """When ebooklib fails (e.g. mimetype compressed), fallback to ZIP parsing yields a document."""
    CONTAINER_XML = """<?xml version="1.0"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OPS/package.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
"""
    PACKAGE_OPF = """<?xml version="1.0"?>
<package version="3.0" xmlns="http://www.idpf.org/2007/opf" unique-identifier="pub-id">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:title>Zip Fallback Test</dc:title>
    <dc:language>en</dc:language>
    <dc:creator>Zip Author</dc:creator>
  </metadata>
  <manifest>
    <item id="s00000" href="s00000-chap.xhtml" media-type="application/xhtml+xml"/>
  </manifest>
  <spine toc="ncx">
    <itemref idref="s00000" linear="yes"/>
  </spine>
</package>
"""
    CHAPTER_XHTML = """<?xml version="1.0"?><html xmlns="http://www.w3.org/1999/xhtml"><body><h1>Zip Chapter</h1><p>From zip.</p></body></html>"""

    with tempfile.NamedTemporaryFile(suffix=".epub", delete=False) as f:
        zip_path = Path(f.name)
    try:
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("mimetype", "application/epub+zip", zipfile.ZIP_DEFLATED)
            zf.writestr("META-INF/container.xml", CONTAINER_XML.encode("utf-8"))
            zf.writestr("OPS/package.opf", PACKAGE_OPF.encode("utf-8"))
            zf.writestr("OPS/s00000-chap.xhtml", CHAPTER_XHTML.encode("utf-8"))
        images_dir = zip_path.parent / (zip_path.stem + "_images")
        doc = EpubExtractor().extract(zip_path, images_dir=images_dir)
        assert doc.metadata.title == "Zip Fallback Test"
        assert "Zip Author" in doc.metadata.authors
        texts = [n.text for n in doc.flat_list() if isinstance(n, ContentNode)]
        assert "Zip Chapter" in texts
        assert "From zip." in texts
    finally:
        zip_path.unlink(missing_ok=True)
