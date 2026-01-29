"""
Build EPUB from Document using ebooklib: metadata, toc, xhtml chapters, basic styles.
All code and comments in English.
"""

from __future__ import annotations

import html
import uuid
from pathlib import Path

from core.converters.base import BaseBuilder
from core.models.document import ContentNode, Document

try:
    from ebooklib import epub
except ImportError:
    epub = None  # type: ignore[assignment]


def _escape(text: str) -> str:
    """Escape text for HTML content."""
    return html.escape(text, quote=True)


def _document_to_chapters(document: Document) -> list[list[ContentNode]]:
    """
    Group document flat list into chapters: each chapter is a list of nodes
    (first node is heading level 1+, rest are paragraphs until next heading).
    """
    flat = document.flat_list()
    if not flat:
        return []
    chapters: list[list[ContentNode]] = []
    current: list[ContentNode] = []
    for node in flat:
        if node.level >= 1 and current:
            chapters.append(current)
            current = []
        current.append(node)
    if current:
        chapters.append(current)
    return chapters


def _nodes_to_xhtml_body(nodes: list[ContentNode]) -> str:
    """Render a list of content nodes as XHTML body fragments (h1/h2/h3/p)."""
    parts: list[str] = []
    for node in nodes:
        text = _escape(node.text.strip())
        if not text:
            continue
        if node.level == 1:
            parts.append(f"<h1>{text}</h1>")
        elif node.level == 2:
            parts.append(f"<h2>{text}</h2>")
        elif node.level == 3:
            parts.append(f"<h3>{text}</h3>")
        else:
            parts.append(f"<p>{text}</p>")
    return "\n".join(parts) if parts else "<p></p>"


def _build_epub(document: Document, path: Path) -> None:
    """Create EpubBook from Document and write to path. Requires ebooklib."""
    if epub is None:
        raise RuntimeError("ebooklib is not installed; install with: pip install ebooklib")

    meta = document.metadata
    book = epub.EpubBook()

    # Identifier: use first from metadata or generate
    identifier = None
    if meta.identifiers:
        for k, v in meta.identifiers.items():
            if v:
                identifier = v
                break
    if not identifier:
        identifier = f"urn:uuid:{uuid.uuid4().hex}"
    book.set_identifier(identifier)
    book.set_title(meta.title)
    book.set_language(meta.language)
    for author in meta.authors:
        book.add_author(author)
    if meta.publisher:
        book.add_metadata("DC", "publisher", meta.publisher)

    # Default CSS (optional)
    nav_css = epub.EpubItem(
        uid="style_main",
        file_name="style/main.css",
        media_type="text/css",
        content="body { font-family: serif; }\np { margin: 1em 0; }\nh1, h2, h3 { margin: 1em 0 0.5em; }\n".encode("utf-8"),
    )
    book.add_item(nav_css)

    chapters_list = _document_to_chapters(document)
    spine_items: list[epub.EpubHtml] = []
    toc_entries: list[epub.EpubHtml] = []

    for i, nodes in enumerate(chapters_list):
        if not nodes:
            continue
        file_name = f"chap_{i + 1:03d}.xhtml"
        title = nodes[0].text.strip() if nodes else f"Chapter {i + 1}"
        body_html = _nodes_to_xhtml_body(nodes)
        chapter = epub.EpubHtml(title=title, file_name=file_name, lang=meta.language)
        chapter.set_content(body_html)
        chapter.add_item(nav_css)
        book.add_item(chapter)
        spine_items.append(chapter)
        toc_entries.append(chapter)

    # At least one content document required for valid EPUB
    if not spine_items:
        chapter = epub.EpubHtml(title="Content", file_name="chap_001.xhtml", lang=meta.language)
        chapter.set_content("<p></p>")
        chapter.add_item(nav_css)
        book.add_item(chapter)
        spine_items.append(chapter)
        toc_entries.append(chapter)

    book.toc = tuple(toc_entries)
    book.spine = ["nav"] + spine_items
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    opts = {"raise_exceptions": True}
    epub.write_epub(str(path), book, opts)


class EpubBuilder(BaseBuilder):
    """Build an EPUB file from a Document (metadata, toc, xhtml chapters, styles)."""

    def build(self, document: Document, path: Path | str) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        _build_epub(document, path)
