"""
Extract Document from EPUB using ebooklib: metadata, spine-ordered content, HTML parsing.
All code and comments in English. Supports images when images_dir is provided.
"""

from __future__ import annotations

import html.parser
import posixpath
from pathlib import Path
from typing import Any
from urllib.parse import unquote

from core.converters.base import BaseExtractor
from core.models.book_metadata import BookMetadata
from core.models.document import ContentItem, ContentNode, Document, ImageNode

try:
    import ebooklib
    from ebooklib import epub
except ImportError:
    ebooklib = None  # type: ignore[assignment]
    epub = None  # type: ignore[assignment]

try:
    from app.config import DEFAULT_LANGUAGE
except ImportError:
    DEFAULT_LANGUAGE = "en"

# Parsed block: (level, text) for text, or ("img", href, alt) for image
_HtmlBlock = tuple[int, str] | tuple[str, str, str | None]


def _first_metadata(book: Any, namespace: str, key: str) -> str | None:
    """Return first metadata value for (namespace, key) or None."""
    if epub is None:
        return None
    values = book.get_metadata(namespace, key)
    if not values or not isinstance(values, list):
        return None
    for v in values:
        if isinstance(v, (list, tuple)) and len(v) >= 1 and v[0]:
            return str(v[0]).strip()
        if isinstance(v, str) and v.strip():
            return v.strip()
    return None


def _epub_metadata_to_book_metadata(book: Any) -> BookMetadata:
    """Build BookMetadata from EPUB Dublin Core and other metadata."""
    title = _first_metadata(book, "DC", "title") or "Untitled"
    language = _first_metadata(book, "DC", "language") or DEFAULT_LANGUAGE
    authors: list[str] = []
    creators = book.get_metadata("DC", "creator")
    if isinstance(creators, list):
        for c in creators:
            if isinstance(c, (list, tuple)) and len(c) >= 1 and c[0]:
                authors.append(str(c[0]).strip())
            elif isinstance(c, str) and c.strip():
                authors.append(c.strip())
    publisher = _first_metadata(book, "DC", "publisher")
    identifiers: dict[str, str] = {}
    idents = book.get_metadata("DC", "identifier")
    if isinstance(idents, list):
        for i in idents:
            if isinstance(i, (list, tuple)) and len(i) >= 1 and i[0]:
                val = str(i[0]).strip()
                # optional: use id from attrs if present
                attrs = i[1] if len(i) > 1 and isinstance(i[1], dict) else {}
                key = attrs.get("id", "identifier")
                identifiers[key] = val
            elif isinstance(i, str) and i.strip():
                identifiers["identifier"] = i.strip()
    return BookMetadata(
        title=title,
        language=language,
        authors=authors or None,
        publisher=publisher,
        identifiers=identifiers or None,
    )


class _HtmlContentParser(html.parser.HTMLParser):
    """Collect (level, text) for h1/h2/h3/p and ("img", src, alt) for img tags."""

    BLOCK_TAGS = {"h1", "h2", "h3", "p", "div", "section"}

    def __init__(self) -> None:
        super().__init__()
        self._blocks: list[_HtmlBlock] = []
        self._current_level: int | None = None
        self._current_text: list[str] = []

    @property
    def blocks(self) -> list[_HtmlBlock]:
        return self._blocks

    def _flush(self) -> None:
        if self._current_level is not None and self._current_text:
            text = " ".join(" ".join(self._current_text).split())
            if text:
                self._blocks.append((self._current_level, text))
        self._current_level = None
        self._current_text = []

    def _attr_dict(self, attrs: list[tuple[str, str | None]]) -> dict[str, str]:
        return {k.lower(): (v or "").strip() for k, v in attrs if v is not None}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag == "img":
            self._flush()
            ad = self._attr_dict(attrs)
            src = ad.get("src", "").strip()
            alt = ad.get("alt", "").strip() or None
            if src:
                self._blocks.append(("img", src, alt))
            return
        if tag == "h1":
            self._flush()
            self._current_level = 1
            self._current_text = []
        elif tag == "h2":
            self._flush()
            self._current_level = 2
            self._current_text = []
        elif tag == "h3":
            self._flush()
            self._current_level = 3
            self._current_text = []
        elif tag == "p":
            self._flush()
            self._current_level = 0
            self._current_text = []
        elif tag in ("div", "section") and self._current_level is None:
            self._current_level = 0
            self._current_text = []

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in self.BLOCK_TAGS:
            self._flush()

    def handle_data(self, data: str) -> None:
        if self._current_level is not None and data:
            self._current_text.append(data)


def _html_to_blocks(html_bytes: bytes) -> list[_HtmlBlock]:
    """Parse HTML body and return flat list of (level, text) or ('img', href, alt)."""
    try:
        html_str = html_bytes.decode("utf-8", errors="replace")
    except Exception:
        return []
    parser = _HtmlContentParser()
    try:
        parser.feed(html_str)
    except Exception:
        return []
    return parser.blocks


