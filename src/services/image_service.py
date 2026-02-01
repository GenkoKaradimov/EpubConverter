"""
Image load, transform (rotate, crop), and encode for display/EPUB build.
Uses Pillow. All code and comments in English.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

try:
    from PIL import Image
except ImportError:
    Image = None  # type: ignore[assignment, misc]

if TYPE_CHECKING:
    from PIL.Image import Image as PilImage


def load_image(path: Path | str) -> "PilImage":
    """
    Load image from path using Pillow. Returns PIL Image (RGB or RGBA).
    Raises RuntimeError if Pillow not installed; OSError on read failure.
    """
    if Image is None:
        raise RuntimeError("Pillow is not installed; install with: pip install Pillow")
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {path}")
    img = Image.open(path).convert("RGBA")
    return img


def apply_transform(
    image: "PilImage",
    rotation_degrees: float = 0.0,
    crop_rect: tuple[float, float, float, float] | None = None,
) -> "PilImage":
    """
    Apply rotation then crop. Rotation uses expand=True so nothing is clipped.
    crop_rect is (left, top, right, bottom) normalized 0-1; applied in pixel coords.
    Returns new PIL Image; does not modify input.
    """
    if Image is None:
        raise RuntimeError("Pillow is not installed; install with: pip install Pillow")
    out = image
    if rotation_degrees != 0:
        resample = getattr(Image, "Resampling", Image).BICUBIC if hasattr(Image, "Resampling") else Image.BICUBIC
        out = out.rotate(-rotation_degrees, expand=True, resample=resample)
    if crop_rect is not None:
        w, h = out.size
        left = int(crop_rect[0] * w)
        top = int(crop_rect[1] * h)
        right = int(crop_rect[2] * w)
        bottom = int(crop_rect[3] * h)
        left = max(0, min(left, w - 1))
        top = max(0, min(top, h - 1))
        right = max(left + 1, min(right, w))
        bottom = max(top + 1, min(bottom, h))
        out = out.crop((left, top, right, bottom))
    return out


def image_to_bytes(image: "PilImage", format: str = "PNG") -> bytes:
    """
    Encode PIL Image to bytes for the given format (e.g. 'PNG', 'JPEG').
    For JPEG, convert to RGB first if image has alpha.
    """
    if Image is None:
        raise RuntimeError("Pillow is not installed; install with: pip install Pillow")
    import io
    buf = io.BytesIO()
    if format.upper() == "JPEG" and image.mode in ("RGBA", "P"):
        image = image.convert("RGB")
    image.save(buf, format=format)
    return buf.getvalue()
