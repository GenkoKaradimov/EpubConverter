"""
Abstract base converter interfaces: extract(path) -> document, build(document, path).
All code and comments in English.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from core.models.document import Document


class BaseExtractor(ABC):
    """Abstract interface for extracting a Document from a file path."""

    @abstractmethod
    def extract(self, path: Path | str) -> Document:
        """Extract a document from the given file path. Raises on error."""
        ...


class BaseBuilder(ABC):
    """Abstract interface for building an output file from a Document."""

    @abstractmethod
    def build(self, document: Document, path: Path | str) -> None:
        """Write the document to the given output path. Raises on error."""
        ...
