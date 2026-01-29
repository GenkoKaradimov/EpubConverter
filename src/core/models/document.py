"""
Document representation: book → chapters → sections/paragraphs.
All code and comments in English.
"""

from __future__ import annotations

from typing import Iterator

from core.models.book_metadata import BookMetadata


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
    Document: metadata plus a list of root nodes (chapters/sections).
    Supports traversal and flat list for editing.
    """

    __slots__ = ("_metadata", "_root_nodes")

    def __init__(
        self,
        metadata: BookMetadata,
        root_nodes: list[ContentNode] | None = None,
    ) -> None:
        if not isinstance(metadata, BookMetadata):
            raise TypeError("metadata must be BookMetadata")
        self._metadata = metadata
        self._root_nodes = list(root_nodes) if root_nodes else []

    @property
    def metadata(self) -> BookMetadata:
        return self._metadata

    @property
    def root_nodes(self) -> list[ContentNode]:
        return self._root_nodes

    def walk(self) -> Iterator[ContentNode]:
        """Depth-first iterator over all nodes in the document."""
        for node in self._root_nodes:
            yield from node.walk()

    def flat_list(self) -> list[ContentNode]:
        """Flat list of all nodes in document order (for editing)."""
        return list(self.walk())

    def get_node_by_id(self, id: str) -> ContentNode | None:
        """Return the first node with the given id, or None."""
        key = id.strip() if isinstance(id, str) else None
        if not key:
            return None
        for node in self.walk():
            if node.id == key:
                return node
        return None

    def __repr__(self) -> str:
        return f"Document(metadata={self._metadata!r}, root_nodes={len(self._root_nodes)})"
