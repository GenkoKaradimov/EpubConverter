"""Run fallback extraction checks without pytest (directory and ZIP)."""

import sys
import tempfile
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from core.converters.epub_extractor import EpubExtractor
from core.models import ContentNode

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


def test_directory() -> None:
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
        texts = [n.text for n in doc.flat_list() if isinstance(n, ContentNode)]
        assert "Cover" in texts
        assert "Chapter One" in texts
        assert "First paragraph." in texts
    print("directory fallback: OK")


def test_zip() -> None:
    with tempfile.NamedTemporaryFile(suffix=".epub", delete=False) as f:
        zip_path = Path(f.name)
    try:
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("mimetype", "application/epub+zip", zipfile.ZIP_DEFLATED)
            zf.writestr("META-INF/container.xml", CONTAINER_XML.encode("utf-8"))
            zf.writestr("OPS/package.opf", PACKAGE_OPF.encode("utf-8"))
            zf.writestr("OPS/titlepage.xhtml", TITLEPAGE_XHTML.encode("utf-8"))
            zf.writestr("OPS/s00000-beta.xhtml", CHAPTER_XHTML.encode("utf-8"))
        images_dir = zip_path.parent / (zip_path.stem + "_images")
        doc = EpubExtractor().extract(zip_path, images_dir=images_dir)
        assert doc.metadata.title == "Fallback Test"
        texts = [n.text for n in doc.flat_list() if isinstance(n, ContentNode)]
        assert "Cover" in texts and "Chapter One" in texts and "First paragraph." in texts
        print("zip fallback: OK")
    finally:
        zip_path.unlink(missing_ok=True)


if __name__ == "__main__":
    test_directory()
    test_zip()
    print("All fallback checks passed.")
