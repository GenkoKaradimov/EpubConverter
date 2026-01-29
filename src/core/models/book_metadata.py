"""
Book metadata: title, author(s), language, publisher, identifiers.
All code and comments in English.
"""

from __future__ import annotations


def _non_empty_stripped(value: str, name: str) -> str:
    """Return stripped string; raise ValueError if empty."""
    if not isinstance(value, str):
        raise TypeError(f"{name} must be str, got {type(value).__name__}")
    s = value.strip()
    if not s:
        raise ValueError(f"{name} cannot be empty")
    return s


def _normalize_identifier_key(key: str) -> str:
    """Normalize identifier type key (e.g. 'isbn' -> 'isbn')."""
    if not isinstance(key, str) or not key.strip():
        raise ValueError("Identifier key must be a non-empty str")
    return key.strip().lower()


class BookMetadata:
    """
    Immutable book metadata for EPUB/conversion.
    Required: title, language. At least one author recommended.
    """

    __slots__ = ("_title", "_authors", "_language", "_publisher", "_identifiers")

    def __init__(
        self,
        title: str,
        language: str,
        authors: list[str] | None = None,
        publisher: str | None = None,
        identifiers: dict[str, str] | None = None,
    ) -> None:
        self._title = _non_empty_stripped(title, "title")
        self._language = _non_empty_stripped(language, "language")
        self._authors = self._validate_authors(authors)
        self._publisher = publisher.strip() if isinstance(publisher, str) and publisher.strip() else None
        self._identifiers = self._validate_identifiers(identifiers)

    @staticmethod
    def _validate_authors(authors: list[str] | None) -> list[str]:
        if authors is None:
            return []
        if not isinstance(authors, list):
            raise TypeError("authors must be list[str] or None")
        result = []
        for i, a in enumerate(authors):
            if not isinstance(a, str):
                raise TypeError(f"authors[{i}] must be str")
            s = a.strip()
            if s:
                result.append(s)
        return result

    @staticmethod
    def _validate_identifiers(identifiers: dict[str, str] | None) -> dict[str, str]:
        if identifiers is None:
            return {}
        if not isinstance(identifiers, dict):
            raise TypeError("identifiers must be dict[str, str] or None")
        return {_normalize_identifier_key(k): str(v).strip() for k, v in identifiers.items() if str(v).strip()}

    @property
    def title(self) -> str:
        return self._title

    @property
    def language(self) -> str:
        return self._language

    @property
    def authors(self) -> list[str]:
        return self._authors.copy()

    @property
    def publisher(self) -> str | None:
        return self._publisher

    @property
    def identifiers(self) -> dict[str, str]:
        return self._identifiers.copy()

    def __repr__(self) -> str:
        return f"BookMetadata(title={self._title!r}, language={self._language!r}, authors={self._authors!r})"
