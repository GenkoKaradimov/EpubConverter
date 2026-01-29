"""Unit tests for Document and ContentNode."""

from core.models.book_metadata import BookMetadata
from core.models.document import ContentNode, Document


def test_content_node_basic() -> None:
    n = ContentNode(id="c1", text="Chapter 1", level=1)
    assert n.id == "c1"
    assert n.text == "Chapter 1"
    assert n.level == 1
    assert n.children == []


def test_content_node_walk_single() -> None:
    n = ContentNode(id="p1", text="Para", level=0)
    nodes = list(n.walk())
    assert len(nodes) == 1
    assert nodes[0] is n


def test_content_node_flat_list_with_children() -> None:
    child = ContentNode(id="p1", text="Para", level=0)
    root = ContentNode(id="ch1", text="Chapter", level=1, children=[child])
    flat = root.flat_list()
    assert len(flat) == 2
    assert flat[0].id == "ch1"
    assert flat[1].id == "p1"


def test_document_walk_and_flat_list() -> None:
    meta = BookMetadata(title="Book", language="en")
    n1 = ContentNode(id="c1", text="Ch1", level=1)
    n2 = ContentNode(id="p1", text="P1", level=0)
    n1.children.append(n2)
    doc = Document(metadata=meta, root_nodes=[n1])
    flat = doc.flat_list()
    assert len(flat) == 2
    assert flat[0].id == "c1"
    assert flat[1].id == "p1"


def test_document_get_node_by_id() -> None:
    meta = BookMetadata(title="Book", language="en")
    n1 = ContentNode(id="c1", text="Ch1", level=1)
    n2 = ContentNode(id="p1", text="P1", level=0)
    n1.children.append(n2)
    doc = Document(metadata=meta, root_nodes=[n1])
    assert doc.get_node_by_id("c1") is n1
    assert doc.get_node_by_id("p1") is n2
    assert doc.get_node_by_id("missing") is None
