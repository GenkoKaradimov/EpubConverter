"""Run Phase 1 checks without pytest: BookMetadata, Document, ContentNode, base converters."""

import sys

# BookMetadata
from core.models.book_metadata import BookMetadata

m = BookMetadata(title="Test", language="en")
assert m.title == "Test" and m.language == "en" and m.authors == []
try:
    BookMetadata(title="", language="en")
    sys.exit(1)
except ValueError as e:
    assert "title" in str(e).lower()
m2 = BookMetadata(title=" T ", language="en", authors=["A1"], identifiers={"isbn": "123"})
assert m2.title == "T" and m2.authors == ["A1"] and "isbn" in m2.identifiers
print("BookMetadata OK")

# ContentNode, Document
from core.models.document import ContentNode, Document

n1 = ContentNode(id="c1", text="Ch1", level=1)
n2 = ContentNode(id="p1", text="P1", level=0)
n1.children.append(n2)
doc = Document(metadata=m, root_nodes=[n1])
flat = doc.flat_list()
assert len(flat) == 2 and flat[0].id == "c1" and flat[1].id == "p1"
assert doc.get_node_by_id("p1") is n2 and doc.get_node_by_id("x") is None
print("Document/ContentNode OK")

# BaseExtractor, BaseBuilder
from core.converters.base import BaseBuilder, BaseExtractor

class E(BaseExtractor):
    def extract(self, path):
        return Document(metadata=BookMetadata(title="T", language="en"))

class B(BaseBuilder):
    def build(self, document, path):
        pass

E().extract("/fake.pdf")
B().build(doc, "/fake.epub")
print("BaseExtractor/BaseBuilder OK")

print("All Phase 1 checks passed.")
