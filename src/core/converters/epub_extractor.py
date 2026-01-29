"""
Extract Document from EPUB using ebooklib: metadata, spine-ordered content, HTML parsing.
All code and comments in English.
"""

from __future__ import annotations

import html.parser
from pathlib import Path
from typing import Any

from core.converters.base import BaseExtractor
from core.models.book_metadata import BookMetadata
from core.models.document import ContentNode, Document

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
    """Collect (level, text) for h1/h2/h3/p tags. level: 1=h1, 2=h2, 3=h3, 0=paragraph."""

    BLOCK_TAGS = {"h1", "h2", "h3", "p", "div", "section"}

    def __init__(self) -> None:
        super().__init__()
        self._blocks: list[tuple[int, str]] = []
        self._current_level: int | None = None
        self._current_text: list[str] = []

    @property
    def blocks(self) -> list[tuple[int, str]]:
        return self._blocks

    def _flush(self) -> None:
        if self._current_level is not None and self._current_text:
            text = " ".join(" ".join(self._current_text).split())
            if text:
                self._blocks.append((self._current_level, text))
        self._current_level = None
        self._current_text = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
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


def _html_to_nodes(html_bytes: bytes) -> list[ContentNode]:
    """Parse HTML body and return flat list of ContentNode (h1/h2/h3/p → level, text)."""
    try:
        html_str = html_bytes.decode("utf-8", errors="replace")
    except Exception:
        return []
    parser = _HtmlContentParser()
    try:
        parser.feed(html_str)
    except Exception:
        return []
    blocks = parser.blocks
    nodes: list[ContentNode] = []
    ch_count = 0
    p_count = 0
    for level, text in blocks:
        text_clean = text.strip()
        if not text_clean:
            continue
        if level >= 1:
            nodes.append(ContentNode(id=f"ch_{ch_count}", text=text_clean, level=level))
            ch_count += 1
        else:
            nodes.append(ContentNode(id=f"p_{p_count}", text=text_clean, level=0))
            p_count += 1
    return nodes


def _extract_nodes_from_epub(book: Any) -> list[ContentNode]:
    """Yield ContentNodes in spine order from EPUB document items."""
    if ebooklib is None or epub is None:
        return []
    all_nodes: list[ContentNode] = []
    # spine is list of (item_id, linear) e.g. [('nav', 'yes'), ('chapter_0', 'yes')]
    spine = getattr(book, "spine", None) or []
    seen_ids: set[str] = set()
    p_global = 0
    ch_global = 0
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
        nodes = _html_to_nodes(raw)
        for n in nodes:
            # Ensure globally unique ids when merging from multiple chapters
            if n.level >= 1:
                new_id = f"ch_{ch_global}"
                ch_global += 1
            else:
                new_id = f"p_{p_global}"
                p_global += 1
            all_nodes.append(ContentNode(id=new_id, text=n.text, level=n.level))
    return all_nodes


class EpubExtractor(BaseExtractor):
    """Extract a Document from an EPUB file using ebooklib and spine-ordered HTML parsing."""

    def extract(self, path: Path | str) -> Document:
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
        root_nodes = _extract_nodes_from_epub(book)
        return Document(metadata=metadata, root_nodes=root_nodes)