def _build_href_to_image_item(book: Any) -> dict[str, Any]:
    """Build map from normalized href / basename to image item for resolving img src."""
    if ebooklib is None:
        return {}
    href_to_item: dict[str, Any] = {}
    for item in book.get_items():
        if item.get_type() != ebooklib.ITEM_IMAGE:
            continue
        name = getattr(item, "file_name", None) or getattr(item, "fileName", "")
        if not name:
            continue
        name = name.replace("\\", "/")
        norm = posixpath.normpath(name)
        href_to_item[norm] = item
        base = posixpath.basename(norm)
        if base not in href_to_item:
            href_to_item[base] = item
    return href_to_item


def _extract_nodes_from_epub(
    book: Any,
    images_dir: Path | None,
) -> tuple[list[ContentItem], dict[str, Path]]:
    """Extract ContentNodes and ImageNodes in spine order; write images to images_dir if provided."""
    if ebooklib is None or epub is None:
        return [], {}
    all_nodes: list[ContentItem] = []
    images: dict[str, Path] = {}
    p_global = 0
    ch_global = 0
    img_global = 0
    href_to_item = _build_href_to_image_item(book) if images_dir is not None else {}
    if images_dir is not None:
        images_dir.mkdir(parents=True, exist_ok=True)

    spine = getattr(book, "spine", None) or []
    for entry in spine:
        item_id = entry[0] if isinstance(entry, (list, tuple)) else entry
        if isinstance(item_id, tuple):
            item_id = item_id[0] if item_id else ""
        item_id = str(item_id).strip()
        if not item_id or item_id.lower() == "nav":
            continue
        item = book.get_item_with_id(item_id)
        if item is None:
            continue
        if item.get_type() != ebooklib.ITEM_DOCUMENT:
            continue
        try:
            raw = item.get_content()
        except Exception:
            continue
        if not raw:
            continue
        doc_base = ""
        fn = getattr(item, "file_name", None) or getattr(item, "fileName", "")
        if fn:
            doc_base = posixpath.dirname(fn.replace("\\", "/"))
        blocks = _html_to_blocks(raw)
        for blk in blocks:
            if isinstance(blk[0], int):
                level, text = blk[0], blk[1]
                text_clean = text.strip()
                if not text_clean:
                    continue
                if level >= 1:
                    all_nodes.append(
                        ContentNode(id=f"ch_{ch_global}", text=text_clean, level=level)
                    )
                    ch_global += 1
                else:
                    all_nodes.append(
                        ContentNode(id=f"p_{p_global}", text=text_clean, level=0)
                    )
                    p_global += 1
            elif blk[0] == "img":
                _, href, alt = blk[0], blk[1], blk[2]
                if not href:
                    continue
                resolved = posixpath.normpath(
                    posixpath.join(doc_base, unquote(href).replace("\\", "/"))
                )
                img_item = href_to_item.get(resolved) or href_to_item.get(
                    posixpath.basename(resolved)
                )
                if img_item is None and images_dir is not None:
                    continue
                if img_item is not None and images_dir is not None:
                    try:
                        content = img_item.get_content()
                    except Exception:
                        content = None
                    if content and isinstance(content, bytes):
                        image_id = f"img_{img_global}"
                        img_global += 1
                        ext = _guess_image_ext(content)
                        file_path = images_dir / f"{image_id}{ext}"
                        file_path.write_bytes(content)
                        images[image_id] = file_path
                        node_id = f"img_node_{img_global - 1}"
                        all_nodes.append(ImageNode(id=node_id, image_id=image_id, alt=alt))
    return all_nodes, images


def _guess_image_ext(data: bytes) -> str:
    """Return file extension from image magic bytes."""
    if data.startswith(b"\x89PNG"):
        return ".png"
    if data.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if data.startswith(b"GIF87a") or data.startswith(b"GIF89a"):
        return ".gif"
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return ".webp"
    return ".png"


class EpubExtractor(BaseExtractor):
    """Extract a Document from an EPUB file using ebooklib and spine-ordered HTML parsing."""

    def extract(self, path: Path | str, images_dir: Path | str | None = None) -> Document:
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"EPUB not found: {path}")
        if epub is None:
            raise RuntimeError("ebooklib is not installed; install with: pip install ebooklib")
        try:
            book = epub.read_epub(str(path))
        except FileNotFoundError:
            raise
        except Exception as e:
            raise RuntimeError(f"Failed to read EPUB: {e}") from e
        metadata = _epub_metadata_to_book_metadata(book)
        idir = Path(images_dir) if images_dir is not None else None
        root_nodes, images = _extract_nodes_from_epub(book, idir)
        return Document(metadata=metadata, root_nodes=root_nodes, images=images)
