"""
Document representation: book → chapters → sections/paragraphs.
All code and comments in English.
Supports text nodes (ContentNode) and image nodes (ImageNode); images stored by path on disk.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterator, Union

from core.models.book_metadata import BookMetadata

ContentItem = Union["ContentNode", "ImageNode"]


class ImageNode:
    """
    Single image node in the document: id, image_id (key into Document.images), optional alt.
    Optional rotation_degrees and crop_rect for edit; applied at EPUB build time.
    is_formula: True if image was generated from a LaTeX formula (used for EPUB CSS sizing).
    Images are stored on disk; Document.images maps image_id -> Path.
    """

    __slots__ = ("_id", "_image_id", "_alt", "_rotation_degrees", "_crop_rect", "_is_formula")

    def __init__(
        self,
        id: str,
        image_id: str,
        alt: str | None = None,
        rotation_degrees: float = 0.0,
        crop_rect: tuple[float, float, float, float] | None = None,
        is_formula: bool = False,
    ) -> None:
        if not isinstance(id, str) or not id.strip():
            raise ValueError("id must be a non-empty str")
        if not isinstance(image_id, str) or not image_id.strip():
            raise ValueError("image_id must be a non-empty str")
        self._id = id.strip()
        self._image_id = image_id.strip()
        self._alt = alt.strip() if isinstance(alt, str) and alt.strip() else None
        self._rotation_degrees = float(rotation_degrees)
        self._crop_rect = self._validate_crop_rect(crop_rect)
        self._is_formula = bool(is_formula)

    @staticmethod
    def _validate_crop_rect(
        value: tuple[float, float, float, float] | None,
    ) -> tuple[float, float, float, float] | None:
        if value is None:
            return None
        if len(value) != 4:
            raise ValueError("crop_rect must be (left, top, right, bottom)")
        left, top, right, bottom = value
        if not (0 <= left < right <= 1 and 0 <= top < bottom <= 1):
            raise ValueError("crop_rect must satisfy 0 <= left < right <= 1, 0 <= top < bottom <= 1")
        return (float(left), float(top), float(right), float(bottom))

    @property
    def id(self) -> str:
        return self._id

    @property
    def image_id(self) -> str:
        return self._image_id

    @property
    def alt(self) -> str | None:
        return self._alt

    @alt.setter
    def alt(self, value: str | None) -> None:
        if value is None:
            self._alt = None
        elif isinstance(value, str):
            self._alt = value.strip() or None
        else:
            raise TypeError("alt must be str or None")

    @property
    def rotation_degrees(self) -> float:
        return self._rotation_degrees

    @rotation_degrees.setter
    def rotation_degrees(self, value: float) -> None:
        self._rotation_degrees = float(value)

    @property
    def crop_rect(self) -> tuple[float, float, float, float] | None:
        return self._crop_rect

    @crop_rect.setter
    def crop_rect(self, value: tuple[float, float, float, float] | None) -> None:
        self._crop_rect = self._validate_crop_rect(value)

    @property
    def is_formula(self) -> bool:
        return self._is_formula

    @is_formula.setter
    def is_formula(self, value: bool) -> None:
        self._is_formula = bool(value)

    def walk(self) -> Iterator[ImageNode]:
        """Yield only this node (no children)."""
        yield self

    def flat_list(self) -> list[ImageNode]:
        return [self]

    def __repr__(self) -> str:
        return f"ImageNode(id={self._id!r}, image_id={self._image_id!r})"


class ContentNode:
    """
    Single node in the document tree: id, text, heading level, children.
    level: 0 = paragraph/body, 1 = h1 (chapter), 2 = h2, 3 = h3, etc.
    """

    __slots__ = ("_id", "_text", "_level", "_children")

    def __init__(
        self,
        id: str,
        text: str,
        level: int = 0,
        children: list[ContentNode] | None = None,
    ) -> None:
        if not isinstance(id, str) or not id.strip():
            raise ValueError("id must be a non-empty str")
        if not isinstance(text, str):
            raise TypeError("text must be str")
        if not isinstance(level, int) or level < 0:
            raise ValueError("level must be a non-negative int")
        self._id = id.strip()
        self._text = text
        self._level = level
        self._children = list(children) if children else []

    @property
    def id(self) -> str:
        return self._id

    @property
    def text(self) -> str:
        return self._text

    @text.setter
    def text(self, value: str) -> None:
        if not isinstance(value, str):
            raise TypeError("text must be str")
        self._text = value

    @property
    def level(self) -> int:
        return self._level

    @property
    def children(self) -> list[ContentNode]:
        return self._children

    def walk(self) -> Iterator[ContentNode]:
        """Depth-first iterator over this node and all descendants."""
        yield self
        for child in self._children:
            yield from child.walk()

    def flat_list(self) -> list[ContentNode]:
        """List of this node and all descendants in document order (depth-first)."""
        return list(self.walk())

    def __repr__(self) -> str:
        return f"ContentNode(id={self._id!r}, level={self._level}, children={len(self._children)})"


class Document:
    """
    Document: metadata, root nodes (text and/or image), and image paths on disk.
    Supports traversal and flat list for editing. Images stored by path, not in RAM.
    """

    __slots__ = ("_metadata", "_root_nodes", "_images")

    def __init__(
        self,
        metadata: BookMetadata,
        root_nodes: list[ContentItem] | None = None,
        images: dict[str, Path] | None = None,
    ) -> None:
        if not isinstance(metadata, BookMetadata):
            raise TypeError("metadata must be BookMetadata")
        self._metadata = metadata
        self._root_nodes = list(root_nodes) if root_nodes else []
        self._images = dict(images) if images else {}

    @property
    def metadata(self) -> BookMetadata:
        return self._metadata

    @property
    def root_nodes(self) -> list[ContentItem]:
        return self._root_nodes

    @property
    def images(self) -> dict[str, Path]:
        return self._images

    def walk(self) -> Iterator[ContentItem]:
        """Depth-first iterator over all nodes in the document."""
        for node in self._root_nodes:
            yield from node.walk()

    def flat_list(self) -> list[ContentItem]:
        """Flat list of all nodes in document order (for editing)."""
        return list(self.walk())

    def get_node_by_id(self, id: str) -> ContentItem | None:
        """Return the first node with the given id, or None."""
        key = id.strip() if isinstance(id, str) else None
        if not key:
            return None
        for node in self.walk():
            if node.id == key:
                return node
        return None

    def __repr__(self) -> str:
        return f"Document(metadata={self._metadata!r}, root_nodes={len(self._root_nodes)}, images={len(self._images)})"
