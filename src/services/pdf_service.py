"""
Wrapper around PyMuPDF for opening PDFs and extracting text/structure per page.
Returns an internal format: list of pages, each page = list of blocks (text + optional font_size).
With images: list of pages, each page = list of BlockData and ImageData in document order.
All code and comments in English.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Union

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None  # type: ignore[assignment]


@dataclass(frozen=True)
class BlockData:
    """Single block of text with optional font size (for heading heuristics)."""

    text: str
    font_size: float | None = None


@dataclass(frozen=True)
class ImageData:
    """Reference to an image written to disk: image_id (key) and path to file."""

    image_id: str
    path: Path


PageItem = Union[BlockData, ImageData]


def extract_pages(path: Path | str) -> list[list[BlockData]]:
    """
    Open the PDF at path and extract blocks per page.
    Each page is a list of BlockData (text, font_size). Order is preserved.
    Raises FileNotFoundError if path does not exist, or fitz-related errors for invalid PDFs.
    """
    if fitz is None:
        raise RuntimeError("PyMuPDF is not installed; install with: pip install pymupdf")
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {path}")
    if not path.is_file():
        raise ValueError(f"Not a file: {path}")

    result: list[list[BlockData]] = []
    doc = fitz.open(path)
    try:
        for page_no in range(len(doc)):
            page = doc[page_no]
            blocks = _page_to_blocks(page)
            result.append(blocks)
    finally:
        doc.close()
    return result


def _page_to_blocks(page: "fitz.Page") -> list[BlockData]:
    """Convert one PyMuPDF page to a list of BlockData (text, font_size)."""
    out: list[BlockData] = []
    raw = page.get_text("dict")
    for block in raw.get("blocks", []):
        lines = block.get("lines", [])
        block_text_parts: list[str] = []
        block_sizes: list[float] = []
        for line in lines:
            line_text_parts: list[str] = []
            for span in line.get("spans", []):
                text = span.get("text", "")
                if text:
                    line_text_parts.append(text)
                size = span.get("size")
                if size is not None:
                    block_sizes.append(float(size))
            if line_text_parts:
                block_text_parts.append(" ".join(line_text_parts))
        text = "\n".join(block_text_parts).strip()
        if text:
            font_size = max(block_sizes) if block_sizes else None
            out.append(BlockData(text=text, font_size=font_size))
    return out


def extract_pages_with_images(
    path: Path | str,
    images_dir: Path,
) -> list[list[PageItem]]:
    """
    Open the PDF at path and extract text blocks and images per page in document order.
    Each page is a list of BlockData and ImageData. Images are written to images_dir.
    Returns list of pages; each page is list[BlockData | ImageData].
    """
    if fitz is None:
        raise RuntimeError("PyMuPDF is not installed; install with: pip install pymupdf")
    path = Path(path)
    images_dir = Path(images_dir)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {path}")
    if not path.is_file():
        raise ValueError(f"Not a file: {path}")
    images_dir.mkdir(parents=True, exist_ok=True)

    result: list[list[PageItem]] = []
    image_counter: list[int] = [0]
    doc = fitz.open(path)
    try:
        for page_no in range(len(doc)):
            page = doc[page_no]
            items = _page_to_items(page, images_dir, image_counter)
            result.append(items)
    finally:
        doc.close()
    return result


def _page_to_items(
    page: "fitz.Page",
    images_dir: Path,
    image_counter: list[int],
) -> list[PageItem]:
    """Convert one PyMuPDF page to a list of BlockData and ImageData in document order."""
    out: list[PageItem] = []
    raw = page.get_text("dict")
    for block in raw.get("blocks", []):
        btype = block.get("type", 0)
        if btype == 0:
            # Text block
            lines = block.get("lines", [])
            block_text_parts: list[str] = []
            block_sizes: list[float] = []
            for line in lines:
                line_text_parts: list[str] = []
                for span in line.get("spans", []):
                    text = span.get("text", "")
                    if text:
                        line_text_parts.append(text)
                    size = span.get("size")
                    if size is not None:
                        block_sizes.append(float(size))
                if line_text_parts:
                    block_text_parts.append(" ".join(line_text_parts))
            text = "\n".join(block_text_parts).strip()
            if text:
                font_size = max(block_sizes) if block_sizes else None
                out.append(BlockData(text=text, font_size=font_size))
        elif btype == 1:
            # Image block: 'image' bytes, 'ext' extension
            image_bytes = block.get("image")
            ext = (block.get("ext") or "png").strip().lower()
            if not ext.startswith("."):
                ext = "." + ext
            if image_bytes and isinstance(image_bytes, bytes):
                n = image_counter[0]
                image_counter[0] += 1
                image_id = f"img_{n}"
                safe_ext = ext if ext in (".png", ".jpg", ".jpeg", ".gif", ".webp") else ".png"
                file_path = images_dir / f"{image_id}{safe_ext}"
                file_path.write_bytes(image_bytes)
                out.append(ImageData(image_id=image_id, path=file_path))
    return out
