"""
Build EPUB from Document using ebooklib: metadata, toc, xhtml chapters, basic styles.
All code and comments in English. Supports ImageNode; images read from disk at build time.
"""

from __future__ import annotations

import html
import uuid
from pathlib import Path

from core.converters.base import BaseBuilder
from core.models.document import ContentItem, ContentNode, Document, ImageNode

try:
    from ebooklib import epub
except ImportError:
    epub = None  # type: ignore[assignment]


def _escape(text: str) -> str:
    """Escape text for HTML content."""
    return html.escape(text, quote=True)


def _document_to_chapters(document: Document) -> list[list[ContentItem]]:
    """
    Group document flat list into chapters: each chapter is a list of nodes
    (text and/or image). New chapter starts at ContentNode with level >= 1; ImageNodes stay in current chapter.
    """
    flat = document.flat_list()
    if not flat:
        return []
    chapters: list[list[ContentItem]] = []
    current: list[ContentItem] = []
    for node in flat:
        if isinstance(node, ContentNode) and node.level >= 1 and current:
            chapters.append(current)
            current = []
        current.append(node)
    if current:
        chapters.append(current)
    return chapters


def _chapter_title(nodes: list[ContentItem], fallback: str) -> str:
    """First heading text in chapter, or fallback (e.g. 'Chapter N')."""
    for node in nodes:
        if isinstance(node, ContentNode) and node.level >= 1 and node.text.strip():
            return node.text.strip()
    return fallback


def _image_ext(path: Path) -> str:
    """Return extension including dot, or .png."""
    s = path.suffix.lower()
    return s if s in (".png", ".jpg", ".jpeg", ".gif", ".webp") else ".png"


def _safe_image_id(node_id: str) -> str:
    """Sanitize node id for use in EPUB file name."""
    return "".join(c if c.isalnum() or c in "_-" else "_" for c in node_id)


def _nodes_to_xhtml_body(
    nodes: list[ContentItem],
    image_hrefs: dict[str, str],
) -> str:
    """Render content and image nodes as XHTML body fragments (h1/h2/h3/p, img)."""
    parts: list[str] = []
    for node in nodes:
        if isinstance(node, ContentNode):
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
        elif isinstance(node, ImageNode):
            href = image_hrefs.get(node.id)
            if not href:
                continue
            alt_attr = f' alt="{_escape(node.alt or "")}"' if node.alt else ""
            parts.append(f'<figure><img src="{_escape(href)}"{alt_attr} /></figure>')
    return "\n".join(parts) if parts else "<p></p>"


def _build_epub(document: Document, path: Path) -> None:
    """Create EpubBook from Document and write to path. Requires ebooklib. Images read from disk."""
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
        content="body { font-family: serif; }\np { margin: 1em 0; }\nh1, h2, h3 { margin: 1em 0 0.5em; }\nfigure { margin: 1em 0; }\n".encode("utf-8"),
    )
    book.add_item(nav_css)

    # Add image items: one per ImageNode (so each can have its own rotate/crop)
    image_hrefs: dict[str, str] = {}
    try:
        from services.image_service import apply_transform, image_to_bytes, load_image
    except ImportError:
        load_image = None  # type: ignore[assignment, misc]
        apply_transform = None  # type: ignore[assignment, misc]
        image_to_bytes = None  # type: ignore[assignment, misc]
    for node in document.flat_list():
        if not isinstance(node, ImageNode):
            continue
        file_path = document.images.get(node.image_id)
        if not file_path or not file_path.exists():
            continue
        ext = _image_ext(file_path)
        safe_id = _safe_image_id(node.id)
        epub_file_name = f"images/{safe_id}{ext}"
        has_transform = node.rotation_degrees != 0 or node.crop_rect is not None
        try:
            if has_transform and load_image is not None and apply_transform is not None and image_to_bytes is not None:
                img = load_image(file_path)
                img = apply_transform(img, node.rotation_degrees, node.crop_rect)
                fmt = "PNG" if ext == ".png" else "JPEG" if ext in (".jpg", ".jpeg") else "GIF" if ext == ".gif" else "WEBP" if ext == ".webp" else "PNG"
                content = image_to_bytes(img, fmt)
            else:
                content = file_path.read_bytes()
        except (OSError, RuntimeError, FileNotFoundError):
            continue
        mt = "image/png" if ext == ".png" else "image/jpeg" if ext in (".jpg", ".jpeg") else "image/gif" if ext == ".gif" else "image/webp" if ext == ".webp" else "image/png"
        img_item = epub.EpubImage(
            uid=f"img_{safe_id}",
            file_name=epub_file_name,
            content=content,
            media_type=mt,
        )
        book.add_item(img_item)
        image_hrefs[node.id] = epub_file_name

    chapters_list = _document_to_chapters(document)
    spine_items: list[epub.EpubHtml] = []
    toc_entries: list[epub.EpubHtml] = []

    for i, nodes in enumerate(chapters_list):
        if not nodes:
            continue
        file_name = f"chap_{i + 1:03d}.xhtml"
        title = _chapter_title(nodes, f"Chapter {i + 1}")
        body_html = _nodes_to_xhtml_body(nodes, image_hrefs)
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
