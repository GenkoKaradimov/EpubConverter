"""Unit tests for BookMetadata."""

import pytest

from core.models.book_metadata import BookMetadata


def test_metadata_required_fields() -> None:
    m = BookMetadata(title="Test", language="en")
    assert m.title == "Test"
    assert m.language == "en"
    assert m.authors == []
    assert m.publisher is None
    assert m.identifiers == {}


def test_metadata_strips_and_validates_title() -> None:
    m = BookMetadata(title="  Title  ", language="en")
    assert m.title == "Title"


def test_metadata_empty_title_raises() -> None:
    with pytest.raises(ValueError, match="title cannot be empty"):
        BookMetadata(title="", language="en")
    with pytest.raises(ValueError, match="title cannot be empty"):
        BookMetadata(title="   ", language="en")


def test_metadata_empty_language_raises() -> None:
    with pytest.raises(ValueError, match="language cannot be empty"):
        BookMetadata(title="T", language="  ")


def test_metadata_authors() -> None:
    m = BookMetadata(title="T", language="en", authors=["A1", "A2"])
    assert m.authors == ["A1", "A2"]
    m2 = BookMetadata(title="T", language="en", authors=["  A  "])
    assert m2.authors == ["A"]


def test_metadata_identifiers() -> None:
    m = BookMetadata(title="T", language="en", identifiers={"ISBN": " 123 ", "uuid": "abc"})
    assert m.identifiers == {"isbn": "123", "uuid": "abc"}
