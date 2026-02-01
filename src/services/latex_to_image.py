"""
Render paragraphs that are entirely LaTeX formulas to PNG images using matplotlib.mathtext.
Used by LaTeX dialog: convert_formula_paragraphs_to_images. No system LaTeX required.
"""

from __future__ import annotations

import re
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from core.models.document import Document

try:
    from matplotlib.mathtext import math_to_image

    MATHTEXT_AVAILABLE = True
except ImportError:
    math_to_image = None  # type: ignore[assignment, misc]
    MATHTEXT_AVAILABLE = False


def _normalize_formula_for_mathtext(formula_text: str) -> str:
    """
    Replace LaTeX aliases that mathtext does not recognize with their canonical form.
    E.g. \\ge -> \\geq, \\le -> \\leq; \\rm -> \\mathrm (mathtext supports \\mathrm but not \\rm).
    """
    text = re.sub(r"\\ge(?!q)", r"\\geq", formula_text)
    text = re.sub(r"\\le(?!q)", r"\\leq", text)
    # \rm is a font switch; mathtext expects \mathrm{...}. \rm n -> \mathrm{n}, \rm{np} -> \mathrm{np}
    text = re.sub(r"\\rm\s*\{([^}]*)\}", r"\\mathrm{\1}", text)
    text = re.sub(r"\\rm\s*(\w)", r"\\mathrm{\1}", text)
    return text


def _next_image_id(document: "Document") -> str:
    """Return a unique image_id for document.images (img_N)."""
    max_n = -1
    for key in document.images:
        if key.startswith("img_"):
            try:
                n = int(key[4:])
                max_n = max(max_n, n)
            except ValueError:
                pass
    return f"img_{max_n + 1}"


def render_formula_to_image(
    formula_text: str,
    output_path: Path,
    dpi: int = 150,
    fmt: str = "png",
) -> tuple[bool, str | None]:
    """
    Render a LaTeX math expression to an image file using matplotlib.mathtext.
    formula_text must contain the expression with dollar signs (e.g. "$\\alpha$" or "$$\\frac{1}{2}$$").
    Returns (True, None) on success, (False, error_message) if unavailable or rendering fails.
    """
    if not MATHTEXT_AVAILABLE or math_to_image is None:
        return False, "matplotlib is not available"
    formula_text = formula_text.strip()
    if not formula_text:
        return False, "empty formula"
    formula_text = _normalize_formula_for_mathtext(formula_text)
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        math_to_image(formula_text, str(output_path), format=fmt, dpi=dpi)
        return True, None
    except Exception as e:
        return False, str(e)


def convert_formula_paragraphs_to_images(
    document: "Document",
    *,
    progress_callback: Callable[[int, int], None] | None = None,
    images_dir: Path | None = None,
    dpi: int = 150,
) -> tuple[int, int, list[str]]:
    """
    Replace each root-level paragraph that is entirely a LaTeX formula with an ImageNode
    pointing to a rendered PNG. Modifies document.root_nodes and document.images in place.
    Returns (converted_count, failed_count, list of error messages).
    """
    from core.models.document import ContentNode, ImageNode

    from services.latex_merge import _is_entirely_formula

    if not MATHTEXT_AVAILABLE:
        return 0, 0, []

    if images_dir is None:
        images_dir = Path(tempfile.gettempdir()) / "EpubConverter" / "formulas"
    images_dir = Path(images_dir)
    images_dir.mkdir(parents=True, exist_ok=True)

    root = document.root_nodes
    new_list: list = []
    total = len(root)
    converted = 0
    failed = 0
    errors: list[str] = []

    for idx, node in enumerate(root):
        if progress_callback:
            progress_callback(idx + 1, total)
        if not isinstance(node, ContentNode) or node.level != 0:
            new_list.append(node)
            continue
        if not _is_entirely_formula(node.text):
            new_list.append(node)
            continue

        image_id = _next_image_id(document)
        out_path = images_dir / f"{image_id}.png"
        ok, err_msg = render_formula_to_image(node.text, out_path, dpi=dpi, fmt="png")
        if ok:
            document.images[image_id] = out_path
            alt = node.text.strip()
            if len(alt) > 80:
                alt = alt[:77] + "..."
            new_list.append(
                ImageNode(id=f"img_node_{image_id}", image_id=image_id, alt=alt or None)
            )
            converted += 1
        else:
            new_list.append(node)
            failed += 1
            formula = node.text.strip()
            errors.append(f"Node: {node.id}\nFormula: {formula}\nError: {err_msg or 'unknown error'}")

    root.clear()
    root.extend(new_list)
    return converted, failed, errors


def convert_single_paragraph_to_image(
    document: "Document",
    flat_index: int,
    *,
    images_dir: Path | None = None,
    dpi: int = 150,
) -> tuple[int, int, list[str]]:
    """
    Convert only the paragraph at the given flat list index to an image, if it is
    a root-level paragraph that is entirely a LaTeX formula. Modifies document in place.
    Returns (converted_count, failed_count, list of error messages).
    """
    from core.models.document import ContentNode, ImageNode

    from services.latex_merge import _is_entirely_formula

    if not MATHTEXT_AVAILABLE:
        return 0, 0, []

    flat_list = document.flat_list()
    if flat_index < 0 or flat_index >= len(flat_list):
        return 0, 1, ["Invalid index."]
    node = flat_list[flat_index]

    if not isinstance(node, ContentNode) or node.level != 0:
        return 0, 1, ["Selected item is not a paragraph (level 0)."]

    if not _is_entirely_formula(node.text):
        return 0, 1, ["This paragraph is not entirely a LaTeX formula."]

    root = document.root_nodes
    root_index: int | None = None
    for j, rn in enumerate(root):
        if rn is node:
            root_index = j
            break
    if root_index is None:
        return 0, 1, ["Only root-level paragraphs can be converted to images."]

    if images_dir is None:
        images_dir = Path(tempfile.gettempdir()) / "EpubConverter" / "formulas"
    images_dir = Path(images_dir)
    images_dir.mkdir(parents=True, exist_ok=True)

    image_id = _next_image_id(document)
    out_path = images_dir / f"{image_id}.png"
    ok, err_msg = render_formula_to_image(node.text, out_path, dpi=dpi, fmt="png")
    if ok:
        document.images[image_id] = out_path
        alt = node.text.strip()
        if len(alt) > 80:
            alt = alt[:77] + "..."
        root[root_index] = ImageNode(
            id=f"img_node_{image_id}", image_id=image_id, alt=alt or None
        )
        return 1, 0, []
    formula = node.text.strip()
    return 0, 1, [f"Node: {node.id}\nFormula: {formula}\nError: {err_msg or 'unknown error'}"]
