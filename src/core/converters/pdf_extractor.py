"""
PDF to Document extractor: uses pdf_service and heuristics to build Document + BookMetadata.
All code and comments in English.
"""

from __future__ import annotations

from pathlib import Path

from core.models.book_metadata import BookMetadata
from core.models.document import ContentNode, Document
from core.converters.base import BaseExtractor
from services.pdf_service import BlockData, extract_pages

try:
    from app.config import DEFAULT_LANGUAGE
except ImportError:
    DEFAULT_LANGUAGE = "en"


def _median(values: list[float]) -> float:
    """Return median of non-empty list of floats."""
    if not values:
        return 0.0
    s = sorted(values)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2.0


def _blocks_to_nodes(
    all_blocks: list[BlockData],
    heading_ratio: float = 1.2,
) -> list[ContentNode]:
    """
    Convert flat list of BlockData to ContentNodes.
    Heuristic: blocks with font_size > median * heading_ratio become level 1 (chapter);
    others level 0 (paragraph). If no font sizes, all level 0.
    """
    if not all_blocks:
        return []
    sizes = [b.font_size for b in all_blocks if b.font_size is not None]
    threshold = _median(sizes) * heading_ratio if sizes else None
    nodes: list[ContentNode] = []
    ch_count = 0
    p_count = 0
    for block in all_blocks:
        text = block.text.strip()
        if not text:
            continue
        if threshold is not None and block.font_size is not None and block.font_size > threshold:
            nodes.append(ContentNode(id=f"ch_{ch_count}", text=text, level=1))
            ch_count += 1
        else:
            nodes.append(ContentNode(id=f"p_{p_count}", text=text, level=0))
            p_count += 1
    return nodes


def _pdf_metadata_to_book_metadata(path: Path) -> BookMetadata:
    """Build BookMetadata from PDF document metadata where available."""
    try:
        import fitz
        doc = fitz.open(path)
        try:
            meta = doc.metadata or {}
        finally:
            doc.close()
    except Exception:
        meta = {}
    title = (meta.get("title") or "").strip() or "Untitled"
    author = (meta.get("author") or "").strip()
    authors = [author] if author else []
    language = (meta.get("language") or "").strip() or DEFAULT_LANGUAGE
    return BookMetadata(title=title, language=language, authors=authors or None)


class PdfExtractor(BaseExtractor):
    """Extract a Document from a PDF file using pdf_service and heading heuristics."""

    def __init__(self, heading_ratio: float = 1.2) -> None:
        """
        heading_ratio: block font_size > median * heading_ratio is treated as heading (level 1).
        """
        self.heading_ratio = heading_ratio

    def extract(self, path: Path | str) -> Document:
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"PDF not found: {path}")
        pages = extract_pages(path)
        all_blocks: list[BlockData] = []
        for page_blocks in pages:
            all_blocks.extend(page_blocks)
        metadata = _pdf_metadata_to_book_metadata(path)
        root_nodes = _blocks_to_nodes(all_blocks, heading_ratio=self.heading_ratio)
        return Document(metadata=metadata, root_nodes=root_nodes)
