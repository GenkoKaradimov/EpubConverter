"""
Merge consecutive paragraphs and separate paragraphs containing LaTeX formulas.
Used by LaTeX dialog: merge_paragraphs (merge), separate_formulas (split by $...$).
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from core.models.document import Document

# Paragraph is "entirely formula" if after strip it is only $...$ and optional whitespace.
_RE_ENTIRELY_FORMULA = re.compile(r"^\s*(\$[^$]*\$\s*)+$")

# Split text into segments: non-formula and formula. Match display math $$...$$ first, then inline $...$.
# Order matters: $$...$$ before $...$ so we don't split "$$ formula $$" into three parts.
_RE_FORMULA = re.compile(r"(\$\$[^$]*\$\$|\$[^$]*\$)")


def _is_entirely_formula(text: str) -> bool:
    """True if text (after strip) is empty or only LaTeX formulas ($...$) and whitespace."""
    if not text or not text.strip():
        return False
    return _RE_ENTIRELY_FORMULA.match(text.strip()) is not None


def merge_paragraphs(
    document: "Document",
    progress_callback: Callable[[int, int], None] | None = None,
) -> None:
    """
    Merge consecutive paragraphs (ContentNode level 0) into one, except paragraphs
    that are entirely a LaTeX formula (such paragraphs stay separate).
    Modifies document.root_nodes in place by building a new list and replacing.
    """
    from core.models.document import ContentNode

    root = document.root_nodes
    new_list: list = []
    i = 0
    total = len(root)
    step = 0

    while i < len(root):
        node = root[i]
        if not isinstance(node, ContentNode) or node.level != 0:
            new_list.append(node)
            i += 1
            if progress_callback:
                step += 1
                progress_callback(step, total)
            continue

        # Collect run of consecutive paragraphs
        run: list[ContentNode] = []
        j = i
        while j < len(root) and isinstance(root[j], ContentNode) and root[j].level == 0:
            run.append(root[j])
            j += 1

        # Split run by "entirely formula": merge each contiguous sub-run of non-formula paragraphs
        merge_group: list[ContentNode] = []
        for p in run:
            if _is_entirely_formula(p.text):
                # Flush current merge group
                if merge_group:
                    merged_text = "\n\n".join(n.text.strip() for n in merge_group if n.text.strip())
                    merged_id = merge_group[0].id
                    new_list.append(ContentNode(id=merged_id, text=merged_text, level=0))
                    merge_group = []
                new_list.append(p)
            else:
                merge_group.append(p)
        if merge_group:
            merged_text = "\n\n".join(n.text.strip() for n in merge_group if n.text.strip())
            merged_id = merge_group[0].id
            new_list.append(ContentNode(id=merged_id, text=merged_text, level=0))

        i = j
        if progress_callback:
            step += len(run)
            progress_callback(min(step, total), total)

    root.clear()
    root.extend(new_list)


def separate_formulas(
    document: "Document",
    progress_callback: Callable[[int, int], None] | None = None,
) -> None:
    """
    Split each paragraph (ContentNode level 0) that contains $...$ into multiple
    paragraphs so that each formula is alone in one paragraph; order is preserved.
    Modifies document.root_nodes by building a new list and replacing.
    """
    from core.models.document import ContentNode

    root = document.root_nodes
    new_list: list = []
    total = len(root)
    for idx, node in enumerate(root):
        if progress_callback:
            progress_callback(idx + 1, total)
        if not isinstance(node, ContentNode) or node.level != 0:
            new_list.append(node)
            continue
        text = node.text
        if "$" not in text:
            new_list.append(node)
            continue
        # Split by formula segments: re.split keeps the delimiters in the list
        parts = _RE_FORMULA.split(text)
        # parts = [before_first, formula1, between, formula2, ...]
        segments = [s.strip() for s in parts if s.strip()]
        if len(segments) <= 1:
            new_list.append(node)
            continue
        base_id = node.id
        for k, seg in enumerate(segments):
            nid = f"{base_id}_s{k}"
            new_list.append(ContentNode(id=nid, text=seg, level=0))

    root.clear()
    root.extend(new_list)
