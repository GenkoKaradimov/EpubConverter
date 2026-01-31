"""
PDF to Document extractor: uses pdf_service and heuristics to build Document + BookMetadata.
All code and comments in English. Supports images when images_dir is provided.
"""

from __future__ import annotations

from pathlib import Path

from core.models.book_metadata import BookMetadata
from core.models.document import ContentItem, ContentNode, Document, ImageNode
from core.converters.base import BaseExtractor
from services.pdf_service import (
    BlockData,
    ImageData,
    PageItem,
    extract_pages,
    extract_pages_with_images,
)

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


def _items_to_root_nodes_and_images(
    all_items: list[PageItem],
    heading_ratio: float = 1.2,
) -> tuple[list[ContentItem], dict[str, Path]]:
    """
    Convert flat list of BlockData and ImageData to root_nodes and images dict.
    Preserves order. Heading heuristic applied to text blocks only.
    """
    if not all_items:
        return [], {}
    blocks_only = [b for b in all_items if isinstance(b, BlockData)]
    sizes = [b.font_size for b in blocks_only if b.font_size is not None]
    threshold = _median(sizes) * heading_ratio if sizes else None

    root_nodes: list[ContentItem] = []
    images: dict[str, Path] = {}
    ch_count = 0
    p_count = 0
    img_count = 0
    for item in all_items:
        if isinstance(item, BlockData):
            text = item.text.strip()
            if not text:
                continue
            if threshold is not None and item.font_size is not None and item.font_size > threshold:
                root_nodes.append(ContentNode(id=f"ch_{ch_count}", text=text, level=1))
                ch_count += 1
            else:
                root_nodes.append(ContentNode(id=f"p_{p_count}", text=text, level=0))
                p_count += 1
        elif isinstance(item, ImageData):
            node_id = f"img_node_{img_count}"
            img_count += 1
            root_nodes.append(ImageNode(id=node_id, image_id=item.image_id, alt=None))
            images[item.image_id] = item.path
    return root_nodes, images


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

    def extract(self, path: Path | str, images_dir: Path | str | None = None) -> Document:
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"PDF not found: {path}")
        metadata = _pdf_metadata_to_book_metadata(path)
        if images_dir is not None:
            images_dir = Path(images_dir)
            pages = extract_pages_with_images(path, images_dir)
            all_items: list[PageItem] = []
            for page_items in pages:
                all_items.extend(page_items)
            root_nodes, images = _items_to_root_nodes_and_images(
                all_items, heading_ratio=self.heading_ratio
            )
            return Document(metadata=metadata, root_nodes=root_nodes, images=images)
        pages = extract_pages(path)
        all_blocks: list[BlockData] = []
        for page_blocks in pages:
            all_blocks.extend(page_blocks)
        root_nodes = _blocks_to_nodes(all_blocks, heading_ratio=self.heading_ratio)
        return Document(metadata=metadata, root_nodes=root_nodes)
