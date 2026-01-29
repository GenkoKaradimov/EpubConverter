"""Unit tests for base converter interfaces."""

from pathlib import Path

import pytest

from core.converters.base import BaseBuilder, BaseExtractor
from core.models import BookMetadata, Document


def test_base_extractor_is_abstract() -> None:
    with pytest.raises(TypeError):
        BaseExtractor()

    class Impl(BaseExtractor):
        def extract(self, path: Path | str) -> Document:
            return Document(metadata=BookMetadata(title="T", language="en"))

    impl = Impl()
    doc = impl.extract(Path("/fake/path.pdf"))
    assert doc.metadata.title == "T"


def test_base_builder_is_abstract() -> None:
    with pytest.raises(TypeError):
        BaseBuilder()

    class Impl(BaseBuilder):
        def build(self, document: Document, path: Path | str) -> None:
            pass

    impl = Impl()
    doc = Document(metadata=BookMetadata(title="T", language="en"))
    impl.build(doc, Path("/fake/out.epub"))
